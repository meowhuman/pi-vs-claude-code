import type { ExtensionAPI, ExtensionContext } from '@mariozechner/pi-coding-agent';
import {
  DEFAULT_MAX_BYTES,
  DEFAULT_MAX_LINES,
  formatSize,
  truncateHead,
} from '@mariozechner/pi-coding-agent';
import { StringEnum } from '@mariozechner/pi-ai';
import { Type } from '@sinclair/typebox';
import { applyExtensionDefaults } from './themeMap.ts';
import { mkdir, mkdtemp, readFile, readdir, rename, rm, stat, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const OUTPUT_FORMATS = ['txt', 'srt', 'vtt', 'json'] as const;
const WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large'] as const;
const SEARCH_SORTS = ['relevance', 'date', 'views', 'likes'] as const;
const TIME_FILTERS = ['today', 'week', 'month', 'year'] as const;
const WSP_KINDS = ['search', 'news', 'forum', 'china', 'geopolitics', 'trading', 'status'] as const;
const WSP_FORUMS = ['reddit', 'hackernews', 'lihkg', 'ptt', 'v2ex', 'stackoverflow', 'multi'] as const;
const WSP_NEWS_SOURCES = ['tech', 'finance', 'world', 'hk', 'china', 'ai', 'crypto'] as const;
const WSP_REGIONS = ['global', 'hk', 'us', 'uk', 'cn'] as const;
const WSP_GEO_TYPES = ['think_tanks', 'expert_commentary', 'academic', 'asia_pacific', 'middle_east'] as const;

function truncateText(text: string): string {
  const truncation = truncateHead(text, {
    maxBytes: DEFAULT_MAX_BYTES,
    maxLines: DEFAULT_MAX_LINES,
  });

  if (!truncation.truncated) return truncation.content;

  return `${truncation.content}\n\n[Output truncated: ${truncation.outputLines} of ${truncation.totalLines} lines (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)})]`;
}

function ensureTool(name: string, result: { code: number; stdout: string; stderr: string }) {
  if (result.code !== 0) {
    throw new Error(`${name} is required but not available. stderr: ${result.stderr || 'unknown error'}`);
  }
}

async function run(pi: ExtensionAPI, command: string, args: string[], ctx?: ExtensionContext) {
  const result = await pi.exec(command, args, { timeout: 1000 * 60 * 10 });
  if (ctx?.hasUI && result.code !== 0) {
    ctx.ui.notify(`${command} failed`, 'error');
  }
  return result;
}

async function requireYtDlp(pi: ExtensionAPI) {
  ensureTool('yt-dlp', await run(pi, 'yt-dlp', ['--version']));
}

async function requireFfmpeg(pi: ExtensionAPI) {
  ensureTool('ffmpeg', await run(pi, 'ffmpeg', ['-version']));
}

async function requireWhisper(pi: ExtensionAPI) {
  ensureTool('whisper', await run(pi, 'whisper', ['--help']));
}

function parseJsonLines(stdout: string): any[] {
  return stdout
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function sanitizeFilename(filename: string): string {
  const replaced = filename.replace(/[<>:"/\\|?*]/g, '_').trim();
  return replaced.length > 200 ? replaced.slice(0, 200) : replaced;
}

function normalizeOutputPath(outputFile: string, outputFormat: string): string {
  const ext = `.${outputFormat}`;
  if (outputFile.endsWith(ext)) return outputFile;
  return outputFile.replace(/\.[^.]+$/, '') + ext;
}

async function findGeneratedSubtitle(baseDir: string, stem: string, format: string) {
  const files = await readdir(baseDir);
  return files.find((file) => file.startsWith(`${stem}.`) && file.endsWith(`.${format}`));
}

async function getVideoInfo(pi: ExtensionAPI, url: string, extractorArgs?: string) {
  const args = ['--dump-json', '--no-playlist', '--no-check-certificate'];
  if (extractorArgs) args.push('--extractor-args', extractorArgs);
  args.push(url);
  const result = await run(pi, 'yt-dlp', args);
  if (result.code !== 0) {
    throw new Error(`Failed to get video info: ${result.stderr || result.stdout}`);
  }
  return JSON.parse(result.stdout);
}

async function listSubtitles(pi: ExtensionAPI, url: string, extractorArgs?: string) {
  const info = await getVideoInfo(pi, url, extractorArgs);
  return {
    title: info.title ?? 'Unknown',
    duration: info.duration ?? 0,
    manual: info.subtitles ?? {},
    automatic: info.automatic_captions ?? {},
    id: info.id,
    uploader: info.uploader,
  };
}

async function downloadSubtitle(
  pi: ExtensionAPI,
  url: string,
  outputFile: string,
  outputFormat: string,
  language?: string,
  includeAuto = false,
  extractorArgs?: string,
) {
  const outputPath = normalizeOutputPath(outputFile, outputFormat);
  const dir = path.dirname(outputPath);
  const stem = path.basename(outputPath, path.extname(outputPath));
  await mkdir(dir, { recursive: true });

  const formatMap: Record<string, string> = {
    txt: 'txt',
    srt: 'srt',
    vtt: 'vtt',
    json: 'json3',
  };
  const subFormat = formatMap[outputFormat] ?? 'srt';

  const args = [
    '--skip-download',
    '--write-sub',
    '--sub-format', subFormat,
    '--convert-subs', subFormat,
    '--no-check-certificate',
    '-o', path.join(dir, stem),
  ];

  if (extractorArgs) args.push('--extractor-args', extractorArgs);
  args.push('--sub-langs', language ?? 'all');
  if (includeAuto) args.push('--write-auto-sub');
  args.push(url);

  const result = await run(pi, 'yt-dlp', args);
  if (result.code !== 0) return { ok: false, stderr: result.stderr };

  const generated = await findGeneratedSubtitle(dir, stem, subFormat);
  if (!generated) return { ok: false, stderr: 'No subtitle file generated' };

  const generatedPath = path.join(dir, generated);
  if (generatedPath !== outputPath) {
    await rename(generatedPath, outputPath);
  }

  return { ok: true, path: outputPath };
}

async function downloadAudio(pi: ExtensionAPI, url: string, audioFile: string, extractorArgs?: string) {
  const args = [
    '-x',
    '--audio-format', 'wav',
    '--audio-quality', '0',
    '--postprocessor-args', 'ffmpeg:-ar 16000 -ac 1',
    '--no-check-certificate',
    '-o', audioFile,
  ];
  if (extractorArgs) args.push('--extractor-args', extractorArgs);
  args.push(url);
  const result = await run(pi, 'yt-dlp', args);
  if (result.code !== 0) {
    throw new Error(`Failed to download audio: ${result.stderr || result.stdout}`);
  }
}

async function transcribeAudio(
  pi: ExtensionAPI,
  audioFile: string,
  outputFile: string,
  outputFormat: string,
  model: string,
  language?: string,
  verbose?: boolean,
) {
  const outputPath = normalizeOutputPath(outputFile, outputFormat);
  await mkdir(path.dirname(outputPath), { recursive: true });

  const args = [
    audioFile,
    '--model', model,
    '--output_format', outputFormat,
    '--output_dir', path.dirname(outputPath),
  ];
  if (language) args.push('--language', language);
  if (!verbose) args.push('--verbose', 'False');

  const result = await run(pi, 'whisper', args);
  if (result.code !== 0) {
    throw new Error(`Whisper transcription failed: ${result.stderr || result.stdout}`);
  }

  const whisperOutput = path.join(
    path.dirname(outputPath),
    `${path.basename(audioFile, path.extname(audioFile))}.${outputFormat}`,
  );
  if (whisperOutput !== outputPath) {
    await rename(whisperOutput, outputPath);
  }
  return outputPath;
}

async function processVideo(
  pi: ExtensionAPI,
  params: {
    url: string;
    output_file: string;
    output_format: string;
    model: string;
    language?: string;
    prefer_subtitle?: boolean;
    verbose?: boolean;
    extractor_args?: string;
  },
) {
  await requireYtDlp(pi);
  await requireFfmpeg(pi);

  const outputPath = normalizeOutputPath(params.output_file, params.output_format);
  await mkdir(path.dirname(outputPath), { recursive: true });

  let method = 'subtitle';
  let subtitleAttempt = null as null | { ok: boolean; path?: string; stderr?: string };

  if (params.prefer_subtitle !== false) {
    subtitleAttempt = await downloadSubtitle(
      pi,
      params.url,
      outputPath,
      params.output_format,
      params.language,
      false,
      params.extractor_args,
    );

    if (!subtitleAttempt.ok) {
      subtitleAttempt = await downloadSubtitle(
        pi,
        params.url,
        outputPath,
        params.output_format,
        params.language,
        true,
        params.extractor_args,
      );
    }
  }

  if (!subtitleAttempt?.ok) {
    await requireWhisper(pi);
    method = 'whisper';
    const tempDir = await mkdtemp(path.join(os.tmpdir(), 'pi-youtube-'));
    const audioFile = path.join(tempDir, 'audio.%(ext)s');

    try {
      await downloadAudio(pi, params.url, audioFile, params.extractor_args);
      const wavFile = path.join(tempDir, 'audio.wav');
      await transcribeAudio(
        pi,
        wavFile,
        outputPath,
        params.output_format,
        params.model,
        params.language,
        params.verbose,
      );
    } finally {
      await rm(tempDir, { recursive: true, force: true });
    }
  }

  const content = await readFile(outputPath, 'utf8');
  const fileStat = await stat(outputPath);

  return {
    path: outputPath,
    method,
    size: fileStat.size,
    preview: truncateText(content),
  };
}

async function searchYoutube(
  pi: ExtensionAPI,
  query: string,
  count: number,
  sortBy: string,
  timeFilter?: string,
  extractorArgs?: string,
) {
  await requireYtDlp(pi);

  const prefixMap: Record<string, string> = {
    relevance: 'ytsearch',
    date: 'ytsearchdate',
    views: 'ytsearch',
    likes: 'ytsearch',
  };
  const prefix = prefixMap[sortBy] ?? 'ytsearch';
  const searchUrl = `${prefix}${count}:${query}`;

  let finalExtractorArgs = extractorArgs ?? '';
  if (timeFilter === 'week') {
    finalExtractorArgs = finalExtractorArgs
      ? `${finalExtractorArgs}:youtube-params=sp=CAI%253D`
      : 'youtube:youtube-params=sp=CAI%253D';
  }

  const args = ['--flat-playlist', '--dump-json', '--no-check-certificate', searchUrl];
  if (finalExtractorArgs) args.push('--extractor-args', finalExtractorArgs);

  const result = await run(pi, 'yt-dlp', args);
  if (result.code !== 0) {
    throw new Error(`YouTube search failed: ${result.stderr || result.stdout}`);
  }

  return parseJsonLines(result.stdout).map((video: any) => ({
    url: `https://www.youtube.com/watch?v=${video.id}`,
    title: video.title ?? 'Unknown',
    id: video.id,
    view_count: video.view_count ?? 0,
    upload_date: video.upload_date ?? '',
    duration: video.duration ?? 0,
    uploader: video.uploader ?? 'Unknown',
    like_count: video.like_count ?? 0,
  }));
}

function formatSearchResults(videos: Array<Record<string, any>>) {
  return videos.map((video, index) => {
    const views = Number(video.view_count ?? 0);
    const duration = Number(video.duration ?? 0);
    const uploadDate = String(video.upload_date ?? '');
    const viewsStr = views >= 1_000_000
      ? `${(views / 1_000_000).toFixed(1)}M`
      : views >= 1_000
        ? `${(views / 1_000).toFixed(1)}K`
        : String(views);
    const durationStr = duration >= 3600
      ? `${Math.floor(duration / 3600)}h${Math.floor((duration % 3600) / 60)}m`
      : duration >= 60
        ? `${Math.floor(duration / 60)}m${duration % 60}s`
        : `${duration}s`;
    const formattedDate = uploadDate.length === 8
      ? `${uploadDate.slice(0, 4)}-${uploadDate.slice(4, 6)}-${uploadDate.slice(6, 8)}`
      : uploadDate || 'unknown';

    return [
      `[${index + 1}] ${video.title}`,
      `  👁️ ${viewsStr} views | ⏱️ ${durationStr} | 📅 ${formattedDate}`,
      `  📺 ${video.uploader}`,
      `  🔗 ${video.url}`,
    ].join('\n');
  }).join('\n\n');
}

async function getFlatVideos(pi: ExtensionAPI, sourceUrl: string, count?: number, extractorArgs?: string) {
  await requireYtDlp(pi);
  const args = ['--flat-playlist', '--dump-json', '--no-check-certificate'];
  if (count) args.push('--playlist-end', String(count));
  if (extractorArgs) args.push('--extractor-args', extractorArgs);
  args.push(sourceUrl);
  const result = await run(pi, 'yt-dlp', args);
  if (result.code !== 0) {
    throw new Error(`Failed to extract videos: ${result.stderr || result.stdout}`);
  }
  return parseJsonLines(result.stdout).map((video: any) => ({
    url: `https://www.youtube.com/watch?v=${video.id}`,
    title: video.title ?? 'Unknown',
    id: video.id,
  }));
}

async function parseUrlFile(urlFile: string) {
  const raw = await readFile(urlFile, 'utf8');
  const trimmed = raw.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith('[')) {
    const parsed = JSON.parse(trimmed);
    return parsed.map((item: any) => typeof item === 'string' ? item : item.url).filter(Boolean);
  }
  return trimmed.split('\n').map((line) => line.trim()).filter((line) => line && !line.startsWith('#'));
}

async function batchProcess(
  pi: ExtensionAPI,
  params: {
    urls?: string[];
    url_file?: string;
    output_dir: string;
    output_format: string;
    model: string;
    language?: string;
    prefer_subtitle?: boolean;
    extractor_args?: string;
  },
) {
  const directUrls = params.urls ?? [];
  const fileUrls = params.url_file ? await parseUrlFile(params.url_file) : [];
  const urls = [...directUrls, ...fileUrls];
  if (urls.length === 0) {
    throw new Error('No URLs provided. Pass urls or url_file.');
  }

  await mkdir(params.output_dir, { recursive: true });

  const results: Array<Record<string, any>> = [];
  for (const url of urls) {
    const info = await getVideoInfo(pi, url, params.extractor_args);
    const safeTitle = sanitizeFilename(info.title ?? info.id ?? 'video');
    const outputFile = path.join(params.output_dir, `${safeTitle}.${params.output_format}`);

    try {
      const processed = await processVideo(pi, {
        url,
        output_file: outputFile,
        output_format: params.output_format,
        model: params.model,
        language: params.language,
        prefer_subtitle: params.prefer_subtitle,
        extractor_args: params.extractor_args,
      });
      results.push({ url, title: info.title, status: 'success', ...processed });
    } catch (error) {
      results.push({
        url,
        title: info.title,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  return results;
}

function parseSrt(content: string) {
  const blocks = content.split(/\r?\n\r?\n/);
  const segments: Array<{ start: string; end: string; text: string }> = [];

  for (const block of blocks) {
    const lines = block.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (lines.length < 2) continue;
    const timestampLine = lines.find((line) => line.includes('-->'));
    if (!timestampLine) continue;
    const [start, end] = timestampLine.split('-->').map((part) => part.trim().replace(',', '.'));
    const textLines = lines.filter((line) => line !== timestampLine && !/^\d+$/.test(line));
    if (!textLines.length) continue;
    segments.push({ start, end, text: textLines.join(' ') });
  }

  return segments;
}

function formatTimestamp(input: string) {
  const [hours, minutes, secondsPart] = input.split(':');
  const seconds = Math.floor(Number(secondsPart));
  if (Number(hours) > 0) return `${Number(hours)}:${String(Number(minutes)).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  return `${Number(minutes)}:${String(seconds).padStart(2, '0')}`;
}

function segmentsToPromptText(segments: Array<{ start: string; end: string; text: string }>, maxChars = 8000) {
  const lines: string[] = [];
  let current = 0;
  for (const segment of segments) {
    const line = `[${formatTimestamp(segment.start)}] ${segment.text}`;
    if (current + line.length > maxChars) break;
    lines.push(line);
    current += line.length;
  }
  return lines.join('\n\n');
}

async function summarizeSrt(params: {
  srt_file: string;
  output_file?: string;
  api_key?: string;
  model: string;
  segments: number;
}) {
  const srt = await readFile(params.srt_file, 'utf8');
  const parsed = parseSrt(srt);
  if (parsed.length === 0) {
    throw new Error('No SRT segments found.');
  }

  const transcript = segmentsToPromptText(parsed);
  const prompt = `Analyze this video transcript and generate a timestamped outline with approximately ${params.segments} key segments.\n\nFormat each line as:\nHH:MM:SS or MM:SS - Brief topic description\n\nFocus on topic transitions, key discussion points, highlights, and natural breaks.\n\nTRANSCRIPT:\n${transcript}\n\nGenerate the outline:`;

  const apiKey = params.api_key || process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    const fallback = `No OPENROUTER_API_KEY found. Use this prompt manually:\n\n${prompt}`;
    if (params.output_file) await writeFile(params.output_file, fallback, 'utf8');
    return { mode: 'manual', output: fallback };
  }

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: params.model,
      max_tokens: 2000,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!response.ok) {
    throw new Error(`OpenRouter API request failed: ${response.status} ${await response.text()}`);
  }

  const data = await response.json() as any;
  const text = data.choices?.[0]?.message?.content ?? '';
  const outline = text
    .split('\n')
    .map((line: string) => line.trim())
    .filter((line: string) => line && /\d/.test(line.slice(0, 8)) && line.includes(':'))
    .join('\n');

  if (params.output_file) {
    await mkdir(path.dirname(params.output_file), { recursive: true });
    await writeFile(params.output_file, outline, 'utf8');
  }

  return { mode: 'api', output: outline };
}

async function runWsp(pi: ExtensionAPI, params: {
  kind: typeof WSP_KINDS[number];
  query?: string;
  count?: number;
  source?: typeof WSP_NEWS_SOURCES[number];
  region?: typeof WSP_REGIONS[number];
  freshness?: string;
  forum?: typeof WSP_FORUMS[number] | string;
  subreddit?: string;
  keyword?: string;
  sort?: string;
  type?: typeof WSP_GEO_TYPES[number] | string;
  preset?: string;
  hours?: number;
  topic?: string;
  xueqiu?: boolean;
}) {
  const wspRoot = path.join(process.cwd(), '.claude', 'skills', 'wsp-v3');
  const scriptPath = path.join('scripts', 'wsp.py');

  const args = ['run', scriptPath, params.kind];

  if (params.kind === 'status') {
    const result = await pi.exec('uv', args, { cwd: wspRoot, timeout: 1000 * 60 * 5 });
    if (result.code !== 0) {
      throw new Error(`wsp-v3 status failed: ${result.stderr || result.stdout}`);
    }
    return result.stdout || result.stderr;
  }

  if ((params.kind === 'search' || params.kind === 'news' || params.kind === 'china' || params.kind === 'geopolitics' || params.kind === 'trading') && params.query) {
    args.push(params.query);
  }

  if (params.kind === 'news') {
    if (params.source) args.push('--source', params.source);
    if (params.region) args.push('--region', params.region);
    if (params.freshness) args.push('--freshness', params.freshness);
    if (params.count) args.push('--count', String(params.count));
  }

  if (params.kind === 'forum') {
    args.push(params.forum ?? 'multi');
    if (params.forum === 'reddit') {
      if (params.subreddit) args.push(params.subreddit);
      if (params.keyword) args.push('--keyword', params.keyword);
      if (params.sort) args.push('--sort', params.sort);
      if (params.hours) args.push('--hours', String(params.hours));
      if (params.count) args.push('--count', String(params.count));
    } else if (params.forum === 'hackernews') {
      if (params.query) args.push(params.query);
      if (params.type) args.push('--type', params.type);
      if (params.hours) args.push('--hours', String(params.hours));
      if (params.count) args.push('--count', String(params.count));
    } else if (params.forum === 'multi') {
      if (params.preset) args.push('--preset', params.preset);
      if (params.query) args.push('--query', params.query);
      if (params.freshness) args.push('--freshness', params.freshness);
      if (params.count) args.push('--count', String(params.count));
    } else {
      if (params.query) args.push(params.query);
      if (params.freshness) args.push('--freshness', params.freshness);
      if (params.count) args.push('--count', String(params.count));
    }
  }

  if (params.kind === 'china') {
    if (params.forum) args.push('--forum', params.forum);
    if (params.xueqiu) args.push('--xueqiu');
    if (params.freshness) args.push('--freshness', params.freshness);
    if (params.count) args.push('--count', String(params.count));
  }

  if (params.kind === 'geopolitics') {
    if (params.topic) args.push('--topic', params.topic);
    if (params.type) args.push('--type', params.type);
    if (params.freshness) args.push('--freshness', params.freshness);
    if (params.count) args.push('--count', String(params.count));
  }

  if (params.kind === 'trading') {
    if (params.forum) args.push('--forum', params.forum);
    if (params.freshness) args.push('--freshness', params.freshness);
    if (params.count) args.push('--count', String(params.count));
  }

  if (params.kind === 'search') {
    if (params.freshness) args.push('--freshness', params.freshness);
    if (params.count) args.push('--count', String(params.count));
  }

  const result = await pi.exec('uv', args, { cwd: wspRoot, timeout: 1000 * 60 * 5 });
  if (result.code !== 0) {
    throw new Error(`wsp-v3 ${params.kind} failed: ${result.stderr || result.stdout}`);
  }
  return result.stdout || result.stderr;
}

export default function (pi: ExtensionAPI) {
  pi.on('session_start', async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    ctx.ui.notify('youtube-video-processor loaded', 'info');
  });

  pi.registerTool({
    name: 'youtube_search',
    label: 'YouTube Search',
    description: 'Search YouTube videos with optional sort and time filters using yt-dlp.',
    parameters: Type.Object({
      query: Type.String({ description: 'Search query' }),
      count: Type.Optional(Type.Number({ default: 10 })),
      sort_by: Type.Optional(StringEnum(SEARCH_SORTS)),
      time_filter: Type.Optional(StringEnum(TIME_FILTERS)),
      output_file: Type.Optional(Type.String({ description: 'Optional JSON file path to save results' })),
      extractor_args: Type.Optional(Type.String()),
    }),
    async execute(_id, params) {
      const videos = await searchYoutube(
        pi,
        params.query,
        params.count ?? 10,
        params.sort_by ?? 'relevance',
        params.time_filter,
        params.extractor_args,
      );
      if (params.output_file) {
        await mkdir(path.dirname(params.output_file), { recursive: true });
        await writeFile(params.output_file, JSON.stringify(videos, null, 2), 'utf8');
      }
      return {
        content: [{ type: 'text', text: truncateText(formatSearchResults(videos)) }],
        details: { videos, output_file: params.output_file },
      };
    },
  });

  pi.registerTool({
    name: 'wsp_search',
    label: 'WSP Search',
    description: 'Run the local .claude/skills/wsp-v3 unified web research CLI via uv. Supports general search, news, forums, China, geopolitics, trading, and status.',
    parameters: Type.Object({
      kind: Type.Optional(StringEnum(WSP_KINDS)),
      query: Type.Optional(Type.String({ description: 'Search query. Not required for status.' })),
      count: Type.Optional(Type.Number()),
      source: Type.Optional(StringEnum(WSP_NEWS_SOURCES)),
      region: Type.Optional(StringEnum(WSP_REGIONS)),
      freshness: Type.Optional(Type.String({ description: 'WSP freshness code like pd, pw, pm, py.' })),
      forum: Type.Optional(Type.String({ description: 'Forum name, e.g. reddit, hackernews, lihkg, ptt, v2ex, multi, xueqiu, stocktwits.' })),
      subreddit: Type.Optional(Type.String()),
      keyword: Type.Optional(Type.String()),
      sort: Type.Optional(Type.String()),
      type: Type.Optional(Type.String({ description: 'Subtype, e.g. think_tanks or expert_commentary.' })),
      preset: Type.Optional(Type.String()),
      hours: Type.Optional(Type.Number()),
      topic: Type.Optional(Type.String()),
      xueqiu: Type.Optional(Type.Boolean()),
    }),
    async execute(_id, params) {
      const output = await runWsp(pi, {
        kind: params.kind ?? 'search',
        query: params.query,
        count: params.count,
        source: params.source,
        region: params.region,
        freshness: params.freshness,
        forum: params.forum,
        subreddit: params.subreddit,
        keyword: params.keyword,
        sort: params.sort,
        type: params.type,
        preset: params.preset,
        hours: params.hours,
        topic: params.topic,
        xueqiu: params.xueqiu,
      });
      return {
        content: [{ type: 'text', text: truncateText(output) }],
        details: { kind: params.kind ?? 'search', output },
      };
    },
  });

  pi.registerTool({
    name: 'youtube_info',
    label: 'YouTube Info',
    description: 'Inspect a YouTube video and list available manual subtitles and automatic captions.',
    parameters: Type.Object({
      url: Type.String(),
      extractor_args: Type.Optional(Type.String()),
    }),
    async execute(_id, params) {
      const info = await listSubtitles(pi, params.url, params.extractor_args);
      const manual = Object.keys(info.manual);
      const automatic = Object.keys(info.automatic);
      const text = [
        `Title: ${info.title}`,
        `Uploader: ${info.uploader ?? 'Unknown'}`,
        `Duration: ${info.duration}s`,
        `Manual subtitles: ${manual.length ? manual.join(', ') : 'none'}`,
        `Automatic captions: ${automatic.length ? automatic.join(', ') : 'none'}`,
      ].join('\n');
      return {
        content: [{ type: 'text', text }],
        details: info,
      };
    },
  });

  pi.registerTool({
    name: 'youtube_process_video',
    label: 'YouTube Process Video',
    description: 'Download subtitles from a YouTube video or fall back to Whisper transcription. Requires yt-dlp, ffmpeg, and whisper for transcription fallback.',
    parameters: Type.Object({
      url: Type.String(),
      output_file: Type.String(),
      output_format: Type.Optional(StringEnum(OUTPUT_FORMATS)),
      model: Type.Optional(StringEnum(WHISPER_MODELS)),
      language: Type.Optional(Type.String()),
      prefer_subtitle: Type.Optional(Type.Boolean({ default: true })),
      verbose: Type.Optional(Type.Boolean({ default: false })),
      extractor_args: Type.Optional(Type.String()),
    }),
    async execute(_id, params) {
      const result = await processVideo(pi, {
        ...params,
        output_format: params.output_format ?? 'txt',
        model: params.model ?? 'base',
      });
      return {
        content: [{ type: 'text', text: `Saved ${result.method} output to ${result.path}\n\n${result.preview}` }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: 'youtube_batch_process',
    label: 'YouTube Batch Process',
    description: 'Process multiple YouTube URLs into transcripts. Accepts direct URLs or a JSON/text url_file.',
    parameters: Type.Object({
      urls: Type.Optional(Type.Array(Type.String())),
      url_file: Type.Optional(Type.String()),
      output_dir: Type.String(),
      output_format: Type.Optional(StringEnum(OUTPUT_FORMATS)),
      model: Type.Optional(StringEnum(WHISPER_MODELS)),
      language: Type.Optional(Type.String()),
      prefer_subtitle: Type.Optional(Type.Boolean({ default: true })),
      extractor_args: Type.Optional(Type.String()),
    }),
    async execute(_id, params) {
      const results = await batchProcess(pi, {
        ...params,
        output_format: params.output_format ?? 'txt',
        model: params.model ?? 'base',
      });
      const summary = results.map((item) => {
        if (item.status === 'success') return `✓ ${item.title} -> ${item.path}`;
        return `✗ ${item.title ?? item.url} -> ${item.error}`;
      }).join('\n');
      return {
        content: [{ type: 'text', text: truncateText(summary) }],
        details: { results },
      };
    },
  });

  pi.registerTool({
    name: 'youtube_channel_process',
    label: 'YouTube Channel Process',
    description: 'Fetch the latest videos from a YouTube channel and process them into transcripts.',
    parameters: Type.Object({
      channel_url: Type.String(),
      count: Type.Optional(Type.Number({ default: 5 })),
      output_dir: Type.String(),
      output_format: Type.Optional(StringEnum(OUTPUT_FORMATS)),
      model: Type.Optional(StringEnum(WHISPER_MODELS)),
      language: Type.Optional(Type.String()),
      prefer_subtitle: Type.Optional(Type.Boolean({ default: true })),
      extractor_args: Type.Optional(Type.String()),
    }),
    async execute(_id, params) {
      const videos = await getFlatVideos(pi, params.channel_url, params.count ?? 5, params.extractor_args);
      const results = await batchProcess(pi, {
        urls: videos.map((video) => video.url),
        output_dir: params.output_dir,
        output_format: params.output_format ?? 'srt',
        model: params.model ?? 'base',
        language: params.language,
        prefer_subtitle: params.prefer_subtitle,
        extractor_args: params.extractor_args,
      });
      return {
        content: [{ type: 'text', text: truncateText(results.map((item) => `${item.status === 'success' ? '✓' : '✗'} ${item.title ?? item.url}`).join('\n')) }],
        details: { videos, results },
      };
    },
  });

  pi.registerTool({
    name: 'youtube_playlist_process',
    label: 'YouTube Playlist Process',
    description: 'Process videos from a YouTube playlist into transcripts.',
    parameters: Type.Object({
      playlist_url: Type.String(),
      output_dir: Type.String(),
      count: Type.Optional(Type.Number()),
      output_format: Type.Optional(StringEnum(OUTPUT_FORMATS)),
      model: Type.Optional(StringEnum(WHISPER_MODELS)),
      language: Type.Optional(Type.String()),
      prefer_subtitle: Type.Optional(Type.Boolean({ default: true })),
      extractor_args: Type.Optional(Type.String()),
    }),
    async execute(_id, params) {
      const videos = await getFlatVideos(pi, params.playlist_url, params.count, params.extractor_args);
      const results = await batchProcess(pi, {
        urls: videos.map((video) => video.url),
        output_dir: params.output_dir,
        output_format: params.output_format ?? 'txt',
        model: params.model ?? 'base',
        language: params.language,
        prefer_subtitle: params.prefer_subtitle,
        extractor_args: params.extractor_args,
      });
      return {
        content: [{ type: 'text', text: truncateText(results.map((item) => `${item.status === 'success' ? '✓' : '✗'} ${item.title ?? item.url}`).join('\n')) }],
        details: { videos, results },
      };
    },
  });

  pi.registerTool({
    name: 'youtube_summarize_srt',
    label: 'YouTube Summarize SRT',
    description: 'Generate a timestamped outline from an SRT transcript, optionally using the Anthropic API.',
    parameters: Type.Object({
      srt_file: Type.String(),
      output_file: Type.Optional(Type.String()),
      api_key: Type.Optional(Type.String()),
      model: Type.Optional(Type.String({ default: 'moonshotai/kimi-k2.5' })),
      segments: Type.Optional(Type.Number({ default: 15 })),
    }),
    async execute(_id, params) {
      const result = await summarizeSrt({
        ...params,
        model: params.model ?? 'moonshotai/kimi-k2.5',
        segments: params.segments ?? 15,
      });
      return {
        content: [{ type: 'text', text: truncateText(result.output) }],
        details: result,
      };
    },
  });
}
