#!/usr/bin/env python3
"""import_historical.py — football-data.co.uk → SQLite"""
import csv, sqlite3, io, urllib.request

DB = '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db'
BASE = 'https://www.football-data.co.uk/mmz4281'

LEAGUES = {
    'E0': ('epl', 'Premier League'), 'SP1': ('laliga', 'La Liga'),
    'I1': ('seriea', 'Serie A'),    'D1': ('bundesliga', 'Bundesliga'),
    'F1': ('ligue1', 'Ligue 1'),
}

COLS = """league_key TEXT, season TEXT, date TEXT, home_team TEXT, away_team TEXT,
ft_hg INTEGER, ft_ag INTEGER, ft_result TEXT,
ht_hg INTEGER, ht_ag INTEGER, ht_result TEXT,
h_shots INTEGER, a_shots INTEGER, h_shots_t INTEGER, a_shots_t INTEGER,
h_corners INTEGER, a_corners INTEGER, h_fouls INTEGER, a_fouls INTEGER,
h_yellow INTEGER, a_yellow INTEGER, h_red INTEGER, a_red INTEGER,
b365_h REAL, b365_d REAL, b365_a REAL, b365_o25 REAL, b365_u25 REAL,
ps_h REAL, ps_d REAL, ps_a REAL, avg_h REAL, avg_d REAL, avg_a REAL,
max_h REAL, max_d REAL, max_a REAL"""

CREATE = f"CREATE TABLE IF NOT EXISTS historical_matches (id INTEGER PRIMARY KEY, {COLS})"

CSV_MAP = [
    ('league_key', None), ('season', None), ('date', 'Date'), ('home_team', 'HomeTeam'),
    ('away_team', 'AwayTeam'), ('ft_hg', 'FTHG'), ('ft_ag', 'FTAG'), ('ft_result', 'FTR'),
    ('ht_hg', 'HTHG'), ('ht_ag', 'HTAG'), ('ht_result', 'HTR'),
    ('h_shots', 'HS'), ('a_shots', 'AS'), ('h_shots_t', 'HST'), ('a_shots_t', 'AST'),
    ('h_corners', 'HF'), ('a_corners', 'AF'), ('h_fouls', None), ('a_fouls', None),
    ('h_yellow', 'HY'), ('a_yellow', 'AY'), ('h_red', 'HR'), ('a_red', 'AR'),
    ('b365_h', 'B365H'), ('b365_d', 'B365D'), ('b365_a', 'B365A'),
    ('b365_o25', 'B365>2.5'), ('b365_u25', 'B365<2.5'),
    ('ps_h', 'PSH'), ('ps_d', 'PSD'), ('ps_a', 'PSA'),
    ('avg_h', 'AvgH'), ('avg_d', 'AvgD'), ('avg_a', 'AvgA'),
    ('max_h', 'MaxH'), ('max_d', 'MaxD'), ('max_a', 'MaxA'),
]
PH = ','.join(['?' for _ in CSV_MAP])
INSERT = f"INSERT OR IGNORE INTO historical_matches ({','.join(c[0] for c in CSV_MAP)}) VALUES ({PH})"

def sf(v):
    try: return float(v) if v and v.strip() else None
    except: return None

def main():
    con = sqlite3.connect(DB)
    con.execute(CREATE)
    con.commit()
    total = 0
    for code, (lk, name) in LEAGUES.items():
        for sc, sl in [('2425','2024-25'),('2526','2025-26')]:
            try:
                req = urllib.request.Request(f"{BASE}/{sc}/{code}.csv")
                req.add_header('User-Agent', 'Mozilla/5.0')
                with urllib.request.urlopen(req, timeout=15) as r:
                    raw = r.read().decode('utf-8-sig')
            except Exception as e:
                print(f"  ❌ {name} {sl}: {e}"); continue
            rows = list(csv.DictReader(io.StringIO(raw)))
            count = 0
            for r in rows:
                ftr = (r.get('FTR') or '').strip()
                if not ftr: continue
                try:
                    vals = []
                    for col_name, csv_key in CSV_MAP:
                        if col_name in ('league_key', 'season'):
                            vals.append(lk if col_name == 'league_key' else sl)
                        elif csv_key is None:
                            vals.append(None)
                        else:
                            vals.append(sf(r.get(csv_key)))
                    con.execute(INSERT, vals)
                    count += 1
                except: pass
            total += count
            con.commit()
            print(f"  ✅ {name:<18} {sl}  {count:>4} matches")
    con.close()
    print(f"\n  📊 {total} matches imported")

if __name__ == '__main__':
    main()
