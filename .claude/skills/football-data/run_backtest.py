import sqlite3, math

DB = '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db'
con = sqlite3.connect(DB)

rows = con.execute("""
    SELECT date, home_team, away_team, ft_hg, ft_ag, ft_result, b365_h, b365_d, b365_a, b365_o25, b365_u25
    FROM historical_matches
    WHERE league_key='epl' AND season='2025-26' AND home_team IS NOT NULL
    ORDER BY rowid DESC LIMIT 5
""").fetchall()
for r in rows:
    print(f"  {r[0]}  {r[1]} vs {r[2]}  {r[3]}-{r[4]} {r[5]}  "
          f"B365:{r[6]:.2f}/{r[7]:.2f}/{r[8]:.2f}  O2.5:{r[9]:.2f}/{r[10]:.2f}")

# Simple backtest: bet favorite EPL 2024-25
rows = con.execute("""
    SELECT ft_result, b365_h, b365_a
    FROM historical_matches
    WHERE league_key='epl' AND season='2024-25' AND b365_h IS NOT NULL AND b365_h != ''
    AND CAST(b365_h AS REAL) > 1.01 AND CAST(b365_a AS REAL) > 1.01
""").fetchall()
bankroll = 1000.0; bets = wins = losses = 0
for r in rows:
    ho, ao = float(r['b365_h']), float(r['b365_a'])
    if ho <= 1.01 or ao <= 1.01: continue
    odds = min(ho, ao)
    bet = 'H' if ho < ao else 'A'
    won = (bet == r['ft_result'])
    bankroll += 50.0 * (odds - 1) if won else -50.0
    if won: wins += 1
    else: losses += 1
    bets += 1
roi = (bankroll - 1000) / 1000 * 100
print(f"\n  EPL 2024-25 Simple Backtest: ${bankroll:.0f} | {bets} bets | ROI {roi:+.1f}%")

# Poisson rolling backtest on second half
teams_stats = {}
all_rows = con.execute("""
    SELECT home_team, away_team, ft_hg, ft_ag, ft_result, b365_h, b365_d, b365_a
    FROM historical_matches
    WHERE league_key='epl' AND season='2024-25' AND b365_h IS NOT NULL
    AND CAST(b365_h AS REAL) > 1.01 AND CAST(b365_a AS REAL) > 1.01
    ORDER BY date
""").fetchall()

mid = len(all_rows) // 2
bankroll = 1000.0; bets2 = wins2 = losses2 = 0

def poisson_p(lam, k):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def match_probs(lh, la):
    h = d = a = 0.0
    for i in range(7):
        for j in range(7):
            p = poisson_p(lh, i) * poisson_p(la, j)
            if i > j: h += p
            elif i == j: d += p
            else: a += p
    return h, d, a

for i, r in enumerate(all_rows):
    if i < mid:
        for team, gf, ga in [(r[0], r[2], r[3]), (r[1], r[4], r[5])]:
            if team not in teams_stats:
                teams_stats[team] = {'gf':0, 'ga':0, 'played':0, 'pts':0}
            teams_stats[team]['gf'] += gf
            teams_stats[team]['ga'] += ga
            teams_stats[team]['played'] += 1
            if r[6] == 'H' and team == r[0]: teams_stats[team]['pts'] += 3
            elif r[6] == 'A' and team == r[1]: teams_stats[team]['pts'] += 3
            elif r[6] == 'D': teams_stats[team]['pts'] += 1
        continue

    for team, gf, ga in [(r[0], r[2], r[3]), (r[1], r[4], r[5])]:
        teams_stats[team]['gf'] += gf
        teams_stats[team]['ga'] += ga
        teams_stats[team]['played'] += 1
        if r[6] == 'H' and team == r[0]: teams_stats[team]['pts'] += 3
        elif r[6] == 'A' and team == r[1]: teams_stats[team]['pts'] += 3
        elif r[6] == 'D': teams_stats[team]['pts'] += 1

    tp = sum(s['played'] for s in teams_stats.values())
    if tp == 0: continue
    ag = sum(s['gf'] for s in teams_stats.values()) / tp
    ac = sum(s['ga'] for s in teams_stats.values()) / tp

    ht, at = r[0], r[1]
    if ht not in teams_stats or at not in teams_stats: continue
    lh, la = teams_stats[ht], teams_stats[at]
    if lh['played'] == 0 or la['played'] == 0: continue

    lam_h = ag * (lh['gf']/lh['played']) / ag * (la['ga']/la['played']) / ac * 1.15
    lam_a = ag * (la['gf']/la['played']) / ag * (lh['ga']/lh['played']) / ac
    h_p, d_p, a_p = match_probs(lam_h, lam_a)

    ho, ao = float(r[7]), float(r[8])
    hd = float(r[8]) if r[8] else 0
    raw_total = 1/ho + 1/hd + 1/ao
    fair_h = (1/ho) / raw_total
    fair_a = (1/ao) / raw_total

    for model_p, mkt_odds, name in [(h_p, ho, 'home'), (a_p, ao, 'away')]:
        mkt_p = (1/mkt_odds) / raw_total
        edge = model_p - mkt_p
        if edge > 0.03:
            stake = max(10, bankroll * 0.03)
            won = (name == 'home' and r[6] == 'H') or (name == 'away' and r[6] == 'A')
            bankroll += stake * (mkt_odds - 1) if won else -stake
            if won: wins2 += 1
            else: losses2 += 1
            bets2 += 1

roi2 = (bankroll - 1000) / 1000 * 100
print(f"\n  Poisson Rolling Backtest: ${bankroll:.0f} | {bets2} bets | ROI {roi2:+.1f}%")

con.close()
ENDOFPYTHON
python3 /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/run_backtest.py
