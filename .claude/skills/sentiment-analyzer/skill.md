---
model: haiku
description: Universal sentiment analysis engine supporting dual-mode analysis (AI + keyword-based), multi-source weighting, time decay, and composite metrics. Use when analyzing sentiment in text, reviews, social media, news, or any non-stock-specific content.
argument-hint: [--text TEXT] [--file FILE] [--config CONFIG] [--mode MODE] [--weighted] [--ai-model]
allowed-tools: [Bash, Read, Write]
disable-model-invocation: false
---

# Sentiment Analyzer

## Purpose

通用情緒分析引擎，提供領域無關嘅 NLP 分析能力。支援 AI 模型 (FinBERT) 同關鍵詞雙模式，可用於金融、社交媒體、產品評論等多種場景。

## Features

- **Dual-mode analysis**: Keyword-based (fast) + AI/FinBERT (accurate)
- **Multi-source weighting**: Source credibility scoring
- **Time decay**: Recent content weighted higher
- **Composite metrics**: Balance, polarity, intensity, volatility, trend
- **Batch processing**: Analyze multiple texts at once
- **Configurable domains**: Financial, social media, product reviews, custom

## Prerequisites

### Required Setup

1. **Python Environment**:
   - Python 3.8+
   - Virtual environment: `/Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa/.venv/`
   - Dependencies installed via `uv sync`

2. **Core Engine**: Located at `/Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa/src/core/sentiment_engine.py`

3. **Optional - AI Model**: FinBERT model (requires `transformers` library)

## Variables

```
--text TEXT       : Single text to analyze
--file FILE       : JSON file with multiple texts/items
--config CONFIG   : Configuration preset (financial, social_media, product_review, default)
--mode MODE       : Analysis mode (keyword, ai, auto)
--weighted        : Enable weighted aggregation (requires source + timestamp)
--ai-model        : Force AI model usage
--output FILE     : Save results to file
```

## Instructions

### Single Text Analysis

```bash
/sentiment-analyzer --text "This product is amazing! Best purchase ever." --config product_review
```

**Output**:
```json
{
  "sentiment": "positive",
  "score": 0.75,
  "positive_score": 0.75,
  "negative_score": 0.0,
  "neutral_score": 0.25,
  "analysis_mode": "keyword"
}
```

### Batch Analysis

```bash
/sentiment-analyzer --file texts.json --config social_media --mode ai
```

**Input format** (`texts.json`):
```json
[
  {"text": "First comment here", "id": 1},
  {"text": "Second comment here", "id": 2}
]
```

### Weighted Aggregation

For items with source and timestamp:

```bash
/sentiment-analyzer --file items.json --config financial --weighted --output report.json
```

**Input format** (`items.json`):
```json
[
  {
    "content": "News article text...",
    "source": "bloomberg.com",
    "timestamp": "2024-01-15T10:00:00Z"
  },
  {
    "content": "Social media post...",
    "source": "reddit.com",
    "timestamp": "2024-01-16T14:30:00Z"
  }
]
```

## Config Presets

| Config | Use Case | Description |
|--------|----------|-------------|
| `financial` | Stock news, earnings, finance | Bloomberg/Reuters weighted 1.5x |
| `social_media` | Twitter, Reddit, forums | Platform-specific weighting |
| `product_review` | Amazon, Yelp, reviews | Customer feedback keywords |
| `default` | General text | Balanced keyword lists |

## Understanding Results

### Sentiment Scores

- **score**: -1.0 (強烈負面) to +1.0 (強烈正面)
  - `+0.5 to +1.0`: Strongly positive
  - `+0.1 to +0.5`: Moderately positive
  - `-0.1 to +0.1`: Neutral
  - `-0.5 to -0.1`: Moderately negative
  - `-1.0 to -0.5`: Strongly negative

### Weighted Metrics

- **sentiment_balance**: Ratio of positive vs negative (-1 to +1)
- **sentiment_polarity**: Absolute strength of sentiment (0 to 1)
- **sentiment_intensity**: Overall activity level (0 to 1)
- **sentiment_volatility**: Consistency of sentiment (0 = consistent, 1 = volatile)
- **sentiment_trend**: Direction (improving/deteriorating/stable)
- **confidence_score**: Reliability of result (> 0.75 = high)

## Analysis Modes

| Mode | Speed | Accuracy | Use When |
|------|-------|----------|----------|
| `keyword` | Fast (~0.001s) | Good | Speed matters, simple text |
| `ai` | Slow (~2-3s) | Excellent | Accuracy critical, nuanced text |
| `auto` | Varies | Best default | Unsure, want best of both |

## Examples

### Example 1: Product Reviews

```bash
/sentiment-analyzer --file reviews.json --config product_review --weighted
```

Input (`reviews.json`):
```json
[
  {"content": "Great product! Works perfectly.", "source": "amazon.com", "timestamp": "2024-01-15T10:00:00Z"},
  {"content": "Broke after 2 days.", "source": "amazon.com", "timestamp": "2024-01-16T14:30:00Z"}
]
```

### Example 2: Social Media Monitoring

```bash
/sentiment-analyzer --file social_posts.json --config social_media --weighted --mode ai
```

### Example 3: News Analysis

```bash
/sentiment-analyzer --file news_articles.json --config financial --weighted
```

## Workflow

1. **Activate Python environment** (automatic in wrapper script)
2. **Select config preset** based on content type
3. **Run analysis** with appropriate mode
4. **Interpret results** using score ranges and metrics
5. **Act on insights** if confidence > 0.5

## Technical Details

### Core Engine Location

```
/Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa/src/core/sentiment_engine.py
```

### Performance

- **Keyword mode**: ~0.001s per text
- **AI mode**: ~2-3s per text (first load slower)
- **Memory**: ~50MB (keyword), ~500MB (AI with model)

### Config Files

Located at: `/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sentiment-analyzer-engine/configs/`

## Integration Examples

### WhatsApp Notification

```bash
/sentiment-analyzer --file mentions.json --config social_media --weighted --output sentiment.json
# Then pipe to wacli for alerts if sentiment < -0.3
```

### Daily Monitoring

```bash
# Cron job to track brand sentiment
0 9 * * * /sentiment-analyzer --file daily_mentions.json --config social_media --weighted >> ~/.cache/sentiment-log.jsonl
```

## Related Skills

- `web-research-pro` - Fetch content for analysis
- `stock-sentiment-analyzer` - Stock-specific wrapper (uses same engine)

## Summary

✅ Dual-mode analysis (keyword + AI)
✅ Multi-source weighting with time decay
✅ Composite sentiment metrics
✅ Batch processing support
✅ Configurable domains
✅ Fast keyword mode, accurate AI mode

**Usage**: `/sentiment-analyzer [--text TEXT] [--file FILE] [--config CONFIG] [--mode MODE] [--weighted]`
