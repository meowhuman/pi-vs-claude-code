/**
 * Music Study Board — Multi-Agent Music Research & Discovery System
 *
 * A collaborative system for deep music exploration with specialist agents:
 * - Deep Researcher: thorough topic investigation
 * - YouTube Curator: video discovery and curation
 * - Genre Historian: historical context and musical lineage
 * - Listening Guide: structured listening guidance
 *
 * Config: .pi/music-study/config.yaml
 * Agents: .pi/music-study/agents/<name>/
 *
 * Commands:
 *   /board-preset   — select a preset (full/discovery/jazz-deep/quick)
 *   /board-status   — show active board members
 *
 * Usage: pi -e extensions/music-study.ts
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { readFileSync, existsSync } from "fs";
import { join, resolve } from "path";
import { applyExtensionDefaults } from "./themeMap.ts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BoardMemberConfig {
  name: string;
  path: string;
  active: boolean;
}

interface BoardConfig {
  meeting: {
    discussion_time_minutes: number;
  };
  board: BoardMemberConfig[];
  presets: Record<string, string[]>;
}

// ── Simple YAML Parser ────────────────────────────────────────────────────────

function parseBoardConfigYaml(raw: string): BoardConfig {
  const config: BoardConfig = {
    meeting: { discussion_time_minutes: 10 },
    board: [],
    presets: {},
  };

  const lines = raw.split("\n");
  let section = "";
  let currentItem: Partial<BoardMemberConfig> = {};

  const flushItem = () => {
    if (currentItem.name) {
      config.board.push({
        name: currentItem.name,
        path: currentItem.path || "",
        active: currentItem.active !== false,
      });
      currentItem = {};
    }
  };

  for (const line of lines) {
    if (line.match(/^meeting:\s*$/)) { section = "meeting"; continue; }
    if (line.match(/^board:\s*$/)) { section = "board"; continue; }
    if (line.match(/^presets:\s*$/)) { flushItem(); section = "presets"; continue; }

    if (section === "meeting") {
      const m = line.match(/^\s+discussion_time_minutes:\s*(\d+)/);
      if (m) config.meeting.discussion_time_minutes = parseInt(m[1], 10);
    }

    if (section === "board") {
      if (line.match(/^\s+-\s+name:/)) {
        flushItem();
        const m = line.match(/name:\s*(.+)/);
        currentItem = { name: m ? m[1].trim() : "" };
      } else if (line.match(/^\s+path:/)) {
        const m = line.match(/path:\s*(.+)/);
        currentItem.path = m ? m[1].trim() : "";
      } else if (line.match(/^\s+active:/)) {
        const m = line.match(/active:\s*(true|false)/);
        currentItem.active = m ? m[1] === "true" : true;
      }
    }

    if (section === "presets") {
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) {
        config.presets[m[1]] = m[2].split(",").map((s) => s.trim()).filter(Boolean);
      }
    }
  }

  flushItem();
  return config;
}

// ── Load Agent System Prompt ──────────────────────────────────────────────────

function parseMemberFile(filePath: string): { name: string; systemPrompt: string } | null {
  if (!existsSync(filePath)) return null;
  try {
    const content = readFileSync(filePath, "utf-8");
    // Extract frontmatter name
    const nameMatch = content.match(/^---[\s\S]*?^name:\s*(.+)$/m);
    const name = nameMatch ? nameMatch[1].trim() : filePath;
    // Everything after frontmatter is the system prompt
    const bodyMatch = content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)$/);
    const systemPrompt = bodyMatch ? bodyMatch[1].trim() : content.trim();
    return { name, systemPrompt };
  } catch {
    return null;
  }
}

// ── Extension Export ──────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let cwd = "";
  let boardConfig: BoardConfig = {
    meeting: { discussion_time_minutes: 10 },
    board: [],
    presets: {},
  };
  let activePreset: string | null = null;

  // ── Config Loader ────────────────────────────────────────────────────────────

  function loadConfig(rootCwd: string) {
    cwd = rootCwd;
    const configPath = join(rootCwd, ".pi", "music-study", "config.yaml");
    if (!existsSync(configPath)) return;
    try {
      boardConfig = parseBoardConfigYaml(readFileSync(configPath, "utf-8"));
    } catch {
      // use defaults
    }
  }

  function getActiveMembers(presetOverride?: string): BoardMemberConfig[] {
    const preset = presetOverride || activePreset;
    if (preset && boardConfig.presets[preset]) {
      const names = new Set(boardConfig.presets[preset]);
      return boardConfig.board.filter((m) => names.has(m.name));
    }
    return boardConfig.board.filter((m) => m.active);
  }

  // ── Tool: music_study_begin ──────────────────────────────────────────────────

  pi.registerTool({
    name: "music_study_begin",
    label: "Music Study Begin",
    description:
      "Convene the Music Study board for a collaborative music exploration session. " +
      "All active members research the topic in parallel and contribute their specialist perspective. " +
      "Provide a topic (genre, artist, album, era, etc.).",
    parameters: Type.Object({
      topic: Type.String({
        description: "Music topic to explore (e.g. 'bebop jazz 1940s', 'Bill Evans piano style')",
      }),
      preset: Type.Optional(
        Type.String({
          description: "Override board preset (full/discovery/jazz-deep/quick)",
        })
      ),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { topic, preset } = params as { topic: string; preset?: string };

      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return {
          content: [{ type: "text", text: "No active board members. Check config or select a preset." }],
          details: { status: "error" },
        };
      }

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `🎵 Convening Music Study Board (${activeMembers.length} members)...` }],
          details: { status: "running" },
        });
      }

      // Load member definitions
      const memberDefs: { name: string; systemPrompt: string }[] = [];
      for (const member of activeMembers) {
        const memberPath = resolve(cwd, member.path);
        const def = parseMemberFile(memberPath);
        if (def) memberDefs.push(def);
      }

      if (memberDefs.length === 0) {
        return {
          content: [{ type: "text", text: "Could not load any agent definitions. Check .pi/music-study/agents/ paths." }],
          details: { status: "error" },
        };
      }

      const memberList = memberDefs.map((m) => `- **${m.name}**`).join("\n");
      const prompt =
        `You are the facilitator of the Music Study Board.\n\n` +
        `The following specialist agents will contribute their perspectives on the topic:\n${memberList}\n\n` +
        `## Topic\n${topic}\n\n` +
        `Please call upon each member to share their specialist perspective in sequence. ` +
        `Frame the topic clearly first, then guide each member's contribution, ` +
        `and finally synthesize the insights into a comprehensive music study guide.\n\n` +
        `Agent system prompts (inject into responses):\n\n` +
        memberDefs.map((m) => `### ${m.name}\n${m.systemPrompt}`).join("\n\n---\n\n");

      return {
        content: [{ type: "text", text: prompt }],
        details: { status: "done", members: memberDefs.map((m) => m.name) },
      };
    },
  });

  // ── Commands ─────────────────────────────────────────────────────────────────

  pi.registerCommand("board-preset", {
    description: "Select a preset for music study session",
    handler: async (_args, ctx) => {
      const presetNames = Object.keys(boardConfig.presets);
      if (presetNames.length === 0) {
        ctx.ui.notify("No presets defined in config.yaml", "warning");
        return;
      }

      const options = presetNames.map((name) => {
        const members = boardConfig.presets[name];
        return `${name} (${members.join(", ")})`;
      });

      const choice = await ctx.ui.select("Select Board Preset", options);
      if (choice === undefined) return;

      const idx = options.indexOf(choice);
      activePreset = presetNames[idx];

      const members = boardConfig.presets[activePreset];
      ctx.ui.setStatus("music-study", `Preset: ${activePreset} · ${members.length} members`);
      ctx.ui.notify(`Preset: ${activePreset}\nMembers: ${members.join(", ")}`, "info");
    },
  });

  pi.registerCommand("board-status", {
    description: "Show active music study board members",
    handler: async (_args, ctx) => {
      const active = getActiveMembers();
      const all = boardConfig.board;

      const lines = all.map((m) => {
        const isActive = active.some((a) => a.name === m.name);
        return `${isActive ? "✓" : "○"} ${m.name}`;
      });

      const presetInfo = activePreset ? `Preset: ${activePreset}` : "Using config defaults";
      ctx.ui.notify(
        `🎵 Music Study Board\n${presetInfo}\n\n${lines.join("\n")}`,
        "info"
      );
    },
  });

  // ── Session Start ─────────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);

    loadConfig(ctx.cwd);

    const active = getActiveMembers();
    ctx.ui.setStatus("music-study", `🎵 Music Study · ${active.length} members`);
    ctx.ui.notify(
      `Music Study Board loaded\n` +
        `${active.length} active members\n\n` +
        `Presets: ${Object.keys(boardConfig.presets).join(", ")}\n\n` +
        `/board-preset    Select preset\n` +
        `/board-status    Show members`,
      "info"
    );
  });

  // ── Before Agent Start ────────────────────────────────────────────────────────

  pi.on("before_agent_start", async (_event, _ctx) => {
    const active = getActiveMembers();
    const presetLabel = activePreset || "config defaults";
    const memberList = active.map((m) => `- **${m.name}**`).join("\n");
    const presetList = Object.keys(boardConfig.presets).join(", ");

    return {
      systemPrompt:
        `You are the facilitator for the Music Study Board — a multi-specialist team for deep music exploration.\n\n` +
        `## Your Role\n` +
        `You help users explore music topics deeply by convening the board with \`music_study_begin\`.\n` +
        `When a user wants to explore a music topic:\n` +
        `1. Ask for the topic (genre, artist, album, era, technique, etc.)\n` +
        `2. Optionally ask which preset to use\n` +
        `3. Call \`music_study_begin\` with the topic and optional preset\n\n` +
        `## Current Board Config\n` +
        `Preset: ${presetLabel}\n` +
        `Active members (${active.length}):\n${memberList}\n\n` +
        `## Available Presets\n` +
        `${presetList || "None defined"}\n` +
        `Use /board-preset to switch presets, /board-status to see all members.\n\n` +
        `## Commands\n` +
        `/board-preset    Select a board preset\n` +
        `/board-status    Show active board members\n\n` +
        `Start by welcoming the user and asking what music topic they'd like to explore.`,
    };
  });
}
