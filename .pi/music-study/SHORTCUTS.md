# Music Study Group — Agent Teams Setup

## Files Created

```
.pi/agents/
  teams.yaml                    # Team definitions
  deep-researcher.md           # Agent: niche music sources
  youtube-curator.md           # Agent: video playlists
  genre-historian.md           # Agent: genre lineage
  listening-guide.md           # Agent: listening paths

.pi/music-study/               # Backup knowledge files
  config.yaml
  agents/
    deep-researcher/
      deep-researcher.md
      deep-researcher-knowledge.md
      deep-researcher-sources.md
    ... (other agents)
```

## Quick Start

```bash
# Launch agent team (will auto-load first team)
just ext-music-study
```

Then in Pi:
```
/agents-team           # Select music-study, music-study-quick, etc.
/agents-list           # See active agents
```

## Available Teams

| Team | Agents | Use For |
|------|--------|---------|
| `music-study` | deep-researcher + youtube-curator + genre-historian + listening-guide | Full research meeting |
| `music-study-quick` | deep-researcher + youtube-curator | Fast queries |
| `music-study-jazz` | deep-researcher + genre-historian | Deep jazz analysis |
| `music-study-discovery` | youtube-curator + listening-guide | Find new music |

## Using the Agents

Once loaded, you are the **dispatcher**. You don't have direct tools — you delegate to agents.

### Example workflow:

```
# 1. User asks: "Who influenced Coltrane's late period?"

# 2. You dispatch to researcher:
dispatch_agent: deep-researcher
  task: "Research Coltrane's late period influences. Find insider sources (Ethan Iverson, liner notes, interviews). Focus on 1965-1967."

# 3. Then dispatch to historian:
dispatch_agent: genre-historian
  task: "Trace how these influences connect to broader jazz evolution (free jazz, modal shift)."

# 4. Then dispatch to curator:
dispatch_agent: youtube-curator
  task: "Find YouTube recordings of late Coltrane performances. Focus on live sessions 1965-1967."

# 5. Summarize findings for user
```

## Agent Details

### deep-researcher
- **Sources:** Ethan Iverson, Ted Gioia, liner notes, artist interviews
- **Tools:** wsp-v3, summarize, bird-cli
- **Best for:** Deep analysis, insider knowledge, musicology

### youtube-curator
- **Finds:** Live performances, documentaries, album breakdowns
- **Tools:** summarize (YouTube transcripts), wsp-v3
- **Best for:** Building watchlists, finding rare footage

### genre-historian
- **Maps:** Genre evolution, influence chains, social context
- **Tools:** wsp-v3, summarize
- **Best for:** Understanding "why" and "how" music changed

### listening-guide
- **Creates:** Structured learning paths, album sequences
- **Tools:** wsp-v3
- **Best for:** "What should I listen to next?"

## Model

All agents use: **glm/glm-5-turbo**

## Example Queries

- "I love D'Angelo's Voodoo. What should I listen to next?"
- "Find me rare Monk live recordings on YouTube"
- "Trace bebop's influence on modern hip-hop"
- "Build a 4-week Jazz listening curriculum"
- "What do insiders say about Kind of Blue?"

## Pi Commands

```
/agents-team        # Switch active team
/agents-list        # Show loaded agents
/agents-grid 2      # Set grid columns
```

---

**Note:** Knowledge files (e.g., `deep-researcher-knowledge.md`) are stored in `.pi/music-study/agents/` for reference but not auto-loaded by agent-team.ts. Agents learn and remember through their individual Pi sessions.
