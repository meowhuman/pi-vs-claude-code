---
model: opus
description: Interactive decision board query tool — explore Drip Music board structure, ask strategic questions, and get member perspectives
argument-hint: [ACTION] [CONTEXT]
allowed-tools: bash, read, write, grep
---

# Purpose

Help users navigate and optimize Drip Music's strategic Decision Board system. This command provides:
- Information about board member roles and perspectives
- Recommendations on which board preset to use for different strategic questions
- Company context and decision-making framework
- Guidance on crafting effective briefs for board deliberation

# Variables

**Company Context:**
- **Organization:** Drip Music Limited (Hong Kong, founded 2017)
- **Mission:** Promoting fusion arts (jazz + classical + contemporary)
- **Key Ensemble:** Ensemble Transience (Third Stream jazz)
- **Team:** Teriver Cheung (Founder/Artistic Director), Samantha Kwok (Producer), Anna (Marketing)
- **Milestone:** 3-year venue partnership at Sai Wan Ho Civic Centre (2026-2029)
- **Revenue Model:** Venue partnership (free space) + 20% profit share from co-presenters + workshops/grants

**Board Member Roles:**

| Member | Role | Focus Area | Active |
|--------|------|-----------|--------|
| **CEO** | Neutral facilitator | Framing decisions, synthesizing perspectives | ✓ |
| **Brand** | Brand & Creative Director | Visual identity, artistic positioning, cultural alignment | ✓ |
| **Marketing** | Audience Development Strategist | Audience growth, campaign strategy, community building | ✓ |
| **Grants** | Grants & Government Relations | ADC, WKCDA, HAB, ETO funding, policy strategy | ✓ |
| **International** | International Partnership Strategist | Overseas artists, co-productions, tours, global network | ✓ |
| **Content** | Content & Copywriting Director | Editorial voice, programme notes, storytelling, cultural messaging | ✓ |
| **Revenue** | Revenue & Sustainability Strategist | Financial realism, monetization, long-term sustainability | ✓ |
| **Contrarian** | Devil's Advocate | Challenges assumptions, identifies blind spots, risk assessment | ✓ |
| **Community** | Community & Education Strategist | Outreach, music education, audience pipeline, social impact | ○ |

**Board Presets:**

```
full              → All 8 members (major strategic decisions)
programming       → Brand, International, Revenue, Contrarian (artist & programming decisions)
marketing-campaign → Brand, Marketing, Content, Contrarian (audience & campaign decisions)
grants-funding    → Grants, Revenue, International, Contrarian (funding & policy decisions)
creative          → Brand, Content, Contrarian (artistic & creative direction)
quick             → Revenue, Contrarian (rapid 2-member sanity check)
```

# Instructions

## Key Guidelines

1. **Brief Format** — Structure your question for the board:
   - **Situation:** What is happening (context, current state)
   - **Stakes:** What's at risk, what we gain/lose
   - **Constraints:** Boundaries, limitations, hard deadlines
   - **Key Question:** The one question that needs answering

2. **Choosing a Preset** — Different decisions require different perspectives:
   - **Programming/Artist Decisions** → Use `programming` preset
   - **Marketing/Campaign Decisions** → Use `marketing-campaign` preset
   - **Funding/Grant Decisions** → Use `grants-funding` preset
   - **Creative/Artistic Direction** → Use `creative` preset
   - **Quick Reality Check** → Use `quick` preset (fastest, 2 people)
   - **Major Strategic Pivot** → Use `full` preset (all perspectives)

3. **Context for Board Members** — Each member brings a distinct lens:
   - **Brand** asks: "Does this strengthen or dilute Drip's identity as Hong Kong's premier jazz fusion platform?"
   - **Marketing** asks: "Does this build sustainable audience habits and community?"
   - **Grants** asks: "How does this affect our fundability with ADC, WKCDA, HAB, ETO?"
   - **International** asks: "Does this enhance or complicate our relationships with world-class artists?"
   - **Content** asks: "What's the story we're telling, and does it reach the right audiences?"
   - **Revenue** asks: "Can we afford this? Is it sustainable? What are the financial trade-offs?"
   - **Contrarian** asks: "What are we assuming that might be wrong? What could go wrong?"
   - **Community** asks: "Does this build long-term audience loyalty and cultural impact?"

4. **Deliberation Style** — The board:
   - Takes 2-5 minutes per deliberation
   - Uses Kimi K2.5 for all agents (all board members same intelligence level)
   - Runs board members in parallel (fast)
   - Outputs a structured memo with decision, stances, trade-offs, next actions

# Workflow

## 1. Understand Your Decision

Identify the strategic question you're facing. Examples:
- **Programming:** "Should we book Kurt Rosenwinkle for 3 nights or 1 night?"
- **Marketing:** "Should we hire Anna, Kini, or Kenji for the marketing role?"
- **Grants:** "Do we apply for the ADC Arts Group Support grant or just project grants?"
- **Partnerships:** "Should we co-produce with a Mainland Chinese presenter or self-produce?"
- **Audience:** "Should we focus on core jazz audience or expand to broader listeners?"
- **Venue:** "How do we maximize the Sai Wan Ho Civic Centre venue partnership?"

Ask yourself: **Which preset fits this decision?**

## 2. Craft Your Brief

Write a concise brief following the 4-section structure:

**Example Brief:**

```
## Situation
We have an offer to co-produce a 3-night residency with Kurt Rosenwinkle
at Sai Wan Ho Civic Centre. Kurt is one of the world's top fusion guitarists.
The residency would include performances, a masterclass, and a workshop.
Timeline: 2 months to confirm.

## Stakes
- Artist credibility: Rosenwinkle is world-class, strengthens Drip's international profile
- Financial risk: ~HK$150K artist fee + production costs, uncertain ticket sales at new venue
- Opportunity cost: This budget could fund 3-4 smaller shows or other programming
- Community impact: Could introduce Hong Kong audiences to cutting-edge fusion jazz

## Constraints
- Budget: ~HK$200K total for artist, production, marketing
- Venue: 300-seat theater, relatively new to Drip's audience base (Sai Wan Ho)
- Timeline: Decision needed in 2 weeks
- Team capacity: Small team (Teriver, Samantha, Anna) for execution

## Key Question
Given our limited budget and new venue, is a 3-night Kurt Rosenwinkle residency
the right first major international booking for Sai Wan Ho, or should we start smaller?
```

## 3. Choose Your Preset

Based on your brief, decide which board members should deliberate:

**For this Rosenwinkle example:** Use `programming` preset
→ Brand (Does it strengthen Drip?), International (Artist relationships),
   Revenue (Can we afford it?), Contrarian (What could go wrong?)

## 4. Start the Deliberation

Run the board:

```bash
# Option A: Use a preset
BOARD_PRESET=programming pi -e extensions/drip-board.ts

# Option B: Run the full board interface
just ext-drip-board

# Option C: Quick sanity check
just ext-drip-board-quick
```

Then paste your brief into the prompt and use the `board_begin` tool.

## 5. Review the Memo

The board will produce a structured memo with:
- **Final Decision:** CEO's synthesis and recommendation
- **Board Member Stances:** Each member's position, key argument, key concern
- **Dissent & Tensions:** Unresolved disagreements
- **Trade-offs:** What you gain / what you lose
- **Next Actions:** Concrete steps to move forward

Save the memo to `.pi/drip-board/memos/` for future reference.

## 6. Iterate (Optional)

If you want a different perspective:
- Try the same brief with a different preset (e.g., switch from `programming` to `creative`)
- Ask a follow-up question based on the board's response
- Reconvene with more context or new constraints

# Report

After deliberation completes:

```
=== Drip Music Decision Board Memo ===

✓ Question: [Your key question]
✓ Board Members: [7 members, took 3-4 minutes]
✓ Preset Used: [programming]
✓ Model: Kimi K2.5 (all agents)

✓ Decision Memo: [.pi/drip-board/memos/FILENAME.md]

Next: Review board stances and trade-offs, then decide on next steps
```

# Error Handling

| Issue | Cause | Solution |
|-------|-------|----------|
| `No config file found` | `.pi/drip-board/config.yaml` missing | Ensure drip-board extension is installed correctly |
| `Agent not found: [name]` | Agent .md file missing from `.pi/drip-board/agents/` | Verify all 9 agent files exist in agents directory |
| `Timeout` | Deliberation exceeded time limit | This is normal — memo will be generated with available responses |
| `Subprocess error: Kimi API` | API key not configured | Run `pi --list-models kimi` to verify Kimi K2.5 access |
| `Permission denied` on memo save | Directory not writable | Ensure `.pi/drip-board/memos/` exists and is writable |

# Examples

## Example 1: Marketing Role Decision

**Brief:**
```
## Situation
We need to hire a Marketing & Communications manager. Three candidates:
1. Anna (HKU, former intern, knows Drip culture) — needs training
2. Kini (ELLE editor, highest editorial quality) — high salary, availability unclear
3. Kenji (Visual designer, AI skills) — strong design, lacks music background

## Stakes
Marketing is critical for our Sai Wan Ho launch. We have budget for 1 hire (not 3).
Right hire = audience growth + brand consistency. Wrong hire = wasted opportunity.

## Constraints
- Budget: HK$25-30K/month for salary + benefits
- Start date: Needed by May 2026
- Available capacity: ~20 hours/week (part-time initially)

## Key Question
Who is the best hire for Drip Music's marketing in 2026 — and why?
```

**Preset:** `marketing-campaign` (Brand, Marketing, Content, Contrarian)

**Outcome:** Board debates candidate fit, growth potential, team dynamics. Memo recommends Anna with structured training plan + support from external content specialist (Kini/Kenji as freelancers).

---

## Example 2: Venue Strategy

**Brief:**
```
## Situation
Sai Wan Ho Civic Centre partnership is now live (2026-2029, 300-seat theater).
First question: How many shows per month should we program?

Option A: 2/month (sustainable, low risk)
Option B: 4/month (ambitious, new venue unknown)
Option C: 6/month (maximize venue partnership value, stretch team)

## Stakes
- Audience building: More shows = more opportunities to engage new audiences
- Team capacity: Samantha + Teriver already stretched; Anna is new
- Artistic quality: Rushed programming = lower-quality curation
- Financial: More shows = more revenue opportunity but higher risk

## Constraints
- Team: 3 people total, Teriver must maintain artistic focus
- Venue hours: Available for ~100 days/year
- Budget: Depends on how many international artists we book

## Key Question
What's the optimal programming frequency for our first year at Sai Wan Ho?
```

**Preset:** `programming` (Brand, International, Revenue, Contrarian)

**Outcome:** Board recommends 3 shows/month (sweet spot between ambition and sustainability). Mix: 2 "bread and butter" (local artists, lower cost), 1 "showcase" (international artist or experimental).

---

## Example 3: Quick Revenue Check

**Brief:**
```
Idea: Launch a "Drip Music Premium" subscription (HK$99/month) with:
- 10% off ticket prices
- Exclusive online masterclasses
- Priority seating

Rough math: 50 subscribers × HK$99 = HK$5,970/month revenue.
Question: Is this worth the effort, or should we focus on other revenue streams?
```

**Preset:** `quick` (Revenue, Contrarian only)

**Outcome:** Fast 2-minute deliberation. Revenue says: Possible but low return vs. effort. Contrarian asks: What if subscribers are mostly existing customers (no net new revenue)? Recommendation: Pilot with 20 people first; measure if it drives new audience or just discounts existing fans.

# Summary

**Drip Music's Decision Board Interactive Tool** enables:

✓ **Fast strategic deliberation** — 2-5 minute board meetings for real decisions
✓ **Multi-perspective thinking** — 8 different expert lenses on every decision
✓ **Documented reasoning** — Memos that capture stances, trade-offs, next actions
✓ **Scalable decision-making** — From quick sanity checks to major strategy pivots
✓ **Context-rich** — All board members know Drip Music's mission, team, constraints, and opportunities

**Best for:**
- Artist/programming decisions (booking, repertoire, venue strategy)
- Marketing/audience decisions (hiring, campaigns, community strategy)
- Funding/business decisions (grants, partnerships, revenue models)
- Creative/artistic direction (brand positioning, identity alignment)
- Major strategic pivots (expansion, new initiatives, pivots)

**Quick Start:**
```bash
# 1. Run the board
just ext-drip-board

# 2. Paste your brief (or reference a file: brief.md)

# 3. Use /board-preset to select which members to invite

# 4. Call board_begin with your strategic question

# 5. Read the memo, capture the decision
```
