#!/usr/bin/env python3
"""
fc26q.py — FC 26 SQLite Quick Query CLI
Usage:
  python3 fc26q.py player <name>
  python3 fc26q.py team <club_name>
  python3 fc26q.py compare <club1> vs <club2>
  python3 fc26q.py top <league> [limit]
  python3 fc26q.py search <name>
"""
import sqlite3, sys, os

DB = '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db'

COLS = 'short_name, player_positions, overall, potential, pace, shooting, passing, dribbling, defending, physic'
HEADER = f"{'Name':<22} {'Pos':<14} {'OVR':>4} {'POT':>4} {'PAC':>4} {'SHO':>4} {'PAS':>4} {'DRI':>4} {'DEF':>4} {'PHY':>4}"
SEP = '-' * 90

def row_line(r):
    def v(x): return str(x) if x is not None else '-'
    return f"{r[0]:<22} {r[1]:<14} {v(r[2]):>4} {v(r[3]):>4} {v(r[4]):>4} {v(r[5]):>4} {v(r[6]):>4} {v(r[7]):>4} {v(r[8]):>4} {v(r[9]):>4}"

def con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def cmd_player(name):
    db = con()
    rows = db.execute(
        "SELECT * FROM players WHERE long_name LIKE ? OR short_name LIKE ? ORDER BY overall DESC",
        (f'%{name}%', f'%{name}%')
    ).fetchall()
    if not rows:
        print(f"No player found: {name}"); return
    for p in rows:
        print(f"\n{'='*55}")
        print(f"  {p['long_name']}")
        print(f"  {p['club_name']} | {p['league_name']}")
        print(f"  Age:{p['age']}  Foot:{p['preferred_foot']}  Height:{p['height_cm']}cm")
        print(f"  Value:€{(p['value_eur'] or 0):,}  Wage:€{(p['wage_eur'] or 0):,}/wk")
        print(f"  Positions: {p['player_positions']}")
        print(f"{'='*55}")
        print(f"  {'Overall':<22} {p['overall']}  (Potential: {p['potential']})")
        groups = [
            ('PACE',     p['pace'],     [('Acceleration',p['acceleration']),('Sprint Speed',p['sprint_speed'])]),
            ('SHOOTING', p['shooting'], [('Finishing',p['finishing']),('Positioning',p['positioning']),('Shot Power',p['shot_power']),('Long Shots',p['long_shots']),('Volleys',p['volleys']),('Penalties',p['penalties'])]),
            ('PASSING',  p['passing'],  [('Short Pass',p['short_passing']),('Long Pass',p['long_passing']),('Vision',p['vision']),('Crossing',p['crossing']),('Curve',p['curve']),('FK Acc',p['fk_accuracy'])]),
            ('DRIBBLING',p['dribbling'],[('Dribbling',p['skill_dribbling']),('Ball Ctrl',p['ball_control']),('Agility',p['agility']),('Balance',p['balance']),('Reactions',p['reactions'])]),
            ('DEFENDING', p['defending'],[('Marking',p['marking_awareness']),('Stand Tackle',p['standing_tackle']),('Slide Tackle',p['sliding_tackle']),('Intercept',p['interceptions'])]),
            ('PHYSICAL',  p['physic'],  [('Stamina',p['stamina']),('Strength',p['strength']),('Jumping',p['jumping']),('Aggression',p['aggression'])]),
        ]
        for grp, base, subs in groups:
            print(f"\n  {grp} ({base})")
            for label, val in subs:
                bar = '█' * int((val or 0) // 10) if val else ''
                print(f"    {label:<20} {str(val or '-'):>4}  {bar}")
    db.close()

def cmd_team(club):
    db = con()
    rows = db.execute(
        f"SELECT {COLS} FROM players WHERE club_name LIKE ? ORDER BY overall DESC",
        (f'%{club}%',)
    ).fetchall()
    if not rows:
        print(f"No team found: {club}"); return
    club_actual = rows[0][0] if rows else club
    print(f"\n{rows[0][0]} — wait, club: checking...")
    # get real club name
    real = db.execute("SELECT DISTINCT club_name FROM players WHERE club_name LIKE ?", (f'%{club}%',)).fetchone()
    print(f"\n{real[0]} ({len(rows)} players)\n")
    print(HEADER); print(SEP)
    for r in rows:
        print(row_line(r))
    # avg
    avgs = db.execute(
        "SELECT AVG(overall),AVG(pace),AVG(shooting),AVG(passing),AVG(dribbling),AVG(defending),AVG(physic) FROM players WHERE club_name LIKE ?",
        (f'%{club}%',)
    ).fetchone()
    print(SEP)
    print(f"{'SQUAD AVG':<22} {'':14} {avgs[0]:>4.0f} {'':>4} {avgs[1]:>4.0f} {avgs[2]:>4.0f} {avgs[3]:>4.0f} {avgs[4]:>4.0f} {avgs[5]:>4.0f} {avgs[6]:>4.0f}")
    db.close()

def cmd_compare(args):
    # parse "Arsenal vs Liverpool" or ["Arsenal", "Liverpool"]
    text = ' '.join(args)
    if ' vs ' in text.lower():
        parts = text.lower().split(' vs ')
        club1, club2 = parts[0].strip(), parts[1].strip()
    elif len(args) >= 2:
        club1, club2 = args[0], args[1]
    else:
        print("Usage: compare <club1> vs <club2>"); return

    db = con()
    for club in [club1, club2]:
        rows = db.execute(
            f"SELECT {COLS} FROM players WHERE LOWER(club_name) LIKE ? ORDER BY overall DESC LIMIT 15",
            (f'%{club}%',)
        ).fetchall()
        real = db.execute("SELECT DISTINCT club_name FROM players WHERE LOWER(club_name) LIKE ?", (f'%{club}%',)).fetchone()
        name = real[0] if real else club
        avgs = db.execute(
            "SELECT AVG(overall),AVG(pace),AVG(shooting),AVG(passing),AVG(dribbling),AVG(defending),AVG(physic),COUNT(*) FROM players WHERE LOWER(club_name) LIKE ?",
            (f'%{club}%',)
        ).fetchone()
        print(f"\n{'='*90}")
        print(f"  {name}  —  Squad: {int(avgs[7])} players  |  Avg OVR: {avgs[0]:.1f}  PAC:{avgs[1]:.0f} SHO:{avgs[2]:.0f} PAS:{avgs[3]:.0f} DRI:{avgs[4]:.0f} DEF:{avgs[5]:.0f} PHY:{avgs[6]:.0f}")
        print(f"{'='*90}")
        print(HEADER); print(SEP)
        for r in rows:
            print(row_line(r))
    db.close()

def cmd_top(args):
    league = ' '.join(args[:-1]) if args[-1].isdigit() else ' '.join(args)
    limit  = int(args[-1]) if args and args[-1].isdigit() else 20

    LEAGUE_MAP = {
        'epl': 'Premier League', 'premier': 'Premier League', 'pl': 'Premier League',
        'laliga': 'La Liga', 'la liga': 'La Liga', 'spain': 'La Liga',
        'seriea': 'Serie A', 'serie a': 'Serie A', 'italy': 'Serie A',
        'bundesliga': 'Bundesliga', 'germany': 'Bundesliga',
        'ligue1': 'Ligue 1', 'ligue 1': 'Ligue 1', 'france': 'Ligue 1',
    }
    lg = LEAGUE_MAP.get(league.lower().strip(), league)
    db = con()
    rows = db.execute(
        f"SELECT {COLS} FROM players WHERE league_name LIKE ? ORDER BY overall DESC LIMIT ?",
        (f'%{lg}%', limit)
    ).fetchall()
    print(f"\nTop {limit} — {lg}\n")
    print(HEADER); print(SEP)
    for r in rows:
        print(row_line(r))
    db.close()

def cmd_search(name):
    db = con()
    rows = db.execute(
        f"SELECT {COLS}, league_name, club_name FROM players WHERE long_name LIKE ? OR short_name LIKE ? ORDER BY overall DESC LIMIT 20",
        (f'%{name}%', f'%{name}%')
    ).fetchall()
    print(f"\nSearch: '{name}' — {len(rows)} results\n")
    print(HEADER); print(SEP)
    for r in rows:
        print(f"{row_line(r)}  {r[10]:<20} {r[11]}")
    db.close()

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)
    cmd = args[0].lower()
    rest = args[1:]
    if cmd == 'player':   cmd_player(' '.join(rest))
    elif cmd == 'team':   cmd_team(' '.join(rest))
    elif cmd == 'compare':cmd_compare(rest)
    elif cmd == 'top':    cmd_top(rest)
    elif cmd == 'search': cmd_search(' '.join(rest))
    else:
        print(f"Unknown command: {cmd}\n{__doc__}")
