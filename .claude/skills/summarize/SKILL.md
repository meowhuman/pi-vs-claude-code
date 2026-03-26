---
name: summarize
description: Summarize or extract text/transcripts from URLs, YouTube videos, podcasts, and local files using the summarize CLI tool. Use when user asks to summarize a link/article/video, transcribe a YouTube video, or extract content from a URL.
homepage: https://summarize.sh
metadata:
  {
    "openclaw":
      {
        "emoji": "🧾",
        "requires": { "bins": ["summarize"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "steipete/tap/summarize",
              "bins": ["summarize"],
              "label": "Install summarize (brew)",
            },
          ],
      },
  }
---

# Summarize

Fast CLI to summarize URLs, local files, and YouTube links via `summarize.sh`.

## When to use (trigger phrases)

Use this skill immediately when the user asks any of:

- "use summarize.sh"
- "what's this link/video about?"
- "summarize this URL/article"
- "transcribe this YouTube/video" (best-effort transcript extraction; no `yt-dlp` needed)
- "extract content from this page"

## Prerequisites

Install `summarize` via Homebrew if not present:

```bash
brew install steipete/tap/summarize
```

Set the API key for your chosen provider (default model: `google/gemini-3-flash-preview`):

- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- xAI: `XAI_API_KEY`
- Google: `GEMINI_API_KEY` (aliases: `GOOGLE_GENERATIVE_AI_API_KEY`, `GOOGLE_API_KEY`)

## Workflow

1. **Check if `summarize` is installed**:
   ```bash
   which summarize || echo "not installed"
   ```
   If missing, prompt user to install via brew.

2. **Run summarize on the target**:
   ```bash
   # URL or article
   summarize "https://example.com" --model google/gemini-3-flash-preview

   # Local file (PDF, text, etc.)
   summarize "/path/to/file.pdf" --model google/gemini-3-flash-preview

   # YouTube video (summary)
   summarize "https://youtu.be/VIDEO_ID" --youtube auto

   # YouTube transcript extraction only
   summarize "https://youtu.be/VIDEO_ID" --youtube auto --extract-only
   ```

3. **Handle large transcripts**: If the transcript is huge, return a tight summary first, then ask which section/time range to expand.

4. **Present results** clearly with source attribution.

## Useful flags

| Flag | Description |
|------|-------------|
| `--length short\|medium\|long\|xl\|xxl\|<chars>` | Control output length |
| `--max-output-tokens <count>` | Limit token output |
| `--extract-only` | Extract text only, no summarization (URLs only) |
| `--json` | Machine-readable output |
| `--firecrawl auto\|off\|always` | Fallback extraction for blocked sites |
| `--youtube auto` | Enable YouTube transcript via Apify fallback |
| `--model <provider/model>` | Override default model |

## Optional services

- `FIRECRAWL_API_KEY` — for sites that block standard extraction
- `APIFY_API_TOKEN` — for YouTube transcript fallback

## Optional config

`~/.summarize/config.json`:
```json
{ "model": "openai/gpt-4o" }
```

## Examples

### Example 1: Summarize a web article

User request:
```
summarize this article: https://example.com/some-post
```

You would:
1. Run: `summarize "https://example.com/some-post" --model google/gemini-3-flash-preview`
2. Present the summary with key points highlighted

### Example 2: Transcribe a YouTube video

User request:
```
transcribe this YouTube video: https://youtu.be/dQw4w9WgXcQ
```

You would:
1. Run: `summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto --extract-only`
2. If transcript is large, summarize first and ask for specific sections

### Example 3: Summarize a local PDF

User request:
```
what's in this PDF: /Users/me/docs/report.pdf
```

You would:
1. Run: `summarize "/Users/me/docs/report.pdf" --model google/gemini-3-flash-preview --length medium`
2. Return a structured summary

### Example 4: Long-form content with length control

User request:
```
give me a detailed summary of this podcast episode
```

You would:
1. Run: `summarize "<url>" --length xl --youtube auto`
2. Return full detailed summary
