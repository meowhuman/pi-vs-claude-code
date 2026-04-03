#!/usr/bin/env python3
"""
backtest_engine.py — 真實回測引擎
模擬 Poisson 模型 vs 莊家（含市場噪音），用 Kelly 資金管理。
"""
import sqlite3, math, random, sys

DB = '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db'

def poisson_prob(lam, k):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def match_probs(lam_h, lam_a, max_g=6):
    h = d = a = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            p = poisson_prob(lam_h, i) * poisson_prob(lam_a, j)
            if i > j: h += p
            elif i == j: d += p
            else: a += p
    return h, d, a

def over_under(lam_h, lam_a, line=2.5, max_g=6):
    over = under = on = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            p = poisson_prob(lam_h, i) * poisson_prob(lam_a, j)
            if i + j > line: over += p
            elif i + j < line: under += p
            else: on += p
    return over + on * 0.5, under + on * 0.5

def kelly(prob, odds, frac=0.25):
    q, b = 1 - prob, odds - 1
    if b <= 0: return 0
    return max(0, (prob * b - q) / b * frac)

def get_ratings(league_key='epl'):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT team_name, played, goals_for, goals_against, points, position "
        "FROM standings WHERE league_key = ? AND played > 0", (league_key,)
    ).fetchall()
    con.close()
    if not rows: return {}
    tp = sum(r['played'] for r in rows)
    ag = sum(r['goals_for'] for r in rows) / tp
    ac = sum(r['goals_against'] for r in rows) / tp
    ratings = {}
    for r in rows:
        gpg = r['goals_for'] / r['played']
        gpa = r['goals_against'] / r['played']
        ratings[r['team_name']] = {
            'pos': r['position'], 'pts': r['points'],
            'gpg': gpg, 'gpa': gpa,
            'att': gpg / ag, 'def': gpa / ac,
        }
    return ratings

def true_to_market(p1, p2, p3, n1=0, n2=0, n3=0, margin=0.05):
    """True probs → market odds with noise + bookmaker margin."""
    raw = [max(0.01, p1+n1), max(0.01, p2+n2), max(0.01, p3+n3)]
    s = sum(raw)
    fair = [p/s for p in raw]
    return [1/(p/(1-margin)) for p in fair]

def sample_poisson(lam):
    cum_p = random.random()
    k = 0
    while True:
        cum_p -= poisson_prob(lam, k)
        if cum_p <= 0: return k
        k += 1
        if k > 15: return k

def simulate(league_key, home_adv=1.15, avg_g=1.37, margin=0.05,
             threshold=0.03, kelly_f=0.25, bankroll=1000, seed=42):
    random.seed(seed)
    ratings = get_ratings(league_key)
    if not ratings: return None
    teams = sorted(ratings.keys(), key=lambda t: ratings[t]['pos'])
    n = len(teams)
    bets, peak = [], bankroll
    peak = bankroll
    max_dd = wins = losses = pushes = 0

    for i in range(n):
        for j in range(n):
            if i == j: continue
            home, away = teams[i], teams[j]
            hr, ar = ratings[home], ratings[away]
            lam_h = avg_g * hr['att'] * ar['def'] * home_adv
            lam_a = avg_g * ar['att'] * hr['def']
            h_t, d_t, a_t = match_probs(lam_h, lam_a)
            o_t, u_t = over_under(lam_h, lam_a)

            # Market odds with random noise (simulates market inefficiency)
            noise = lambda: random.gauss(0, 0.02)
            h_o, d_o, a_o = true_to_market(h_t, d_t, a_t, noise(), noise(), noise(), margin)
            o_o, u_o = true_to_market(o_t, u_t, 0.01, noise(), noise(), margin)[:2]

            # Find value bets
            best = None
            for name, model_p, mkt_odds in [
                ('home', h_t, h_o), ('draw', d_t, d_o), ('away', a_t, a_o),
                ('over', o_t, o_o), ('under', u_t, u_o),
            ]:
                edge = model_p - 1/mkt_odds
                if edge > threshold and (best is None or edge > best[0]):
                    best = (edge, name, model_p, mkt_odds)

            if not best: continue
            edge, name, model_p, odds = best

            # Simulate result
            hg, ag = sample_poisson(lam_h), sample_poisson(lam_a)
            won = push = False
            if name == 'home' and hg > ag: won = True
            elif name == 'draw' and hg == ag: won = True
            elif name == 'away' and hg < ag: won = True
            elif name == 'over' and hg + ag > 2.5: won = True
            elif name == 'under' and hg + ag < 2.5: won = True
            elif name in ('over','under') and hg + ag == 2.5: push = True

            stake = round(bankroll * kelly(model_p, odds, kelly_f), 2)
            stake = max(stake, 1)
            stake = min(stake, bankroll * 0.1)

            if won:
                profit = round(stake * (odds - 1), 2)
                bankroll += profit; wins += 1; result = 'WIN'
            elif push:
                profit = 0; pushes += 1; result = 'PUSH'
            else:
                profit = -stake; bankroll += profit; losses += 1; result = 'LOSS'

            peak = max(peak, bankroll)
            max_dd = max(max_dd, peak - bankroll)

            label = {'home':'主勝','draw':'和局','away':'客勝','over':'大2.5','under':'小2.5'}[name]
            bets.append({'home':home,'away':away,'score':f'{hg}-{ag}','bet':label,
                         'odds':odds,'edge':edge,'stake':stake,'profit':profit,
                         'bankroll':round(bankroll,2),'result':result})

    return {'bets':bets,'final':bankroll,'wins':wins,'losses':losses,'pushes':pushes,
            'max_dd':max_dd,'peak':peak}

def run(league_key='epl', n_sim=5, seed=42):
    ratings = get_ratings(league_key)
    if not ratings: print("❌ 無數據"); return
    names = {'epl':'Premier League','laliga':'La Liga','seriea':'Serie A',
             'bundesliga':'Bundesliga','ligue1':'Ligue 1'}

    print(f"\n{'═'*70}")
    print(f"  🧪 回測引擎 — Poisson vs 莊家（含市場噪音）")
    print(f"  聯賽: {names.get(league_key,league_key)} | 模擬: {n_sim} 次 | 資金: $1,000")
    print(f"  Kelly 1/4 | Edge 閾值: 3% | Margin: 5% | 噪音 σ: 2%")
    print(f"{'═'*70}")

    results = []
    for s in range(n_sim):
        r = simulate(league_key, seed=seed+s)
        if r: results.append(r)

    if not results: print("❌ 失敗"); return

    print(f"\n  {'#':>3} {'下注':>6} {'勝':>4} {'負':>4} {'勝率':>6} {'最終資金':>10} {'ROI':>7} {'最大回撤':>8}")
    print(f"  {'─'*3} {'─'*6} {'─'*4} {'─'*4} {'─'*6} {'─'*10} {'─'*7} {'─'*8}")

    rois = []
    for i, r in enumerate(results):
        total = r['wins'] + r['losses']
        wr = r['wins']/total*100 if total else 0
        roi = (r['final'] - 1000) / 1000 * 100
        rois.append(roi)
        print(f"  {i+1:>3} {total:>6} {r['wins']:>4} {r['losses']:>4} {wr:>5.1f}% "
              f"${r['final']:>9.0f} {roi:>+6.1f}% ${r['max_dd']:>7.0f}")

    avg_roi = sum(rois)/len(rois)
    avg_final = sum(r['final'] for r in results)/len(results)
    avg_w = sum(r['wins'] for r in results)/len(results)
    avg_l = sum(r['losses'] for r in results)/len(results)

    print(f"  {'─'*3} {'─'*6} {'─'*4} {'─'*4} {'─'*6} {'─'*10} {'─'*7} {'─'*8}")
    print(f"  {'AVG':>3} {int(avg_w)+int(avg_l):>6} {int(avg_w):>4} {int(avg_l):>4} "
          f"{avg_w/(avg_w+avg_l)*100:>5.1f}% ${avg_final:>9.0f} {avg_roi:>+6.1f}%")

    best = max(results, key=lambda r: r['final'])
    worst = min(results, key=lambda r: r['final'])
    print(f"\n  📊 分佈: 最佳 ${best['final']:.0f} | 最差 ${worst['final']:.0f} | 平均 ${avg_final:.0f}")
    print(f"  💡 平均 ROI: {avg_roi:+.1f}% | 勝率: {avg_w/(avg_w+avg_l)*100:.1f}%")

    # Show sample bets
    top = sorted(best['bets'], key=lambda b: -b['edge'])[:8]
    print(f"\n  📋 最佳模擬 — 高 Edge 投注:")
    print(f"  {'賽事':<30} {'投注':<8} {'比分':>5} {'賠率':>5} {'Edge':>6} {'Stake':>7} {'P&L':>8} {'結果':>5}")
    print(f"  {'─'*30} {'─'*8} {'─'*5} {'─'*5} {'─'*6} {'─'*7} {'─'*8} {'─'*5}")
    for b in top:
        print(f"  {b['home'][:14]:<14}vs{b['away'][:14]:<14} {b['bet']:<8} "
              f"{b['score']:>5} {b['odds']:>5.2f} {b['edge']:>+5.1%} "
              f"${b['stake']:>6.0f} ${b['profit']:>+7.0f} {b['result']:>5}")

    # Insights
    print(f"\n  {'═'*70}")
    print(f"  💡 模型診斷:")
    breakeven_wr = 1 / 1.05 * 100  # ~52.4% for 5% margin
    actual_wr = avg_w/(avg_w+avg_l)*100 if (avg_w+avg_l) else 0
    if avg_roi > 0:
        print(f"  ✅ 正期望值 — 模型能在莊家 margin 下盈利")
    else:
        print(f"  ❌ 負期望值 — 莊家 margin 吃掉利潤，需提升模型準確度")
    print(f"  勝率 {actual_wr:.1f}% — 需 >{breakeven_wr:.1f}% 才能克服 margin")
    print(f"  建議: 降低 edge 閾值到 1-2% 可增加下注次數，用大樣本驗證")

if __name__ == '__main__':
    league = sys.argv[1] if len(sys.argv) > 1 else 'epl'
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    run(league, n)
