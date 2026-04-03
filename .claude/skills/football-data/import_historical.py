#!/usr/bin/env python3
"""import_historical.py — 從 football-data.co.uk 匯入歷史賽果+賠率到本地 DB"""
import csv, sqlite3, io, urllib.request

DB = '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db'
BASE = 'https://www.football-data.co.uk/mmz4281'

LEAGUES = {
    'E0': ('epl', 'Premier League'),
    'SP1': ('laliga', 'La Liga'),
    'I1': ('seriea', 'Serie A'),
    'D1': ('bundesliga', 'Bundesliga'),
    'F1': ('ligue1', 'Ligue 1'),
}

def dl(code):
    req = urllib.request.Request(f"{BASE}/2425/{code}.csv")
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8-sig')

def sf(v):
    try: return float(v) if v and v.strip() else None
    except: return None

def main():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS historical_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        league_key TEXT, season TEXT, date TEXT,
        home_team TEXT, away_team TEXT,
        ft_hg INTEGER, ft_ag INTEGER, ft_result TEXT,
        ht_hg INTEGER, ht_ag INTEGER, ht_result TEXT,
        h_shots INTEGER, a_shots INTEGER,
        h_shots_t INTEGER, a_shots_t INTEGER,
        h_corners INTEGER, a_corners INTEGER,
        h_fouls INTEGER, a_fouls INTEGER,
        h_yellow INTEGER, a_yellow INTEGER,
        h_red INTEGER, a_red INTEGER,
        b365_h REAL, b365_d REAL, b365_a REAL,
        b365_o25 REAL, b365_u25 REAL,
        ps_h REAL, ps_d REAL, ps_a REAL,
        avg_h REAL, avg_d REAL, avg_a REAL,
        max_h REAL, max_d REAL, max_a REAL
    )""")
    con.commit()

    total = 0
    for code, (lk, name) in LEAGUES.items():
        for season_code, season_label in [('2425','2024-25'),('2526','2025-26')]:
            try:
                req = urllib.request.Request(f"{BASE}/{season_code}/{code}.csv")
                req.add_header('User-Agent', 'Mozilla/5.0')
                with urllib.request.urlopen(req, timeout=15) as r:
                    raw = r.read().decode('utf-8-sig')
            except Exception as e:
                print(f"  ❌ {name} {season_label}: {e}"); continue

            rows = list(csv.DictReader(io.StringIO(raw)))
            count = 0
            for r in rows:
                ftr = (r.get('FTR') or '').strip()
                if not ftr: continue
                try:
                    con.execute("""INSERT OR IGNORE INTO historical_matches
                        (league_key,season,date,home_team,away_team,
                         ft_hg,ft_ag,ft_result,ht_hg,ht_ag,ht_result,
                         h_shots,a_shots,h_shots_t,a_shots_t,
                         h_corners,a_corners,h_fouls,a_fouls,
                         h_yellow,a_yellow,h_red,a_red,
                         b365_h,b365_d,b365_a,b365_o25,b365_u25,
                         ps_h,ps_d,ps_a,avg_h,avg_d,avg_a,max_h,max_d,max_a)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (lk,season_label,r.get('Date'),r.get('HomeTeam'),r.get('AwayTeam'),
                         sf(r.get('FTHG')),sf(r.get('FTAG')),ftr,
                         sf(r.get('HTHG')),sf(r.get('HTAG')),r.get('HTR',''),
                         sf(r.get('HS')),sf(r.get('AS')),sf(r.get('HST')),sf(r.get('AST')),
                         sf(r.get('HF')),sf(r.get('AF')),sf(r.get('HY')),sf(r.get('AY')),
                         sf(r.get('HR')),sf(r.get('AR')),
                         sf(r.get('B365H')),sf(r.get('B365D')),sf(r.get('B365A')),
                         sf(r.get('B365>2.5')),sf(r.get('B365<2.5')),
                         sf(r.get('PSH')),sf(r.get('PSD')),sf(r.get('PSA')),
                         sf(r.get('AvgH')),sf(r.get('AvgD')),sf(r.get('AvgA')),
                         sf(r.get('MaxH')),sf(r.get('MaxD')),sf(r.get('MaxA'))))
                    count += 1
                except: pass
            total += count
            con.commit()
            print(f"  ✅ {name:<18} {season_label}  {count:>4} matches")

    con.close()
    print(f"\n  📊 總計: {total} matches imported")

if __name__ == '__main__':
    main()
