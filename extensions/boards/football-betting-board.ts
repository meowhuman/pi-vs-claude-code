/**
 * Football Betting Board — 多代理足球博彩情報委員會
 *
 * 召集多位足球博彩專家並行分析賽事，最後由 Director 整合成可執行的投注報告。
 *
 * Config: .pi/football-betting-board/config.yaml
 * Agents: .pi/football-betting-board/agents/<name>/<name>.md
 * Memos:  .pi/football-betting-board/memos/<slug>-<timestamp>.md
 *
 * Commands:
 *   /board-preset  — 選擇 preset
 *   /board-status  — 顯示活躍委員
 *   /board-history — 顯示最近報告
 *
 * Tools:
 *   board_begin    — 提交賽事 brief → 全自動委員會分析 → 輸出 Markdown/HTML 報告
 *
 * Tools (Mode B — 互動討論):
 *   board_discuss  — 開始互動討論模式，用戶作為「人類委員」坐入委員會
 *   board_next     — 讓下一位或指定委員發言（可帶入用戶的背景/回應）
 *   board_report   — 結束討論，生成最終報告（輸出 -discussion 後綴的 .md 和 .html）
 */

import type { ExtensionAPI, ExtensionContext } from '@mariozechner/pi-coding-agent';
import { Type } from '@sinclair/typebox';
import { Text, truncateToWidth, visibleWidth } from '@mariozechner/pi-tui';
import { spawn } from 'child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { applyExtensionDefaults } from '../themeMap.ts';

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

interface MemberDef {
  name: string;
  description: string;
  systemPrompt: string;
  model: string;
  tools: string;
  knowledgePath: string;
}

interface MemberState {
  name: string;
  status: 'pending' | 'running' | 'done' | 'error';
  elapsed: number;
  lastWork: string;
}

interface RunResult {
  output: string;
  exitCode: number;
  elapsed: number;
}

let cwd = process.cwd();
let boardConfig: BoardConfig = {
  meeting: { discussion_time_minutes: 10 },
  board: [],
  presets: {},
};
let activePreset: string | null = process.env.BOARD_PRESET || null;
let memberStates: MemberState[] = [];
let boardPhase: 'idle' | 'framing' | 'deliberating' | 'synthesizing' = 'idle';
let directorFramingText = '';
let widgetCtx: ExtensionContext | null = null;

function parseBoardConfigYaml(raw: string): BoardConfig {
  const config: BoardConfig = {
    meeting: { discussion_time_minutes: 10 },
    board: [],
    presets: {},
  };

  const lines = raw.split('\n');
  let section = '';
  let inBoardItem = false;
  let currentItem: Partial<BoardMemberConfig> = {};
  let inPresets = false;

  for (const line of lines) {
    if (line.match(/^meeting:\s*$/)) {
      section = 'meeting';
      inBoardItem = false;
      inPresets = false;
      continue;
    }
    if (line.match(/^board:\s*$/)) {
      section = 'board';
      inBoardItem = false;
      inPresets = false;
      continue;
    }
    if (line.match(/^presets:\s*$/)) {
      if (inBoardItem && currentItem.name) {
        config.board.push({
          name: currentItem.name,
          path: currentItem.path || '',
          active: currentItem.active !== false,
        });
        currentItem = {};
      }
      section = 'presets';
      inBoardItem = false;
      inPresets = true;
      continue;
    }

    if (section === 'meeting') {
      const m = line.match(/^\s+discussion_time_minutes:\s*(\d+)/);
      if (m) config.meeting.discussion_time_minutes = parseInt(m[1], 10);
      continue;
    }

    if (section === 'board') {
      if (line.match(/^\s+-\s+name:/)) {
        if (inBoardItem && currentItem.name) {
          config.board.push({
            name: currentItem.name,
            path: currentItem.path || '',
            active: currentItem.active !== false,
          });
        }
        currentItem = {};
        inBoardItem = true;
        const m = line.match(/^\s+-\s+name:\s*(.+)$/);
        if (m) currentItem.name = m[1].trim();
        continue;
      }
      if (inBoardItem) {
        const pathM = line.match(/^\s+path:\s*(.+)$/);
        if (pathM) {
          currentItem.path = pathM[1].trim();
          continue;
        }
        const activeM = line.match(/^\s+active:\s*(true|false)/);
        if (activeM) {
          currentItem.active = activeM[1] === 'true';
          continue;
        }
      }
      continue;
    }

    if (section === 'presets' && inPresets) {
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) {
        config.presets[m[1].trim()] = m[2]
          .split(',')
          .map(s => s.trim())
          .filter(Boolean);
      }
    }
  }

  if (section === 'board' && inBoardItem && currentItem.name) {
    config.board.push({
      name: currentItem.name,
      path: currentItem.path || '',
      active: currentItem.active !== false,
    });
  }

  return config;
}

function parseMemberFile(filePath: string): MemberDef | null {
  try {
    const raw = readFileSync(filePath, 'utf-8');
    const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) return null;

    const fm: Record<string, string> = {};
    for (const line of match[1].split('\n')) {
      const idx = line.indexOf(':');
      if (idx > 0) fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }

    const name = fm.name || filePath;
    return {
      name,
      description: fm.description || '',
      systemPrompt: match[2].trim(),
      model: fm.model || '',
      tools: fm.tools || 'bash,read',
      knowledgePath: join(dirname(filePath), `${name}-knowledge.md`),
    };
  } catch {
    return null;
  }
}

function loadMemberKnowledge(member: MemberDef): string {
  if (!existsSync(member.knowledgePath)) return '';
  const content = readFileSync(member.knowledgePath, 'utf-8').trim();
  return content ? `\n\n## ${displayName(member.name)} 個人知識庫\n\n${content}` : '';
}

function loadBoardKnowledge(): string {
  const kbPath = join(cwd, '.pi', 'football-betting-board', 'knowledge-base.md');
  if (!existsSync(kbPath)) return '';
  const content = readFileSync(kbPath, 'utf-8').trim();
  return content ? `\n\n## 足球博彩情報中心共享知識庫\n\n${content}` : '';
}

function displayName(name: string): string {
  return name
    .split(/[-_]/)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 60);
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function resolveBrief(brief: string): string | null {
  if (!brief.endsWith('.md')) return brief;
  const briefPath = resolve(cwd, brief);
  if (!existsSync(briefPath)) return null;
  return readFileSync(briefPath, 'utf-8');
}

interface FixtureCandidate {
  league: string;
  competitionCode: string;
  home: string;
  away: string;
  utcDate: string;
  status: string;
}

function hasConcreteFixtures(brief: string): boolean {
  return /\bvs\b|v\.|對|主隊|客隊|Arsenal|Liverpool|Chelsea|Real Madrid|Barcelona|Inter|Milan|Juventus|Bayern|Dortmund|PSG/i
    .test(brief);
}

function inferCompetitionCodes(brief: string): string[] {
  const lower = brief.toLowerCase();
  const codes = new Set<string>();

  if (lower.includes('major 5') || lower.includes('big 5') || lower.includes('五大聯賽')) {
    ['PL', 'PD', 'SA', 'BL1', 'FL1'].forEach(code => codes.add(code));
  }
  if (lower.includes('epl') || lower.includes('premier league') || lower.includes('英超')) codes.add('PL');
  if (lower.includes('la liga') || lower.includes('laliga') || lower.includes('西甲')) codes.add('PD');
  if (lower.includes('serie a') || lower.includes('seriea') || lower.includes('意甲')) codes.add('SA');
  if (lower.includes('bundesliga') || lower.includes('德甲')) codes.add('BL1');
  if (lower.includes('ligue 1') || lower.includes('ligue1') || lower.includes('法甲')) codes.add('FL1');
  if (codes.size === 0) ['PL', 'PD', 'SA', 'BL1', 'FL1'].forEach(code => codes.add(code));

  return Array.from(codes);
}

function inferFixtureLimit(brief: string): number {
  const match = brief.match(/(\d+)\s*場/);
  if (!match) return 5;
  const n = parseInt(match[1], 10);
  if (Number.isNaN(n)) return 5;
  return Math.min(Math.max(n, 1), 12);
}

function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function inferDateRange(brief: string): { from: string; to: string; label: string } {
  const now = new Date();
  const day = now.getDay();
  const lower = brief.toLowerCase();

  const addDays = (base: Date, n: number) => {
    const d = new Date(base);
    d.setDate(d.getDate() + n);
    return d;
  };

  if (lower.includes('本週六日') || lower.includes('this weekend') || lower.includes('週末')) {
    const untilSat = ((6 - day) + 7) % 7;
    const sat = addDays(now, untilSat === 0 ? 0 : untilSat);
    const sun = addDays(sat, 1);
    return { from: formatDate(sat), to: formatDate(sun), label: '本週六日' };
  }

  if (lower.includes('今日') || lower.includes('today')) {
    const today = formatDate(now);
    return { from: today, to: today, label: '今日' };
  }

  if (lower.includes('明日') || lower.includes('tomorrow')) {
    const tomorrow = addDays(now, 1);
    const date = formatDate(tomorrow);
    return { from: date, to: date, label: '明日' };
  }

  const explicit = brief.match(/(20\d{2}-\d{2}-\d{2})/g);
  if (explicit && explicit.length >= 2) {
    return { from: explicit[0], to: explicit[1], label: `${explicit[0]} ~ ${explicit[1]}` };
  }
  if (explicit && explicit.length === 1) {
    return { from: explicit[0], to: explicit[0], label: explicit[0] };
  }

  const today = formatDate(now);
  const plus2 = formatDate(addDays(now, 2));
  return { from: today, to: plus2, label: `${today} ~ ${plus2}` };
}

async function fetchCompetitionFixtures(
  competitionCode: string,
  from: string,
  to: string,
): Promise<FixtureCandidate[]> {
  const apiKey = process.env.FOOTBALL_DATA_KEY;
  if (!apiKey) return [];

  const url = `https://api.football-data.org/v4/competitions/${competitionCode}/matches?dateFrom=${from}&dateTo=${to}`;

  try {
    const response = await fetch(url, {
      headers: {
        'X-Auth-Token': apiKey,
      },
    });

    if (!response.ok) return [];
    const data = await response.json() as {
      competition?: { name?: string };
      matches?: Array<{
        utcDate?: string;
        status?: string;
        homeTeam?: { name?: string };
        awayTeam?: { name?: string };
      }>;
    };

    return (data.matches || [])
      .filter(match => match.homeTeam?.name && match.awayTeam?.name && match.utcDate)
      .map(match => ({
        league: data.competition?.name || competitionCode,
        competitionCode,
        home: match.homeTeam!.name!,
        away: match.awayTeam!.name!,
        utcDate: match.utcDate!,
        status: match.status || '',
      }));
  } catch {
    return [];
  }
}

async function enrichBriefWithAutoFixtures(brief: string): Promise<string> {
  if (hasConcreteFixtures(brief)) return brief;

  const competitionCodes = inferCompetitionCodes(brief);
  const dateRange = inferDateRange(brief);
  const fixtureLimit = inferFixtureLimit(brief);

  const fetched = await Promise.all(
    competitionCodes.map(code => fetchCompetitionFixtures(code, dateRange.from, dateRange.to)),
  );
  const fixtures = fetched
    .flat()
    .sort((a, b) => a.utcDate.localeCompare(b.utcDate));

  if (fixtures.length === 0) {
    return `${brief}\n\n## Auto Fixture Discovery\n\n` +
      `- 狀態：找不到可用賽程資料\n` +
      `- 日期範圍：${dateRange.label}\n` +
      `- 聯賽：${competitionCodes.join(', ')}\n` +
      `- 說明：請 Director 先誠實回報 fixture discovery 失敗，不可虛構賽事。`;
  }

  const shortlisted = fixtures.slice(0, Math.max(fixtureLimit * 3, 10));
  const lines = shortlisted.map((fixture, index) => {
    const kickoff = fixture.utcDate.replace('T', ' ').slice(0, 16);
    return `${index + 1}. [${fixture.competitionCode}] ${fixture.home} vs ${fixture.away} | ${kickoff} UTC | ${fixture.status}`;
  });

  return `${brief}\n\n## Auto Fixture Discovery\n\n` +
    `系統已自動抓取候選賽程。請 Director 先從以下候選中挑選最適合分析與下注規劃的 ${fixtureLimit} 場，` +
    `再要求各委員圍繞這些具體 fixtures 進行分析。若盤口或資料不足，允許輸出 no-bet。\n\n` +
    `- 日期範圍：${dateRange.label}\n` +
    `- 聯賽：${competitionCodes.join(', ')}\n` +
    `- 候選場次數：${shortlisted.length}\n\n` +
    `### Candidate Fixtures\n` +
    `${lines.join('\n')}`;
}

function loadConfig(nextCwd: string) {
  cwd = nextCwd;
  const configPath = join(cwd, '.pi', 'football-betting-board', 'config.yaml');
  if (!existsSync(configPath)) {
    boardConfig = { meeting: { discussion_time_minutes: 10 }, board: [], presets: {} };
    return;
  }
  boardConfig = parseBoardConfigYaml(readFileSync(configPath, 'utf-8'));
}

function getActiveMembers(preset?: string | null): BoardMemberConfig[] {
  const presetName = preset || activePreset;
  if (presetName && boardConfig.presets[presetName]) {
    const names = new Set(boardConfig.presets[presetName]);
    return boardConfig.board.filter(member => member.active && names.has(member.name));
  }
  return boardConfig.board.filter(member => member.active);
}

function renderStatusLine(state: MemberState): string {
  const icon = state.status === 'running'
    ? '●'
    : state.status === 'done'
      ? '✓'
      : state.status === 'error'
        ? '✗'
        : '○';
  const elapsed = state.elapsed > 0 ? ` ${state.elapsed}s` : '';
  return `${icon} ${displayName(state.name)}${elapsed}`;
}

function updateWidget() {
  if (!widgetCtx?.hasUI) return;

  widgetCtx.ui.setWidget(
    'football-betting-board',
    (_tui, theme) => {
      const lines: string[] = [];

      // ── Discussion mode widget ──────────────────────────────────────────────
      if (discussionSession?.active) {
        const sess = discussionSession;
        const spokenNames = sess.history
          .filter(e => e.speaker !== 'user' && e.speaker !== 'director')
          .map(e => displayName(e.speaker));
        const uniqueSpoken = [...new Set(spokenNames)];
        const rounds = sess.history.length;
        const remaining = sess.speakOrder.length - sess.nextSpeakerIdx;

        lines.push(theme.fg('accent', '  ● 互動討論模式'));
        lines.push('');
        lines.push(theme.fg('muted', `  對話輪次：${rounds}  |  已發言：${uniqueSpoken.length} 位  |  待發言：${remaining} 位`));
        if (uniqueSpoken.length > 0) {
          lines.push(theme.fg('dim', `  已發言：${uniqueSpoken.join(', ')}`));
        }
        if (sess.nextSpeakerIdx < sess.speakOrder.length) {
          lines.push(theme.fg('accent', `  下一位：${displayName(sess.speakOrder[sess.nextSpeakerIdx])}`));
        } else {
          lines.push(theme.fg('success', '  所有委員已發言，可 board_report 生成報告'));
        }

        return {
          render(width: number) {
            return lines.map(line => truncateToWidth(line, width));
          },
          invalidate() {},
        };
      }

      // ── Auto mode widget ────────────────────────────────────────────────────
      lines.push(theme.fg('accent', theme.bold('  Football Betting Board  ')));
      lines.push(theme.fg('dim', `  Phase: ${boardPhase}`));
      lines.push(theme.fg('dim', `  Preset: ${activePreset || 'default'} · Members: ${getActiveMembers().length}`));
      lines.push(theme.fg('dim', `  ${'─'.repeat(52)}`));

      if (boardPhase === 'framing' && directorFramingText.trim()) {
        const preview = directorFramingText.trim().split('\n').slice(0, 3);
        lines.push(theme.fg('muted', '  Director framing...'));
        for (const line of preview) lines.push(`  ${line}`);
      } else if (memberStates.length > 0) {
        for (const state of memberStates) {
          const color = state.status === 'done'
            ? 'success'
            : state.status === 'error'
              ? 'error'
              : state.status === 'running'
                ? 'accent'
                : 'dim';
          lines.push(theme.fg(color as any, `  ${renderStatusLine(state)}`));
        }
      } else {
        lines.push(theme.fg('muted', '  Idle. Use board_begin or board_discuss to start.'));
      }

      return {
        render(width: number) {
          return lines.map(line => truncateToWidth(line, width));
        },
        invalidate() {},
      };
    },
    { placement: 'belowEditor' },
  );
}

function runSubagent(
  systemPrompt: string,
  prompt: string,
  model: string,
  tools: string,
  onChunk?: (text: string) => void,
): Promise<RunResult> {
  const args = [
    '--mode', 'json',
    '-p',
    '--no-extensions',
  ];

  if (model?.trim()) {
    args.push('--model', model.trim());
  }

  if (tools === 'none') {
    args.push('--no-tools');
  } else if (tools?.trim()) {
    args.push('--tools', tools.trim());
  }

  args.push(
    '--thinking', 'off',
    '--append-system-prompt', systemPrompt,
    '--no-session',
    prompt,
  );

  return new Promise(resolve => {
    const start = Date.now();
    const proc = spawn('pi', args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    const chunks: string[] = [];
    let buffer = '';

    proc.stdout.setEncoding('utf-8');
    proc.stdout.on('data', (chunk: string) => {
      buffer += chunk;
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.type === 'message_update') {
            const delta = event.assistantMessageEvent;
            if (delta?.type === 'text_delta') {
              const text = delta.delta || '';
              chunks.push(text);
              onChunk?.(text);
            }
          }

          if ((event.type === 'turn_end' || event.type === 'message_end') && !chunks.length) {
            const msg = event.message;
            const content = Array.isArray(msg?.content) ? msg.content : [];
            const text = content
              .filter((item: { type?: string; text?: string }) => item.type === 'text')
              .map((item: { text?: string }) => item.text || '')
              .join('');
            if (text) chunks.push(text);
          }

          if (event.type === 'agent_turn_complete' && !chunks.length) {
            const content = event.result?.content || [];
            const text = content
              .filter((item: { type?: string; text?: string }) => item.type === 'text')
              .map((item: { text?: string }) => item.text || '')
              .join('');
            if (text) chunks.push(text);
          }
        } catch {
          // ignore malformed event lines
        }
      }
    });

    proc.on('close', code => {
      resolve({
        output: chunks.join('').trim(),
        exitCode: code ?? 0,
        elapsed: Math.max(1, Math.round((Date.now() - start) / 1000)),
      });
    });

    proc.on('error', err => {
      resolve({
        output: `Error: ${String(err)}`,
        exitCode: 1,
        elapsed: Math.max(1, Math.round((Date.now() - start) / 1000)),
      });
    });
  });
}

function buildHtmlReport(title: string, memo: string, briefText: string, preset: string, members: string[]) {
  const body = escapeHtml(memo).replace(/\n/g, '<br>');
  const brief = escapeHtml(briefText).replace(/\n/g, '<br>');
  return `<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; background: #0b1020; color: #e5e7eb; font: 16px/1.7 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    .wrap { max-width: 980px; margin: 0 auto; padding: 40px 24px 80px; }
    .card { background: #111827; border: 1px solid #243042; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    h1, h2 { margin: 0 0 16px; }
    .meta { color: #9ca3af; font-size: 14px; }
    .pill { display: inline-block; border: 1px solid #334155; border-radius: 999px; padding: 4px 10px; margin-right: 8px; }
    code { background: #0f172a; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>${escapeHtml(title)}</h1>
      <div class="meta">
        <span class="pill">Preset: ${escapeHtml(preset)}</span>
        <span class="pill">Members: ${escapeHtml(members.join(', '))}</span>
      </div>
    </div>
    <div class="card">
      <h2>Brief</h2>
      <div>${brief}</div>
    </div>
    <div class="card">
      <h2>Board Report</h2>
      <div>${body}</div>
    </div>
  </div>
</body>
</html>
`;
}

function formatHistory(
  history: Array<{ speaker: string; content: string; timestamp: number }>,
): string {
  if (history.length === 0) return '（尚無討論記錄）';
  return history
    .map((entry, i) => {
      const speakerLabel =
        entry.speaker === 'user'
          ? '👤 人類委員（Human Board Member）'
          : entry.speaker === 'director'
            ? '🏛 Director（Board Chair）'
            : `📊 ${displayName(entry.speaker)}`;
      return `[${i + 1}] ${speakerLabel}\n${entry.content}`;
    })
    .join('\n\n---\n\n');
}

export default function (pi: ExtensionAPI) {
  // ── Discussion Mode State ──────────────────────────────────────────────────

  interface DiscussionEntry {
    speaker: string; // 'director' | 'user' | member name
    content: string;
    timestamp: number;
  }

  interface DiscussionSession {
    active: boolean;
    brief: string;
    directorFrame: string;
    history: DiscussionEntry[];
    activeMembers: BoardMemberConfig[];
    memberDefs: Map<string, MemberDef>;
    speakOrder: string[];
    nextSpeakerIdx: number;
    directorModel: string;
    sharedKnowledge: string;
    preset: string;
  }

  let discussionSession: DiscussionSession | null = null;

  // ── board_begin Tool (Mode A — Full Auto) ──────────────────────────────────

  pi.registerTool({
    name: 'board_begin',
    label: 'Board Begin',
    description: '召開足球博彩情報中心，讓多位專家並行分析賽事 brief，輸出最終投注報告。',
    parameters: Type.Object({
      brief: Type.String({
        description: '分析 brief 文字（markdown）或 .md 檔案路徑，應包含賽事、時間、市場與問題。',
      }),
      preset: Type.Optional(Type.String({
        description: '可選 preset：full / pre-match / live / value-scan / quick / risk-review / deep-analysis / cloudbet-ready',
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };
      const rawBriefText = resolveBrief(brief);

      if (!rawBriefText) {
        return {
          content: [{ type: 'text', text: `Brief 檔案未找到：${resolve(cwd, brief)}` }],
          details: { status: 'error' },
        };
      }

      const briefText = await enrichBriefWithAutoFixtures(rawBriefText);

      if (preset) activePreset = preset;
      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return {
          content: [{ type: 'text', text: '沒有活躍委員。請檢查 .pi/football-betting-board/config.yaml。' }],
          details: { status: 'error' },
        };
      }

      const missing = activeMembers.filter(member => !existsSync(resolve(cwd, member.path)));
      if (missing.length > 0) {
        return {
          content: [{
            type: 'text',
            text: `缺少 agent 檔案：\n${missing.map(m => `  • ${m.name}: ${m.path}`).join('\n')}`,
          }],
          details: { status: 'error' },
        };
      }

      const memberDefs = new Map<string, MemberDef>();
      for (const member of activeMembers) {
        const def = parseMemberFile(resolve(cwd, member.path));
        if (def) memberDefs.set(member.name, def);
      }

      const director = memberDefs.get('director');
      if (!director) {
        return {
          content: [{ type: 'text', text: '找不到 director 定義，無法主持會議。' }],
          details: { status: 'error' },
        };
      }

      memberStates = activeMembers.map(member => ({
        name: member.name,
        status: 'pending',
        elapsed: 0,
        lastWork: '',
      }));
      boardPhase = 'framing';
      directorFramingText = '';
      updateWidget();

      onUpdate?.({
        content: [{ type: 'text', text: `Director 正在框架問題，接著將交由 ${activeMembers.length} 位委員分析...` }],
        details: { status: 'running', phase: 'framing' },
      });

      const sharedKnowledge = loadBoardKnowledge();
      const framingPrompt =
        `閱讀以下足球博彩 brief，先完成本次委員會分析框架。\n` +
        `若 brief 內含 Auto Fixture Discovery 候選賽程，你必須先明確選出本次要深入分析的具體 fixtures（例如 3-5 場），` +
        `不可停留在抽象聯賽層級。\n\n` +
        `請明確指出：\n` +
        `1. 本次最終選定的目標賽事與關鍵市場\n` +
        `2. 哪些不確定性最重要\n` +
        `3. 各委員應該分別回答什麼問題\n` +
        `4. 最後應如何決定是否下注、下哪個市場、以及倉位大小\n\n` +
        `Brief：\n${briefText}\n\n` +
        `請用繁體中文，200-350 字，直接清楚。`;

      const framing = await runSubagent(
        `${director.systemPrompt}${sharedKnowledge}${loadMemberKnowledge(director)}`,
        framingPrompt,
        director.model,
        'none',
        chunk => {
          directorFramingText += chunk;
          updateWidget();
        },
      );

      const directorFrame = framing.output || 'Director framing failed.';

      boardPhase = 'deliberating';
      updateWidget();
      onUpdate?.({
        content: [{ type: 'text', text: '委員會並行分析中...' }],
        details: { status: 'running', phase: 'deliberating' },
      });

      const results = await Promise.all(activeMembers.map(async (member, index) => {
        const def = memberDefs.get(member.name);
        if (!def) {
          memberStates[index].status = 'error';
          memberStates[index].lastWork = 'Agent definition missing';
          updateWidget();
          return { name: member.name, output: 'Agent definition missing', error: true };
        }

        memberStates[index].status = 'running';
        updateWidget();

        const prompt =
          `你正在參與 Football Betting Board。\n\n` +
          `## Director Framing\n${directorFrame}\n\n` +
          `## Original Brief\n${briefText}\n\n` +
          `請只從你的角色專業出發，產出一份可供 Director 整合的分析。\n` +
          `要求：\n` +
          `- 嚴禁虛構數字；若工具或資料不足，必須明說\n` +
          `- 若有數據或盤口，請附來源或計算方式\n` +
          `- 最後用 2-4 點列出你對下注與否的結論\n` +
          `- 全程繁體中文\n`;

        const result = await runSubagent(
          `${def.systemPrompt}${sharedKnowledge}${loadMemberKnowledge(def)}`,
          prompt,
          def.model,
          def.tools,
        );

        memberStates[index].status = result.exitCode === 0 ? 'done' : 'error';
        memberStates[index].elapsed = result.elapsed;
        memberStates[index].lastWork = result.output.slice(0, 120);
        updateWidget();

        return {
          name: member.name,
          output: result.output || '(無輸出)',
          error: result.exitCode !== 0,
        };
      }));

      boardPhase = 'synthesizing';
      updateWidget();
      onUpdate?.({
        content: [{ type: 'text', text: 'Director 正在整合最終投注報告...' }],
        details: { status: 'running', phase: 'synthesizing' },
      });

      const validResults = results.filter(result => !result.error);
      const resultText = validResults
        .map(result => `## ${displayName(result.name)}\n${result.output}`)
        .join('\n\n');
      const failures = results.length - validResults.length;
      const failureNote = failures > 0
        ? `\n\n注意：有 ${failures} 位委員執行失敗，整合時請明確標註資料缺口。`
        : '';

      const synthesisPrompt =
        `你是足球博彩情報中心總監（Director）。\n\n` +
        `根據 brief、你的 framing、以及各委員輸出，撰寫一份最終投注決策報告。\n\n` +
        `## Original Brief\n${briefText}\n\n` +
        `## Director Framing\n${directorFrame}\n\n` +
        `## Member Reports\n${resultText}\n\n` +
        `請用以下結構輸出：\n` +
        `## Final Decision\n` +
        `## Best Market To Bet\n` +
        `## Price Thresholds\n` +
        `## Evidence Summary\n` +
        `## Risks & Invalidations\n` +
        `## Stake Plan\n` +
        `## Member Stances\n` +
        `## Next Actions\n\n` +
        `規則：\n` +
        `- 若資訊不足或 edge 不成立，要明確說「不下注 / 等待更好價格」\n` +
        `- 不得虛構賠率、機率、EV\n` +
        `- 要明確分辨已驗證數據 vs 待確認假設\n` +
        `- 全程繁體中文，章節標題維持英文${failureNote}`;

      const synthesis = await runSubagent(
        `${director.systemPrompt}${sharedKnowledge}${loadMemberKnowledge(director)}`,
        synthesisPrompt,
        director.model,
        'none',
      );

      const memo = synthesis.output || 'Director 無法產出最終報告。';
      const memosDir = join(cwd, '.pi', 'football-betting-board', 'memos');
      mkdirSync(memosDir, { recursive: true });

      const firstLine = briefText.split('\n').find(line => line.trim()) || 'football-betting-report';
      const slug = slugify(firstLine.replace(/^#+\s*/, '')) || 'football-betting-report';
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const mdPath = join(memosDir, `${slug}-${timestamp}.md`);
      const htmlPath = mdPath.replace(/\.md$/, '.html');

      const presetLabel = preset || activePreset || 'default';
      const memoContent =
        `# Football Betting Board Report\n\n` +
        `**Date:** ${new Date().toISOString().slice(0, 10)}\n` +
        `**Preset:** ${presetLabel}\n` +
        `**Members:** ${activeMembers.map(member => displayName(member.name)).join(', ')}\n\n` +
        `---\n\n` +
        `## Brief\n\n${briefText}\n\n` +
        `---\n\n` +
        `## Director Framing\n\n${directorFrame}\n\n` +
        `---\n\n` +
        `## Member Reports\n\n${resultText}\n\n` +
        `---\n\n` +
        `${memo}\n`;

      writeFileSync(mdPath, memoContent);
      writeFileSync(
        htmlPath,
        buildHtmlReport(
          'Football Betting Board Report',
          memo,
          briefText,
          presetLabel,
          activeMembers.map(member => displayName(member.name)),
        ),
      );

      boardPhase = 'idle';
      directorFramingText = '';
      updateWidget();

      return {
        content: [{
          type: 'text',
          text:
            `足球博彩情報中心分析完成。\n\n` +
            `Preset: ${presetLabel}\n` +
            `成員: ${activeMembers.map(member => displayName(member.name)).join(', ')}\n\n` +
            `${memo}\n\n` +
            `Markdown: ${mdPath}\nHTML: ${htmlPath}`,
        }],
        details: {
          status: 'success',
          mdPath,
          htmlPath,
          preset: presetLabel,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const presetLabel = a.preset ? ` [${a.preset}]` : '';
      const briefPreview = (a.brief || '').slice(0, 50).replace(/\n/g, ' ');
      const preview = briefPreview.length > 47 ? briefPreview.slice(0, 47) + '...' : briefPreview;
      return new Text(
        theme.fg('toolTitle', theme.bold('board_begin')) +
        theme.fg('accent', presetLabel) +
        theme.fg('dim', ' — ') +
        theme.fg('muted', preview),
        0, 0,
      );
    },

    renderResult(result, options, theme) {
      const details = result.details as any;
      if (!details) {
        const text = result.content[0];
        return new Text(text?.type === 'text' ? text.text : '', 0, 0);
      }

      if (options.isPartial || details.status === 'running') {
        const phase = details.phase || 'running';
        const phaseZh = phase === 'framing' ? 'Director 框架中'
          : phase === 'deliberating' ? '委員分析中'
            : phase === 'synthesizing' ? '整合報告中' : phase;
        return new Text(
          theme.fg('accent', `● football-betting-board`) +
          theme.fg('dim', ` ${phaseZh}...`),
          0, 0,
        );
      }

      if (details.status === 'error') {
        return new Text(theme.fg('error', `✗ board_begin 失敗`), 0, 0);
      }

      const header =
        theme.fg('success', `✓ football-betting-board`) +
        theme.fg('dim', ` · ${details.preset || 'default'}`) +
        theme.fg('muted', ` · ${details.mdPath || ''}`);

      return new Text(header, 0, 0);
    },
  });

  // ── board_discuss Tool (Mode B — Interactive Discussion) ────────────────────

  pi.registerTool({
    name: 'board_discuss',
    label: 'Board Discuss',
    description:
      '開始互動討論模式。用戶作為「人類委員」坐入委員會，Director 框架後第一位委員發言，' +
      '之後用 board_next 輪流發言，最後用 board_report 生成報告。',
    parameters: Type.Object({
      brief: Type.String({
        description: '分析 brief 文字（markdown）或 .md 檔案路徑',
      }),
      preset: Type.Optional(Type.String({
        description: '可選 preset：full / pre-match / live / value-scan / quick / risk-review / deep-analysis / cloudbet-ready',
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };
      const rawBriefText = resolveBrief(brief);

      if (!rawBriefText) {
        return {
          content: [{ type: 'text', text: `Brief 檔案未找到：${resolve(cwd, brief)}` }],
          details: { status: 'error' },
        };
      }

      const briefText = await enrichBriefWithAutoFixtures(rawBriefText);

      if (preset) activePreset = preset;
      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return {
          content: [{ type: 'text', text: '沒有活躍委員。請檢查 config.yaml 或選擇一個 preset。' }],
          details: { status: 'error' },
        };
      }

      const missing = activeMembers.filter(member => !existsSync(resolve(cwd, member.path)));
      if (missing.length > 0) {
        return {
          content: [{ type: 'text', text: `缺少 agent 檔案：\n${missing.map(m => `  • ${m.name}: ${m.path}`).join('\n')}` }],
          details: { status: 'error' },
        };
      }

      const memberDefs = new Map<string, MemberDef>();
      for (const member of activeMembers) {
        const def = parseMemberFile(resolve(cwd, member.path));
        if (def) memberDefs.set(member.name, def);
      }

      const director = memberDefs.get('director');
      if (!director) {
        return {
          content: [{ type: 'text', text: '找不到 director 定義，無法主持會議。' }],
          details: { status: 'error' },
        };
      }

      const directorModel = director.model;
      const sharedKnowledge = loadBoardKnowledge();

      // Director framing
      boardPhase = 'framing';
      directorFramingText = '';
      memberStates = [];
      updateWidget();

      onUpdate?.({
        content: [{ type: 'text', text: '🏛 Director 框架問題中...' }],
        details: { status: 'running', phase: 'framing' },
      });

      const directorSystemPrompt =
        `你是足球博彩情報中心（Football Betting Board）的總監（Director）。` +
        `你負責框架博彩分析問題並整合委員意見。` +
        sharedKnowledge;

      const framingPrompt =
        `閱讀以下足球博彩 brief，為委員會框架此次分析。識別：\n` +
        `1. 目標賽事和關鍵市場\n` +
        `2. 核心問題和分析框架\n` +
        `3. 各委員應聚焦的面向\n` +
        `4. 哪些不確定性最影響下注決策\n\n` +
        `注意：此次為互動討論模式，人類委員也將參與討論。請框架時留下開放問題供討論。\n\n` +
        `Brief：\n${briefText}\n\n` +
        `輸出框架分析 200-350 字，語氣直接清晰。全程繁體中文。`;

      const framing = await runSubagent(
        `${directorSystemPrompt}${loadMemberKnowledge(director)}`,
        framingPrompt,
        directorModel,
        'none',
        chunk => {
          directorFramingText += chunk;
          updateWidget();
        },
      );
      const directorFrame = framing.output || 'Director framing failed.';

      // Select first non-director member
      const nonDirectorMembers = activeMembers.filter(m => m.name !== 'director');
      const speakOrder = nonDirectorMembers.map(m => m.name);
      const firstName = speakOrder[0];
      const firstMember = nonDirectorMembers[0];
      const firstDef = memberDefs.get(firstName);

      onUpdate?.({
        content: [{ type: 'text', text: `📊 ${displayName(firstName)} 發言中...` }],
        details: { status: 'running', phase: 'discussing' },
      });

      let firstOutput = `（${displayName(firstName)} agent 未找到）`;
      if (firstDef && firstMember) {
        const firstPrompt =
          `Director 框架：\n${directorFrame}\n\n` +
          `原始 Brief：\n${briefText}\n\n` +
          `現在是互動討論模式的第一輪發言。輪到你（${displayName(firstName)}）率先發言。\n` +
          `請基於 Director 框架和 Brief，給出你的初步分析。\n` +
          `格式：立場 → 關鍵論點 → 主要顧慮 → 你想問其他委員或人類委員的一個問題\n\n` +
          `重要：全程繁體中文。200-350 字。嚴禁虛構數據。`;

        const result = await runSubagent(
          `${firstDef.systemPrompt}${sharedKnowledge}${loadMemberKnowledge(firstDef)}`,
          firstPrompt,
          firstDef.model,
          firstDef.tools,
        );
        firstOutput = result.output || `（${displayName(firstName)} 無輸出，exit ${result.exitCode}）`;
      }

      // Initialize discussion session
      const history: DiscussionEntry[] = [
        { speaker: 'director', content: directorFrame, timestamp: Date.now() },
        { speaker: firstName, content: firstOutput, timestamp: Date.now() },
      ];

      discussionSession = {
        active: true,
        brief: briefText,
        directorFrame,
        history,
        activeMembers,
        memberDefs,
        speakOrder,
        nextSpeakerIdx: 1,
        directorModel,
        sharedKnowledge,
        preset: preset || activePreset || 'custom',
      };

      boardPhase = 'idle';
      updateWidget();

      const remainingNames = speakOrder.slice(1).map(displayName).join(', ');
      const output =
        `## 🏛 足球博彩情報中心 — 互動討論模式已開始\n\n` +
        `### Director 框架\n\n${directorFrame}\n\n` +
        `---\n\n` +
        `### 📊 ${displayName(firstName)}（第一位發言）\n\n${firstOutput}\n\n` +
        `---\n\n` +
        `**你可以：**\n` +
        `- 直接回應上述觀點，然後用 \`board_next\` 繼續（在 \`context\` 參數填入你的回應）\n` +
        `- 用 \`board_next member="委員名稱"\` 指定下一位發言\n` +
        `- 用 \`board_report\` 結束討論並生成最終報告\n\n` +
        `待發言委員：${remainingNames || '（全部已發言）'}`;

      return {
        content: [{ type: 'text', text: output }],
        details: {
          status: 'discussing',
          directorFrame,
          firstSpeaker: firstName,
          speakOrder,
          remainingCount: speakOrder.length - 1,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const presetLabel = a.preset ? ` [${a.preset}]` : '';
      const briefPreview = (a.brief || '').slice(0, 50).replace(/\n/g, ' ');
      const preview = briefPreview.length > 47 ? briefPreview.slice(0, 47) + '...' : briefPreview;

      return new Text(
        theme.fg('toolTitle', theme.bold('board_discuss')) +
        theme.fg('accent', presetLabel) +
        theme.fg('dim', ' — ') +
        theme.fg('muted', preview),
        0, 0,
      );
    },

    renderResult(result, options, theme) {
      const details = result.details as any;
      if (!details) {
        const text = result.content[0];
  
        return new Text(text?.type === 'text' ? text.text : '', 0, 0);
      }
      if (options.isPartial || details.status === 'running') {
        const phase = details.phase || 'running';
        const phaseZh = phase === 'framing' ? 'Director 框架中' : phase === 'discussing' ? '委員發言中' : phase;
  
        return new Text(
          theme.fg('accent', `● board_discuss`) + theme.fg('dim', ` ${phaseZh}...`),
          0, 0,
        );
      }
      if (details.status === 'error') {
  
        return new Text(theme.fg('error', `✗ board_discuss 失敗`), 0, 0);
      }

      return new Text(
        theme.fg('success', `✓ board_discuss 互動討論已開始`) +
        theme.fg('dim', ` · 首位：${displayName(details.firstSpeaker || '')} · 待發言：${details.remainingCount || 0} 位`),
        0, 0,
      );
    },
  });

  // ── board_next Tool ─────────────────────────────────────────────────────────

  pi.registerTool({
    name: 'board_next',
    label: 'Board Next',
    description:
      '在互動討論模式中，讓下一位或指定委員發言。需先呼叫 board_discuss 開始討論。',
    parameters: Type.Object({
      member: Type.Optional(Type.String({
        description: '指定委員名稱（如 data-scout、odds-tracker 等）。不填則自動選下一位未發言的委員。',
      })),
      context: Type.Optional(Type.String({
        description: '你對上一位委員發言的回應或補充觀點。會被記錄為人類委員發言並轉達給接下來的委員。',
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { member, context } = params as { member?: string; context?: string };

      if (!discussionSession?.active) {
        return {
          content: [{ type: 'text', text: '目前沒有進行中的互動討論。請先呼叫 board_discuss 開始討論。' }],
          details: { status: 'error' },
        };
      }

      const sess = discussionSession;

      // Record user response if provided
      if (context?.trim()) {
        sess.history.push({
          speaker: 'user',
          content: context.trim(),
          timestamp: Date.now(),
        });
        updateWidget();
      }

      // Determine target speaker
      let targetName: string | undefined;
      if (member) {
        targetName = sess.speakOrder.find(n =>
          n === member || n.includes(member) || displayName(n).toLowerCase().includes(member.toLowerCase()),
        );
        if (!targetName) {
          return {
            content: [{ type: 'text', text: `找不到委員「${member}」。可用委員：${sess.speakOrder.map(displayName).join(', ')}` }],
            details: { status: 'error' },
          };
        }
      } else {
        if (sess.nextSpeakerIdx >= sess.speakOrder.length) {
          return {
            content: [{ type: 'text', text: '所有委員都已發言。你可以繼續指定特定委員補充發言，或用 board_report 生成最終報告。' }],
            details: { status: 'all_spoken' },
          };
        }
        targetName = sess.speakOrder[sess.nextSpeakerIdx];
        sess.nextSpeakerIdx++;
      }

      const targetMember = sess.activeMembers.find(m => m.name === targetName);
      const targetDef = sess.memberDefs.get(targetName);

      if (!targetDef || !targetMember) {
        return {
          content: [{ type: 'text', text: `無法載入委員 ${targetName} 的定義。` }],
          details: { status: 'error' },
        };
      }

      onUpdate?.({
        content: [{ type: 'text', text: `📊 ${displayName(targetName!)} 發言中...` }],
        details: { status: 'running' },
      });

      // Build prompt with full history
      const historyText = formatHistory(sess.history);
      const memberPrompt =
        `Director 框架：\n${sess.directorFrame}\n\n` +
        `原始 Brief：\n${sess.brief}\n\n` +
        `委員會討論歷史：\n${historyText}\n\n` +
        `現在輪到你（${displayName(targetName!)}）發言。\n` +
        `請基於以上討論，給出你的分析並回應已提出的觀點（包括人類委員的觀點，若有）。\n` +
        `格式：立場 → 關鍵論點 → 主要顧慮 → 對之前觀點的回應\n\n` +
        `重要：全程繁體中文。200-350 字。嚴禁虛構數據。`;

      let result;
      try {
        result = await runSubagent(
          `${targetDef.systemPrompt}${sess.sharedKnowledge}${loadMemberKnowledge(targetDef)}`,
          memberPrompt,
          targetDef.model,
          targetDef.tools,
        );
      } catch (err) {
        return {
          content: [{ type: 'text', text: `${displayName(targetName!)} 子進程錯誤：${String(err)}` }],
          details: { status: 'error' },
        };
      }

      if (result.exitCode !== 0 && !result.output) {
        return {
          content: [{ type: 'text', text: `${displayName(targetName!)} 執行失敗（exit ${result.exitCode}）：${result.output || '無輸出'}` }],
          details: { status: 'error' },
        };
      }

      // Record speech
      sess.history.push({
        speaker: targetName!,
        content: result.output,
        timestamp: Date.now(),
      });
      updateWidget();

      // Count spoken
      const spokenSet = new Set(
        sess.history.filter(e => e.speaker !== 'user' && e.speaker !== 'director').map(e => e.speaker),
      );
      const remainingMembers = sess.speakOrder.filter(n => !spokenSet.has(n));
      const allSpoken = remainingMembers.length === 0;

      const nextHint = allSpoken
        ? '\n\n所有委員都已發言。輸入 `board_report` 生成最終報告，或繼續用 `board_next member="委員名稱"` 補充發言。'
        : `\n\n待發言委員：${remainingMembers.map(displayName).join(', ')}\n繼續用 \`board_next\` 讓下一位發言，或用 \`board_next member="委員名稱"\` 指定委員。`;

      const userNoteShown = context?.trim() ? '\n**（已記錄你的回應）**\n\n' : '\n\n';

      return {
        content: [{ type: 'text', text: `### 📊 ${displayName(targetName!)}\n\n${userNoteShown}${result.output}${nextHint}` }],
        details: { status: 'ok', speaker: targetName },
      };
    },

    renderCall(args, theme) {
      const a = args as any;

      const memberLabel = a.member ? ` → ${displayName(a.member)}` : '';
      return new Text(
        theme.fg('toolTitle', theme.bold('board_next')) +
        theme.fg('accent', memberLabel),
        0, 0,
      );
    },

    renderResult(result, options, theme) {
      const details = result.details as any;
      if (options.isPartial || (details?.status === 'running')) {
  
        return new Text(theme.fg('accent', `● board_next`) + theme.fg('dim', ' 委員發言中...'), 0, 0);
      }
      if (details?.status === 'all_spoken') {
  
        return new Text(theme.fg('success', '✓ 所有委員已發言') + theme.fg('dim', ' — 可 board_report 生成報告'), 0, 0);
      }

      return new Text(
        theme.fg('success', `✓ ${displayName(details?.speaker || '')}`) + theme.fg('dim', ' 發言完成'),
        0, 0,
      );
    },
  });

  // ── board_report Tool ──────────────────────────────────────────────────────

  pi.registerTool({
    name: 'board_report',
    label: 'Board Report',
    description:
      '結束互動討論模式，由 Director 整合所有發言（含人類委員觀點）生成最終投注報告。' +
      '輸出 -discussion 後綴的 .md 和 .html 報告。',
    parameters: Type.Object({
      user_final_take: Type.Optional(Type.String({
        description: '你作為人類委員的最後總結或最終立場（可選）。會被納入報告。',
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { user_final_take } = params as { user_final_take?: string };

      if (!discussionSession?.active) {
        return {
          content: [{ type: 'text', text: '目前沒有進行中的互動討論。請先呼叫 board_discuss 開始討論。' }],
          details: { status: 'error' },
        };
      }

      const sess = discussionSession;

      // Record user final take if provided
      if (user_final_take?.trim()) {
        sess.history.push({
          speaker: 'user',
          content: `【人類委員最終總結】\n${user_final_take.trim()}`,
          timestamp: Date.now(),
        });
      }

      onUpdate?.({
        content: [{ type: 'text', text: '🏛 Director 整合所有討論生成最終報告中...' }],
        details: { status: 'running', phase: 'synthesizing' },
      });

      boardPhase = 'synthesizing';
      updateWidget();

      const historyText = formatHistory(sess.history);

      // Build board results for HTML report
      const boardResults: { name: string; stance: string; error: boolean }[] = sess.speakOrder
        .map(name => {
          const entries = sess.history.filter(e => e.speaker === name);
          if (entries.length === 0) return { name, stance: '（未發言）', error: true };
          return { name, stance: entries.map(e => e.content).join('\n\n'), error: false };
        });

      const userEntries = sess.history.filter(e => e.speaker === 'user');
      const userContributions = userEntries.length > 0
        ? `\n\n## 人類委員（Human Board Member）貢獻\n\n${userEntries.map(e => e.content).join('\n\n---\n\n')}`
        : '';

      const validResults = boardResults.filter(r => !r.error);
      const resultText = validResults
        .map(r => `## ${displayName(r.name)}\n${r.stance}`)
        .join('\n\n');
      const failures = boardResults.length - validResults.length;
      const failureNote = failures > 0
        ? `\n\n注意：有 ${failures} 位委員執行失敗，整合時請明確標註資料缺口。`
        : '';

      const directorSystemPrompt =
        `你是足球博彩情報中心（Football Betting Board）的總監（Director）。` +
        `你負責框架博彩分析問題並整合委員意見。` +
        sess.sharedKnowledge;

      const synthesisPrompt =
        `你是足球博彩情報中心的總監（Director）。\n\n` +
        `根據原始 brief 和完整互動討論，撰寫最終投注決策報告。\n\n` +
        `Brief：\n${sess.brief}\n\n` +
        `Director 框架：\n${sess.directorFrame}\n\n` +
        `完整討論歷史：\n${historyText}\n\n` +
        `注意：此次為互動討論模式，人類委員也參與了討論，請特別注意人類委員提出的觀點。\n\n` +
        `請用以下結構輸出：\n` +
        `## Final Decision\n` +
        `## Best Market To Bet\n` +
        `## Price Thresholds\n` +
        `## Evidence Summary\n` +
        `## Risks & Invalidations\n` +
        `## Stake Plan\n` +
        `## Member Stances\n` +
        `[每位委員一段：立場 + 關鍵論點 + 主要顧慮；並包含人類委員的觀點摘要]\n\n` +
        `## Next Actions\n` +
        `## Deliberation Summary\n` +
        `[互動討論如何展開，人類委員的參與如何影響了最終判斷]\n\n` +
        `規則：\n` +
        `- 若資訊不足或 edge 不成立，要明確說「不下注 / 等待更好價格」\n` +
        `- 不得虛構賠率、機率、EV\n` +
        `- 全程繁體中文，章節標題維持英文${failureNote}`;

      const synthesis = await runSubagent(
        `${directorSystemPrompt}${loadMemberKnowledge(sess.memberDefs.get('director')!)}`,
        synthesisPrompt,
        sess.directorModel,
        'none',
      );

      const memo = synthesis.output || 'Director 無法產出最終報告。';

      // Save report
      const memosDir = join(cwd, '.pi', 'football-betting-board', 'memos');
      mkdirSync(memosDir, { recursive: true });

      const firstLine = sess.brief.split('\n').find(l => l.trim()) || 'football-betting-report';
      const slug = slugify(firstLine.replace(/^#+\s*/, '')) || 'football-betting-report';
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const mdPath = join(memosDir, `${slug}-${timestamp}-discussion.md`);
      const htmlPath = mdPath.replace(/\.md$/, '.html');

      const memoContent =
        `# Football Betting Board Report（互動討論模式）\n\n` +
        `**Date:** ${new Date().toISOString().slice(0, 10)}\n` +
        `**Mode:** 互動討論（Mode B）\n` +
        `**Preset:** ${sess.preset}\n` +
        `**Members:** ${sess.activeMembers.map(m => displayName(m.name)).join(', ')}\n` +
        `**Rounds:** ${sess.history.length}\n` +
        `**Human Contributions:** ${userEntries.length}\n\n` +
        `---\n\n` +
        `## Brief\n\n${sess.brief}\n\n` +
        `---\n\n` +
        `## Director Framing\n\n${sess.directorFrame}\n\n` +
        `---\n\n` +
        `## Discussion History\n\n${historyText}\n\n` +
        `---\n\n` +
        `## Member Reports（彙整）\n\n${resultText}${userContributions}\n\n` +
        `---\n\n` +
        `${memo}\n`;

      writeFileSync(mdPath, memoContent, 'utf-8');

      // Generate HTML
      const htmlBoardResults = [
        ...boardResults,
        ...(userEntries.length > 0 ? [{
          name: 'human-board-member',
          stance: userEntries.map(e => e.content).join('\n\n---\n\n'),
          error: false,
        }] : []),
      ];

      writeFileSync(
        htmlPath,
        buildHtmlReport(
          'Football Betting Board Report（互動討論）',
          memo,
          sess.brief,
          `${sess.preset} · 互動討論模式`,
          [
            ...sess.activeMembers.map(m => displayName(m.name)),
            ...(userEntries.length > 0 ? ['Human Board Member'] : []),
          ],
        ),
      );

      // Clear session
      discussionSession = null;
      boardPhase = 'done';
      updateWidget();

      const truncated = memo.length > 8000 ? memo.slice(0, 8000) + '\n\n... [截斷 — 請查看報告檔案]' : memo;

      return {
        content: [{ type: 'text', text: `報告已儲存：\n  📄 ${mdPath}\n  🌐 ${htmlPath}\n\n${truncated}` }],
        details: {
          status: 'done',
          memoPath: mdPath,
          htmlPath,
          preset: sess.preset,
          memberCount: sess.activeMembers.length,
          discussionRounds: sess.history.length,
          memo,
        },
      };
    },

    renderCall(_args, theme) {

      return new Text(
        theme.fg('toolTitle', theme.bold('board_report')) +
        theme.fg('dim', ' — 生成最終討論報告'),
        0, 0,
      );
    },

    renderResult(result, options, theme) {
      const details = result.details as any;
      if (!details) {
        const text = result.content[0];
  
        return new Text(text?.type === 'text' ? text.text : '', 0, 0);
      }
      if (options.isPartial || details.status === 'running') {
  
        return new Text(theme.fg('accent', `● board_report`) + theme.fg('dim', ' Director 整合報告中...'), 0, 0);
      }
      if (details.status === 'error') {
  
        return new Text(theme.fg('error', `✗ board_report 失敗`), 0, 0);
      }

      return new Text(
        theme.fg('success', `✓ 互動討論報告已生成`) +
        theme.fg('dim', ` · ${details.memberCount} 位委員 · ${details.discussionRounds} 輪對話 · `) +
        theme.fg('muted', details.memoPath || ''),
        0, 0,
      );
    },
  });

  // ── Commands ─────────────────────────────────────────────────────────────────

  pi.registerCommand('board-preset', {
    description: '選擇足球博彩委員會 preset',
    handler: async (_args, ctx) => {
      const presets = Object.keys(boardConfig.presets);
      if (presets.length === 0) {
        ctx.ui.notify('未定義任何 preset', 'warning');
        return;
      }

      const choice = await ctx.ui.select('選擇 Football Betting Board preset', presets);
      if (!choice) return;
      activePreset = choice;
      updateWidget();
      ctx.ui.notify(`已切換 preset：${choice}`, 'info');
    },
  });

  pi.registerCommand('board-status', {
    description: '顯示當前足球博彩委員會狀態',
    handler: async (_args, ctx) => {
      const active = getActiveMembers();
      const lines = [
        `Preset: ${activePreset || 'default'}`,
        `Active members: ${active.length}`,
        ...active.map(member => `- ${displayName(member.name)} (${member.name})`),
      ];
      ctx.ui.notify(lines.join('\n'), 'info');
    },
  });

  pi.registerCommand('board-history', {
    description: '查看最近的足球博彩報告',
    handler: async (_args, ctx) => {
      const memosDir = join(cwd, '.pi', 'football-betting-board', 'memos');
      if (!existsSync(memosDir)) {
        ctx.ui.notify('尚未產生任何報告', 'info');
        return;
      }

      const files = readdirSync(memosDir)
        .filter(file => file.endsWith('.md'))
        .sort()
        .reverse()
        .slice(0, 10);

      if (files.length === 0) {
        ctx.ui.notify('尚未產生任何報告', 'info');
        return;
      }

      const lines = files.map(file => {
        const hasHtml = existsSync(join(memosDir, file.replace(/\.md$/, '.html')));
        return `- ${file}${hasHtml ? ' 🌐' : ''}`;
      });
      ctx.ui.notify(`最近報告：\n\n${lines.join('\n')}\n\n📁 ${memosDir}`, 'info');
    },
  });

  pi.on('before_agent_start', async (_event, ctx) => {
    widgetCtx = ctx;
    loadConfig(ctx.cwd);

    const presetList = Object.keys(boardConfig.presets).join(', ') || '未定義';
    const active = getActiveMembers();
    const memberList = active.map(member => `- **${displayName(member.name)}**`).join('\n');

    return {
      systemPrompt:
        `你是 Football Betting Board 的主持人。\n\n` +
        `這是一個多代理足球博彩委員會系統，支援兩種分析模式：\n` +
        `- **Mode A — 全自動**：提交 brief → AI 全自動運行 → 輸出報告\n` +
        `- **Mode B — 互動討論**：用戶作為「人類委員」坐入委員會，與 AI 委員輪流討論\n\n` +
        `## 兩種分析模式\n\n` +
        `### Mode A — 全自動（board_begin）\n` +
        `用戶提交 brief → Director 框架 → 所有委員並行分析 → Director 整合輸出投注報告。\n\n` +
        `### Mode B — 互動討論（board_discuss → board_next → board_report）\n` +
        `用戶作為「人類委員」坐入委員會，與 AI 委員輪流討論。\n` +
        `- \`board_discuss\`：開始互動模式，Director 框架 + 第一位委員發言\n` +
        `- \`board_next\`：讓下一位委員發言（可在 context 填入你的回應）\n` +
        `- \`board_report\`：結束討論，生成報告（-discussion 後綴）\n\n` +
        `## 你的職責\n` +
        `當用戶要分析賽事時，先詢問偏好全自動模式還是互動討論模式：\n` +
        `1. **全自動模式**：呼叫 \`board_begin\` 即可\n` +
        `2. **互動討論模式**：先呼叫 \`board_discuss\`，然後引導用戶用 \`board_next\` 輪流討論\n\n` +
        `如果用戶沒有明確表示偏好：想快速得到報告選 Mode A；想深度參與討論選 Mode B。\n` +
        `如果用戶沒有提供具體 fixtures，但有提供聯賽、日期範圍、場數、風格，系統會自動找候選賽程。\n\n` +
        `## 當前配置\n` +
        `Preset: ${activePreset || 'default'}\n` +
        `活躍委員（${active.length}）：\n${memberList}\n\n` +
        `## 可用 Presets\n${presetList}\n` +
        `可用指令：/board-preset、/board-status、/board-history\n\n` +
        `## Brief 建議格式\n` +
        `- 賽事：聯賯 / 主隊 vs 客隊\n` +
        `- 開賽時間\n` +
        `- 目標市場：1X2 / Asian Handicap / Total Goals / BTTS 等\n` +
        `- 問題：例如是否有 value、是否該等盤、倉位怎麼配\n\n` +
        `**語言規則：永遠使用繁體中文（Traditional Chinese）與用戶溝通。技術術語、聯賽名、市場名可保留英文。**`,
    };
  });

  pi.on('session_start', async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);

    widgetCtx = ctx;
    activePreset = process.env.BOARD_PRESET || activePreset;
    boardPhase = 'idle';
    memberStates = [];
    directorFramingText = '';
    discussionSession = null;

    loadConfig(ctx.cwd);
    updateWidget();

    const active = getActiveMembers();
    const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 10), 10);

    ctx.ui.setStatus('football-betting-board', `Football Betting Board · ${active.length} 位委員活躍`);
    ctx.ui.notify(
      `Football Betting Board\n` +
        `${active.length} 位活躍委員 · ${time} 分鐘分析\n\n` +
        `Mode A（全自動）：board_begin\n` +
        `Mode B（互動討論）：board_discuss → board_next → board_report\n\n` +
        `/board-preset    選擇 preset\n` +
        `/board-status    顯示委員\n` +
        `/board-history   查看過往報告`,
      'info',
    );

    ctx.ui.setFooter((_tui, theme) => ({
      dispose: () => {},
      invalidate() {},
      render(width: number): string[] {
        const presetLabel = activePreset || 'default';
        const memberCount = getActiveMembers().length;
        const left =
          theme.fg('accent', 'football-board') +
          theme.fg('muted', ' · ') +
          theme.fg('dim', presetLabel) +
          theme.fg('muted', ' · ') +
          theme.fg('dim', `${memberCount} 位委員活躍`);
        const right = theme.fg('dim', ' board_begin / board_discuss');
        const pad = ' '.repeat(Math.max(1, width - visibleWidth(left) - visibleWidth(right)));
        return [truncateToWidth(left + pad + right, width)];
      },
    }));
  });
}
