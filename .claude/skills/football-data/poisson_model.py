#!/usr/bin/env python3
"""
poisson_model.py — 博彩預測模型 + 價值投注偵測 + 回測框架

Using:
  - Standings GF/GA → Attack/Defense strength ratings
  - FC 26 avg OVR → Team quality proxy
  - The Odds API → Market odds for value detection

Models:
  1. Poisson Goal Model — Predict match scores from team strengths
  2. Kelly Criterion — Calculate optimal bet sizing
  3. Backtest — Validate model against historical results
"""
import sqlite3, sys, math, json
from datetime import datetime

DB = '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db'
ODDS_API_KEY = '7cb32f9dd8d62dc575d80b11fad88c3b'

ODDS_SPORTS = {
    'epl': 'soccer_epl',
    'laliga': 'soccer_spain_la_liga',
    'seriea': 'soccer_italy_serie_a',
    'bundesliga': 'soccer_germany_bundesliga',
    'ligue1': 'soccer_france_ligue_one',
}

# ════════════════════════════════════════════════════
#  Poisson Math
# ════════════════════════════════════════════════════

def poisson_prob(lam, k):
    """P(X=k) for Poisson distribution with mean lam."""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def poisson_matrix(lambda_home, lambda_away, max_goals=6):
    """Build score probability matrix."""
    matrix = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[(i, j)] = poisson_prob(lambda_home, i) * poisson_prob(lambda_away, j)
    # Add overflow
    overflow = 0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            overflow += matrix[(i, j)]
    # Normalize (should be close to 1 already)
    # Calculate margins
    return matrix

def match_probabilities(lambda_home, lambda_away, max_goals=6):
    """Calculate Home/Draw/Away probabilities from Poisson model."""
    matrix = poisson_matrix(lambda_home, lambda_away, max_goals)
    home_win = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i > j)
    draw = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i == j)
    away_win = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i < j)
    return home_win, draw, away_win, matrix

def over_under_prob(lambda_home, lambda_away, line=2.5, max_goals=6):
    """Calculate Over/Under probabilities."""
    matrix = poisson_matrix(lambda_home, lambda_away, max_goals)
    over = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i + j > line)
    under = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i + j < line)
    on_line = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i + j == line)
    return over + on_line * 0.5, under + on_line * 0.5  # half-push on exact line

def expected_score(matrix, max_goals=6):
    """Expected goals for each team from probability matrix."""
    e_home = sum(i * matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1))
    e_away = sum(j * matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1))
    return e_home, e_away

def most_likely_scores(matrix, n=5, max_goals=6):
    """Top N most likely exact scores."""
    scores = sorted(matrix.items(), key=lambda x: -x[1])
    return [(s, p) for s, p in scores[:n] if s[0] <= max_goals and s[1] <= max_goals]

def decimal_to_implied(odds):
    """Decimal odds to implied probability (remove margin)."""
    return 1.0 / odds

def remove_margin(probs):
    """Normalize probabilities to sum to 1.0 (remove bookmaker margin)."""
    total = sum(probs)
    if total == 0:
        return probs
    return [p / total for p in probs]

def kelly_fraction(prob, odds, fraction=0.25):
    """Kelly criterion with fractional Kelly for safety."""
    q = 1 - prob
    b = odds - 1
    kelly = (prob * b - q) / b
    return max(0, kelly * fraction)  # quarter Kelly

def implied_odds(prob):
    """Probability to fair decimal odds."""
    return 1.0 / prob if prob > 0 else 999

# ════════════════════════════════════════════════════
#  Team Strength from Standings
# ════════════════════════════════════════════════════

def get_team_ratings(league_key='epl'):
    """Calculate Attack/Defense strength from standings GF/GA per game."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT team_name, played, goals_for, goals_against, points, position "
        "FROM standings WHERE league_key = ? AND played > 0", (league_key,)
    ).fetchall()
    con.close()

    if not rows:
        return {}

    # League average: per-team per-game (NOT per-game total)
    # total_played counts each team's games, so per-team avg = total / total_played
    total_gf = sum(r['goals_for'] for r in rows)
    total_ga = sum(r['goals_against'] for r in rows)
    total_played = sum(r['played'] for r in rows)
    avg_gpg = total_gf / total_played  # avg goals scored per team per game
    avg_gpa = total_ga / total_played  # avg goals conceded per team per game

    ratings = {}
    for r in rows:
        gpg = r['goals_for'] / r['played']
        gpa = r['goals_against'] / r['played']
        # Strength relative to league average (1.0 = average)
        attack = gpg / avg_gpg if avg_gpg > 0 else 1.0
        defense = gpa / avg_gpa if avg_gpa > 0 else 1.0
        # Lower defense rating = better defense
        ratings[r['team_name']] = {
            'position': r['position'],
            'played': r['played'],
            'gf': r['goals_for'], 'ga': r['goals_against'],
            'gpg': round(gpg, 2), 'gpa': round(gpa, 2),
            'attack': round(attack, 3),    # >1 = scores more than avg
            'defense': round(defense, 3),  # >1 = concedes more than avg (BAD)
            'points': r['points'],
        }

    return ratings

def get_fc26_ratings(league_name='Premier League'):
    """Get FC 26 average OVR, shooting, defending per team."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT club_name, COUNT(*) as squad,
               ROUND(AVG(overall),1) as ovr,
               ROUND(AVG(shooting),1) as sho,
               ROUND(AVG(defending),1) as dfd,
               ROUND(AVG(pace),1) as pac,
               ROUND(AVG(passing),1) as pas
        FROM players WHERE league_name = ?
        GROUP BY club_name ORDER BY ovr DESC
    """, (league_name,)).fetchall()
    con.close()
    return {r['club_name']: dict(r) for r in rows}

def predict_match(home, away, ratings, home_adv=1.15, league_avg=1.35):
    """Predict match using Poisson model.
    
    Args:
        home_adv: Home advantage multiplier (typical 1.1-1.2)
        league_avg: League average goals per team per game
    Returns:
        dict with probabilities, expected score, value analysis
    """
    hr = ratings.get(home)
    ar = ratings.get(away)
    if not hr or not ar:
        return None

    # lambda = league_avg * own_attack * opp_defense_conceded
    # attack = own GPG / league GPG (>1 = scores more)
    # defense = opp GPA / league GPA (>1 = concedes more, so OPPONENT concedes more)
    # We want: home expected = league_avg * home_attack * away_defense_leakiness
    lambda_home = league_avg * hr['attack'] * ar['defense'] * home_adv
    lambda_away = league_avg * ar['attack'] * hr['defense']

    h_prob, d_prob, a_prob, matrix = match_probabilities(lambda_home, lambda_away)
    over_prob, under_prob = over_under_prob(lambda_home, lambda_away, 2.5)
    e_home, e_away = expected_score(matrix)
    top_scores = most_likely_scores(matrix)

    return {
        'home': home, 'away': away,
        'lambda_home': round(lambda_home, 2),
        'lambda_away': round(lambda_away, 2),
        'home_prob': round(h_prob, 3),
        'draw_prob': round(d_prob, 3),
        'away_prob': round(a_prob, 3),
        'over_prob': round(over_prob, 3),
        'under_prob': round(under_prob, 3),
        'expected_score': f"{e_home:.1f} - {e_away:.1f}",
        'top_scores': [(f"{h}-{a}", f"{p:.1%}") for (h, a), p in top_scores[:5]],
    }

# ════════════════════════════════════════════════════
#  Odds Comparison (The Odds API)
# ════════════════════════════════════════════════════

def fetch_odds(league_key='epl'):
    """Fetch current odds from The Odds API."""
    import urllib.request
    sport = ODDS_SPORTS.get(league_key)
    if not sport:
        print(f"❌ 不支援的聯賽: {league_key}"); return []

    url = (f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
           f"?apiKey={ODDS_API_KEY}&regions=uk,eu&markets=h2h,totals&oddsFormat=decimal")
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"❌ Odds API error: {e}"); return []

def find_value_bets(league_key='epl', value_threshold=0.05):
    """Compare model predictions with market odds to find value."""
    ratings = get_team_ratings(league_key)
    if not ratings:
        print(f"❌ 無積分榜數據: {league_key}"); return

    odds_data = fetch_odds(league_key)
    if not odds_data:
        return

    t_name = {'epl': 'Premier League', 'laliga': 'La Liga', 'seriea': 'Serie A',
              'bundesliga': 'Bundesliga', 'ligue1': 'Ligue 1'}.get(league_key, league_key)

    print(f"\n{'═'*75}")
    print(f"  💰 價值投注偵測 — {t_name}")
    print(f"  模型: Poisson (Standings GF/GA) | Home Advantage: 1.15")
    print(f"  價值閾值: 模型概率 > 市場隱含概率 + {value_threshold:.0%}")
    print(f"{'═'*75}")

    value_bets = []

    for event in odds_data:
        home_team = event['home_team']
        away_team = event['away_team']
        commence = event.get('commence_time', '')

        pred = predict_match(home_team, away_team, ratings)
        if not pred:
            continue

        # Find best odds across all bookmakers
        best = {'home': 0, 'draw': 0, 'away': 0, 'over': 0, 'under': 0}
        for bm in event.get('bookmakers', []):
            for mkt in bm.get('markets', []):
                key = mkt['key']
                for outcome in mkt.get('outcomes', []):
                    name = outcome['name']
                    price = outcome['price']
                    if key == 'h2h':
                        if name == home_team and price > best['home']:
                            best['home'] = price
                        elif name == 'Draw' and price > best['draw']:
                            best['draw'] = price
                        elif name == away_team and price > best['away']:
                            best['away'] = price
                    elif key == 'totals':
                        if name == 'Over' and price > best['over']:
                            best['over'] = price
                        elif name == 'Under' and price > best['under']:
                            best['under'] = price

        # Compare model vs market
        markets = []
        if best['home'] > 1:
            market_prob = remove_margin([decimal_to_implied(best['home']),
                                        decimal_to_implied(best['draw']),
                                        decimal_to_implied(best['away'])])
            # model: [home, draw, away]
            edges = [pred['home_prob'] - market_prob[0],
                     pred['draw_prob'] - market_prob[1],
                     pred['away_prob'] - market_prob[2]]
            labels = [f"主勝 {home_team}", "和局", f"客勝 {away_team}"]
            odds_list = [best['home'], best['draw'], best['away']]
            for edge, label, odds, mkt_prob in zip(edges, labels, odds_list, market_prob):
                if edge >= value_threshold:
                    kelly = kelly_fraction(pred[f'{"home" if "主" in label else "draw" if "和" in label else "away"}_prob'], odds)
                    value_bets.append({
                        'match': f"{home_team} vs {away_team}",
                        'bet': label,
                        'model_prob': pred[f'{"home" if "主" in label else "draw" if "和" in label else "away"}_prob'],
                        'market_prob': mkt_prob,
                        'edge': edge,
                        'best_odds': odds,
                        'kelly': kelly,
                        'ev': (pred[f'{"home" if "主" in label else "draw" if "和" in label else "away"}_prob'] * (odds - 1) - (1 - pred[f'{"home" if "主" in label else "draw" if "和" in label else "away"}_prob'])) * 100,
                    })

        if best['over'] > 1:
            market_ou = remove_margin([decimal_to_implied(best['over']),
                                       decimal_to_implied(best['under'])])
            over_edge = pred['over_prob'] - market_ou[0]
            under_edge = pred['under_prob'] - market_ou[1]
            if over_edge >= value_threshold:
                kelly = kelly_fraction(pred['over_prob'], best['over'])
                value_bets.append({
                    'match': f"{home_team} vs {away_team}",
                    'bet': "大球 2.5",
                    'model_prob': pred['over_prob'],
                    'market_prob': market_ou[0],
                    'edge': over_edge,
                    'best_odds': best['over'],
                    'kelly': kelly,
                    'ev': (pred['over_prob'] * (best['over'] - 1) - (1 - pred['over_prob'])) * 100,
                })
            elif under_edge >= value_threshold:
                kelly = kelly_fraction(pred['under_prob'], best['under'])
                value_bets.append({
                    'match': f"{home_team} vs {away_team}",
                    'bet': "小球 2.5",
                    'model_prob': pred['under_prob'],
                    'market_prob': market_ou[1],
                    'edge': under_edge,
                    'best_odds': best['under'],
                    'kelly': kelly,
                    'ev': (pred['under_prob'] * (best['under'] - 1) - (1 - pred['under_prob'])) * 100,
                })

    # Sort by edge
    value_bets.sort(key=lambda x: -x['edge'])

    if not value_bets:
        print(f"\n  📭 本輪無明顯價值投注（閾值 {value_threshold:.0%}）")
        print(f"  提示：可降低閾值至 0.02-0.03 查看更多機會\n")
        return

    print(f"\n  發現 {len(value_bets)} 個價值投注機會\n")
    print(f"  {'賽事':<35} {'投注':<16} {'模型':>6} {'市場':>6} {'Edge':>6} {'賠率':>6} {'Kelly':>6} {'EV%':>7}")
    print(f"  {'─'*35} {'─'*16} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*7}")

    for vb in value_bets:
        print(f"  {vb['match']:<35} {vb['bet']:<16} "
              f"{vb['model_prob']:>5.1%} {vb['market_prob']:>5.1%} "
              f"{vb['edge']:>+5.1%} {vb['best_odds']:>6.2f} "
              f"{vb['kelly']:>5.1%} {vb['ev']:>+6.1f}%")

    print(f"\n  Kelly = 建議下注比例（1/4 Kelly，保守策略）")
    print(f"  EV% = 期望值（正數 = 長期有利）")

# ════════════════════════════════════════════════════
#  Backtest: Simulate against standings data
# ════════════════════════════════════════════════════

def backtest_poisson(league_key='epl', home_adv=1.15):
    """Backtest Poisson model by simulating all pairings in standings.
    
    Since we don't have actual match-by-match results yet, we use
    a round-robin simulation approach and check if model predictions
    align with final standings positions.
    """
    ratings = get_team_ratings(league_key)
    if not ratings:
        print(f"❌ 無積分榜數據"); return

    teams = list(ratings.keys())
    n = len(teams)
    correct = 0
    total = 0
    bps_correct = 0  # bps = both predict same outcome

    print(f"\n{'═'*70}")
    print(f"  🧪 回測報告 — Poisson 模型 vs 積分榜")
    print(f"  聯賽: {league_key.upper()} | 球隊: {n} | 模擬對賽: {n*(n-1)//2}")
    print(f"  方法: 對每對球隊模擬雙回合，比較模型預測 vs 積分榜排名")
    print(f"{'═'*70}")

    # For each pair, predict both home/away
    for i in range(n):
        for j in range(i + 1, n):
            home, away = teams[i], teams[j]
            hr, ar = ratings[home], ratings[away]
            pred = predict_match(home, away, ratings, home_adv)
            if not pred:
                continue

            # Did model predict the higher-ranked team wins?
            # Use position: lower position = stronger team
            stronger_home = hr['position'] < ar['position']  # home is higher ranked?

            # Model prediction
            model_home_wins = pred['home_prob'] > pred['away_prob']
            model_favors_stronger = (stronger_home and model_home_wins) or (not stronger_home and not model_home_wins)

            if model_favors_stronger:
                bps_correct += 1
            total += 1

    alignment = bps_correct / total * 100 if total else 0

    print(f"\n  📊 結果:")
    print(f"  模型 vs 排名一致率: {bps_correct}/{total} ({alignment:.1f}%)")
    print(f"  (預期基線 ~50%，理想 >55%)")
    print()

    # Detailed team-by-team analysis
    print(f"  {'球隊':<20} {'排名':>4} {'積分':>4} {'GPG':>5} {'GPA':>5} {'ATT':>5} {'DEF':>5} {'隱含xG主':>8} {'隱含xG客':>8}")
    print(f"  {'─'*20} {'─'*4} {'─'*4} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*8} {'─'*8}")

    league_avg = 1.35
    for team in teams:
        r = ratings[team]
        xg_home = round(league_avg * r['attack'] * r['defense'] * home_adv, 2)  # vs self = league avg opponent
        xg_away = round(league_avg * r['attack'] * r['defense'], 2)
        # Actually let's compute vs league average opponent
        avg_def = sum(rr['defense'] for rr in ratings.values()) / len(ratings)
        avg_att = sum(rr['attack'] for rr in ratings.values()) / len(ratings)
        xg_home_vs_avg = round(league_avg * r['attack'] * avg_def * home_adv, 2)
        xg_away_vs_avg = round(league_avg * r['attack'] * avg_def, 2)  # defensive strength of avg opponent

        print(f"  {team:<20} {r['position']:>4} {r['points']:>4} {r['gpg']:>5.2f} {r['gpa']:>5.2f} "
              f"{r['attack']:>5.2f} {r['defense']:>5.2f} "
              f"{xg_home_vs_avg:>8.2f} {xg_away_vs_avg:>8.2f}")

    return {'alignment': alignment, 'bps_correct': bps_correct, 'total': total}

# ════════════════════════════════════════════════════
#  Full Match Prediction Display
# ════════════════════════════════════════════════════

def predict_and_display(home, away, league_key='epl'):
    """Full prediction report for a specific match."""
    ratings = get_team_ratings(league_key)
    pred = predict_match(home, away, ratings)

    if not pred:
        print(f"❌ 找不到球隊數據: {home} vs {away}"); return

    hr = ratings.get(home, {})
    ar = ratings.get(away, {})

    print(f"\n{'═'*60}")
    print(f"  ⚽ 預測: {home} vs {away}")
    print(f"  數據: {league_key.upper()} 積分榜 + Poisson 模型")
    print(f"{'═'*60}")

    print(f"\n  球隊實力:")
    print(f"  {'':20} {'排名':>4} {'GPG':>5} {'GPA':>5} {'ATT':>5} {'DEF':>5}")
    print(f"  {home:<20} {hr.get('position','?'):>4} {hr.get('gpg','?'):>5.2f} {hr.get('gpa','?'):>5.2f} {hr.get('attack','?'):>5.2f} {hr.get('defense','?'):>5.2f}")
    print(f"  {away:<20} {ar.get('position','?'):>4} {ar.get('gpg','?'):>5.2f} {ar.get('gpa','?'):>5.2f} {ar.get('attack','?'):>5.2f} {ar.get('defense','?'):>5.2f}")

    print(f"\n  模型預測 (Home Adv: 1.15):")
    print(f"  λ(Home) = {pred['lambda_home']:.2f}  |  λ(Away) = {pred['lambda_away']:.2f}")
    print(f"  預期比分: {pred['expected_score']}")

    print(f"\n  勝負概率:")
    print(f"    主勝: {pred['home_prob']:.1%}  (公平賠率: {implied_odds(pred['home_prob']):.2f})")
    print(f"    和局: {pred['draw_prob']:.1%}  (公平賠率: {implied_odds(pred['draw_prob']):.2f})")
    print(f"    客勝: {pred['away_prob']:.1%}  (公平賠率: {implied_odds(pred['away_prob']):.2f})")

    print(f"\n  大小球 (2.5):")
    print(f"    大球: {pred['over_prob']:.1%}  (公平賠率: {implied_odds(pred['over_prob']):.2f})")
    print(f"    小球: {pred['under_prob']:.1%}  (公平賠率: {implied_odds(pred['under_prob']):.2f})")

    print(f"\n  最可能比分:")
    for score, prob in pred['top_scores']:
        p_val = prob if isinstance(prob, float) else float(str(prob).replace('%', '')) / 100
        bar = '█' * int(p_val * 100)
        print(f"    {score:<8} {p_val:>5.1%}  {bar}")

# ════════════════════════════════════════════════════
#  Main CLI
# ════════════════════════════════════════════════════

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)

    cmd = args[0].lower()
    rest = args[1:]

    if cmd == 'predict' and len(rest) >= 2:
        league = rest[0] if len(rest) > 2 else 'epl'
        home, away = (rest[-2], rest[-1]) if len(rest) > 2 else (rest[0], rest[1])
        predict_and_display(home, away, league)
    elif cmd == 'value':
        league = rest[0] if rest else 'epl'
        threshold = float(rest[1]) if len(rest) > 1 else 0.05
        find_value_bets(league, threshold)
    elif cmd == 'backtest':
        league = rest[0] if rest else 'epl'
        backtest_poisson(league)
    elif cmd == 'ratings':
        league = rest[0] if rest else 'epl'
        ratings = get_team_ratings(league)
        print(f"\n  {league.upper()} Team Strength Ratings\n")
        print(f"  {'Team':<20} {'Pos':>3} {'Pts':>4} {'GPG':>5} {'GPA':>5} {'ATT':>6} {'DEF':>6}")
        print(f"  {'─'*20} {'─'*3} {'─'*4} {'─'*5} {'─'*5} {'─'*6} {'─'*6}")
        for team, r in sorted(ratings.items(), key=lambda x: x[1]['position']):
            print(f"  {team:<20} {r['position']:>3} {r['points']:>4} {r['gpg']:>5.2f} {r['gpa']:>5.2f} {r['attack']:>6.3f} {r['defense']:>6.3f}")
    else:
        print("Usage:")
        print("  predict <league> <home> <away>   — 預測單場")
        print("  value [league] [threshold]       — 偵測價值投注")
        print("  backtest [league]                — 回測模型")
        print("  ratings [league]                 — 球隊實力評分")
