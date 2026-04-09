#!/usr/bin/env python3
"""
sportapi_stats.py — SportAPI7 即時數據抓取 + 本地快取
Usage: see function definitions below
"""
import os, sqlite3, sys, json, time, csv, urllib.request, urllib.error
from datetime import datetime, timedelta

# ── Config ──────────────────────────────────────────
DB_PATH = os.getenv(
    'SOCCER_BETTING_DB_PATH',
    '/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db',
)
API_KEY = os.getenv('SPORTAPI7_API_KEY', '')
API_HOST = os.getenv('SPORTAPI7_API_HOST', 'sportapi7.p.rapidapi.com')
BASE_URL = f'https://{API_HOST}/api/v1'
REQUEST_DELAY = 1.5

TOURNAMENTS = {
    'epl':       {'name': 'Premier League',       'tid': 17, 'sid': 76986},
    'laliga':    {'name': 'La Liga',               'tid': 8,  'sid': 77559},
    'seriea':    {'name': 'Serie A',               'tid': 23, 'sid': 76457},
    'bundesliga':{'name': 'Bundesliga',            'tid': 35, 'sid': 77333},
    'ligue1':    {'name': 'Ligue 1',               'tid': 34, 'sid': 77356},
    'ucl':       {'name': 'UEFA Champions League', 'tid': 7,  'sid': 76953},
}

LEAGUE_TO_KEY = {
    'Premier League': 'epl', 'La Liga': 'laliga', 'Serie A': 'seriea',
    'Bundesliga': 'bundesliga', 'Ligue 1': 'ligue1',
    'UEFA Champions League': 'ucl',
}

PLAYER_ID_MAP = {
    'Bukayo Saka': 934235, 'Martin Ødegaard': 944921, 'Declan Rice': 941247,
    'William Saliba': 962117, 'Kai Havertz': 836705, 'Gabriel Martinelli': 922573,
    'Gabriel Jesus': 794839, 'Thomas Partey': 831730, 'Leandro Trossard': 880031,
    'Viktor Gyökeres': 804508,
    'Lamine Yamal': 1402912, 'Robert Lewandowski': 32526, 'Pedri': 861450,
    'Gavi': 886512, 'Raphinha': 854493, 'Frenkie de Jong': 851477,
    'Ronald Araújo': 852653,
    'Vinícius Júnior': 868812, 'Jude Bellingham': 874630, 'Rodrygo': 854895,
    'Federico Valverde': 860136, 'Eduardo Camavinga': 912433,
    'Aurélien Tchouaméni': 908396, 'Dani Carvajal': 832570,
    'Erling Haaland': 901324, 'Phil Foden': 938704, 'Kevin De Bruyne': 581453,
    'Bernardo Silva': 832699, 'Rodri': 832745, 'Rúben Dias': 842112,
}

TEAM_ID_MAP = {
    'Arsenal': 42, 'Man City': 17, 'Man Utd': 35, 'Aston Villa': 40,
    'Liverpool': 44, 'Chelsea': 38, 'Tottenham': 33, 'Newcastle': 39,
    'Brighton': 30, 'West Ham': 37, 'Fulham': 43, 'Everton': 48,
    'Brentford': 50, 'Bournemouth': 60, 'Crystal Palace': 7,
    'Sunderland': 41, 'Nottm Forest': 14, 'Leeds': 34, 'Burnley': 6, 'Wolves': 3,
    'Barcelona': 2817, 'Real Madrid': 2829, 'Atletico': 2836,
    'Villarreal': 2819, 'Real Betis': 2816, 'Real Sociedad': 2824,
    'Athletic': 2825, 'Sevilla': 2833, 'Valencia': 2828,
    'Girona': 24264, 'Mallorca': 2826, 'Celta': 2821,
    'Inter': 2697, 'Milan': 2692, 'Napoli': 2714, 'Juventus': 2687,
    'Roma': 2702, 'Atalanta': 2686, 'Lazio': 2699, 'Fiorentina': 2693,
    'Bayern': 2672, 'Dortmund': 2673, 'Leverkusen': 2681,
    'Stuttgart': 2677, 'Leipzig': 36360, 'Frankfurt': 2674,
    'PSG': 1644, 'Marseille': 1641, 'Lyon': 1649, 'Lille': 1643,
    'Monaco': 1653, 'Nice': 1661, 'Lens': 1648, 'Rennes': 1658,
}

# ════════════════════════════════════════════════════
#  Core helpers
# ════════════════════════════════════════════════════

def api_get(path):
    url = f"{BASE_URL}/{path}"
    req = urllib.request.Request(url)
    req.add_header('x-rapidapi-key', API_KEY)
    req.add_header('x-rapidapi-host', API_HOST)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {'_error': f'HTTP {e.code}'}
    except Exception as e:
        return {'_error': str(e)}

def check_api():
    data = api_get("sport/football/scheduled-events/2026-04-01")
    if '_error' in data:
        print(f"  ❌ API 錯誤: {data['_error']}"); return False
    events = data.get('events', [])
    if events:
        print(f"  ✅ SportAPI7 正常 ({len(events)} 場賽事)"); return True
    print(f"  ⚠️ 異常回應"); return False

def get_con():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def ensure_tables():
    con = get_con()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS season_stats (
            id INTEGER PRIMARY KEY, fc26_player_id TEXT, sportapi_player_id INTEGER,
            player_name TEXT, club_name TEXT, league_key TEXT,
            tournament_id INTEGER, season_id INTEGER,
            appearances INTEGER DEFAULT 0, minutes_played INTEGER DEFAULT 0,
            goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0,
            shots_total INTEGER DEFAULT 0, shots_on_target INTEGER DEFAULT 0,
            xg REAL DEFAULT 0, xa REAL DEFAULT 0,
            passes_total INTEGER DEFAULT 0, passes_key INTEGER DEFAULT 0,
            passes_accuracy REAL DEFAULT 0, crosses_total INTEGER DEFAULT 0,
            dribbles_attempted INTEGER DEFAULT 0, dribbles_success INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0, interceptions INTEGER DEFAULT 0,
            fouls_committed INTEGER DEFAULT 0, fouls_drawn INTEGER DEFAULT 0,
            yellow_cards INTEGER DEFAULT 0, red_cards INTEGER DEFAULT 0,
            rating REAL DEFAULT 0, fetched_at TEXT,
            UNIQUE(fc26_player_id, league_key)
        );
        CREATE INDEX IF NOT EXISTS idx_ss_player ON season_stats(player_name);
        CREATE INDEX IF NOT EXISTS idx_ss_club ON season_stats(club_name);
        CREATE INDEX IF NOT EXISTS idx_ss_league ON season_stats(league_key);
        CREATE INDEX IF NOT EXISTS idx_ss_rating ON season_stats(rating DESC);

        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY, league_key TEXT, team_name TEXT,
            sportapi_team_id INTEGER, position INTEGER,
            played INTEGER, wins INTEGER, draws INTEGER, losses INTEGER,
            goals_for INTEGER, goals_against INTEGER, goal_diff INTEGER,
            points INTEGER, form TEXT, fetched_at TEXT,
            UNIQUE(league_key, team_name)
        );
        CREATE INDEX IF NOT EXISTS idx_st_league ON standings(league_key, position);

        CREATE TABLE IF NOT EXISTS match_results (
            id INTEGER PRIMARY KEY, sportapi_event_id INTEGER UNIQUE,
            league_key TEXT, home_team TEXT, away_team TEXT,
            home_score INTEGER, away_score INTEGER,
            home_xg REAL DEFAULT 0, away_xg REAL DEFAULT 0,
            match_date TEXT, status TEXT, fetched_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mr_league ON match_results(league_key, match_date);
        CREATE INDEX IF NOT EXISTS idx_mr_team ON match_results(home_team);
        CREATE INDEX IF NOT EXISTS idx_mr_team2 ON match_results(away_team);

        CREATE TABLE IF NOT EXISTS fixtures (
            id INTEGER PRIMARY KEY, sportapi_event_id INTEGER UNIQUE,
            league_key TEXT, home_team TEXT, away_team TEXT,
            match_date TEXT, fetched_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_fx_league ON fixtures(league_key, match_date);
    """)
    con.commit()
    con.close()

def detect_league(club_or_key):
    lk = club_or_key.lower().strip()
    if lk in TOURNAMENTS:
        return lk
    con = get_con()
    row = con.execute(
        "SELECT league_name FROM players WHERE LOWER(club_name) LIKE ? LIMIT 1",
        (f'%{club_or_key}%',)).fetchone()
    con.close()
    return LEAGUE_TO_KEY.get(row[0], 'epl') if row else 'epl'

def find_team_id(club_name):
    for k, v in TEAM_ID_MAP.items():
        if k.lower() == club_name.lower() or k.lower() in club_name.lower():
            return v
    con = get_con()
    row = con.execute(
        "SELECT sportapi_team_id FROM standings WHERE LOWER(team_name) LIKE ? LIMIT 1",
        (f'%{club_name}%',)).fetchone()
    con.close()
    return row['sportapi_team_id'] if row else None

def find_fc26_player(name):
    con = get_con()
    rows = con.execute(
        "SELECT player_id, short_name, long_name, club_name, league_name "
        "FROM players WHERE long_name LIKE ? OR short_name LIKE ? "
        "ORDER BY overall DESC LIMIT 5",
        (f'%{name}%', f'%{name}%')).fetchall()
    con.close()
    return rows

def find_sportapi_player_id(name, club):
    """Find sportapi ID: manual map → team roster."""
    for map_name, map_id in PLAYER_ID_MAP.items():
        if name.lower() in map_name.lower() or map_name.lower() in name.lower():
            return map_id
    tid = find_team_id(club)
    if tid:
        time.sleep(REQUEST_DELAY)
        roster = api_get(f"team/{tid}/players")
        if roster and 'players' in roster:
            for rp in roster['players']:
                rp_name = rp.get('player', rp).get('name', '')
                if name.lower() in rp_name.lower() or rp_name.lower() in name.lower():
                    sid = rp.get('player', rp).get('id')
                    PLAYER_ID_MAP[name] = sid
                    return sid
    return None

def parse_player_stats(raw, fc26_id='', name='', club='', lk='epl', tid=17, sid=76986):
    if not raw or '_error' in raw or (isinstance(raw, dict) and 'error' in raw):
        return None
    if isinstance(raw, dict) and 'statistics' in raw:
        s = raw['statistics']
        if not club and 'team' in raw:
            club = raw['team'].get('name', '')
    elif isinstance(raw, dict):
        s = raw
    else:
        return None

    def sg(*keys, default=0):
        for k in keys:
            if k in s:
                return s[k]
        return default

    succ = sg('successfulDribbles', default=0)
    pct = sg('successfulDribblesPercentage', default=0)
    att = int(succ / (pct / 100)) if pct > 0 else 0

    return {
        'fc26_player_id': fc26_id or '', 'sportapi_player_id': sg('id'),
        'player_name': name or '', 'club_name': club or '',
        'league_key': lk, 'tournament_id': tid, 'season_id': sid,
        'appearances': sg('appearances'), 'minutes_played': sg('minutesPlayed'),
        'goals': sg('goals'), 'assists': sg('assists'),
        'shots_total': sg('totalShots'), 'shots_on_target': sg('shotsOnTarget'),
        'xg': sg('expectedGoals'), 'xa': sg('expectedAssists'),
        'passes_total': sg('totalPasses'), 'passes_key': sg('keyPasses'),
        'passes_accuracy': sg('accuratePassesPercentage'), 'crosses_total': sg('totalCross'),
        'dribbles_attempted': att, 'dribbles_success': succ,
        'tackles_total': sg('tackles'), 'interceptions': sg('interceptions'),
        'fouls_committed': sg('fouls'), 'fouls_drawn': sg('wasFouled'),
        'yellow_cards': sg('yellowCards'), 'red_cards': sg('redCards'),
        'rating': sg('rating'), 'fetched_at': datetime.now().isoformat(),
    }

def save_player_stats(data):
    ensure_tables()
    con = get_con()
    try:
        con.execute("""INSERT OR REPLACE INTO season_stats (
            fc26_player_id, sportapi_player_id, player_name, club_name,
            league_key, tournament_id, season_id, appearances, minutes_played,
            goals, assists, shots_total, shots_on_target, xg, xa,
            passes_total, passes_key, passes_accuracy, crosses_total,
            dribbles_attempted, dribbles_success, tackles_total, interceptions,
            fouls_committed, fouls_drawn, yellow_cards, red_cards, rating, fetched_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            data['fc26_player_id'], data['sportapi_player_id'], data['player_name'],
            data['club_name'], data['league_key'], data['tournament_id'], data['season_id'],
            data['appearances'], data['minutes_played'], data['goals'], data['assists'],
            data['shots_total'], data['shots_on_target'], data['xg'], data['xa'],
            data['passes_total'], data['passes_key'], data['passes_accuracy'],
            data['crosses_total'], data['dribbles_attempted'], data['dribbles_success'],
            data['tackles_total'], data['interceptions'], data['fouls_committed'],
            data['fouls_drawn'], data['yellow_cards'], data['red_cards'],
            data['rating'], data['fetched_at']
        ))
        con.commit()
        return True
    except Exception as e:
        print(f"  ❌ DB: {e}"); return False
    finally:
        con.close()

# ════════════════════════════════════════════════════
#  FETCH commands
# ════════════════════════════════════════════════════

def cmd_fetch_player(name, league_key=None):
    fc26_rows = find_fc26_player(name)
    if not fc26_rows:
        print(f"❌ 找不到球員: {name}"); return None
    p = fc26_rows[0]
    if not league_key:
        league_key = detect_league(p['club_name'])
    t = TOURNAMENTS.get(league_key)
    if not t:
        print(f"❌ 不支援的聯賽: {league_key}"); return None

    sp_id = find_sportapi_player_id(name, p['club_name'])
    if not sp_id:
        print(f"❌ 找不到 SportAPI ID: {p['long_name']}"); return None

    print(f"  🔄 {p['long_name']} ({p['club_name']}) — ID: {sp_id}")
    time.sleep(REQUEST_DELAY)
    raw = api_get(f"player/{sp_id}/unique-tournament/{t['tid']}/season/{t['sid']}/statistics/overall")
    if '_error' in raw:
        print(f"  ❌ {raw['_error']}"); return None

    parsed = parse_player_stats(raw, fc26_id=p['player_id'], name=p['long_name'],
                                club=p['club_name'], lk=league_key, tid=t['tid'], sid=t['sid'])
    if parsed and save_player_stats(parsed):
        print(f"  ✅ Rtg:{parsed['rating']:.2f} | {parsed['goals']}G {parsed['assists']}A | "
              f"xG:{parsed['xg']:.1f} xA:{parsed['xa']:.1f} | {parsed['appearances']}場")
        return parsed
    return None

def cmd_fetch_team(club_name, league_key=None):
    if not league_key:
        league_key = detect_league(club_name)
    t = TOURNAMENTS.get(league_key)
    if not t:
        print(f"❌ 不支援的聯賽: {league_key}"); return
    tid = find_team_id(club_name)
    if not tid:
        print(f"❌ 找不到 Team ID: {club_name}"); return

    print(f"  🔄 {club_name} 陣容 (ID: {tid})...")
    time.sleep(REQUEST_DELAY)
    roster = api_get(f"team/{tid}/players")
    if not roster or 'players' not in roster:
        print(f"  ❌ 無法獲取陣容"); return

    players = roster['players']
    print(f"  📋 {len(players)} 位球員\n")
    ok, fail = 0, 0
    for i, rp in enumerate(players):
        pl = rp.get('player', rp)
        sp_id, sp_name = pl.get('id'), pl.get('name', '')
        time.sleep(REQUEST_DELAY)
        raw = api_get(f"player/{sp_id}/unique-tournament/{t['tid']}/season/{t['sid']}/statistics/overall")
        if '_error' in raw or not raw:
            fail += 1; continue
        parsed = parse_player_stats(raw, name=sp_name, club=club_name,
                                    lk=league_key, tid=t['tid'], sid=t['sid'])
        if parsed and save_player_stats(parsed):
            ok += 1
            g, a = parsed['goals'], parsed['assists']
            print(f"  ✅ [{i+1:>2}/{len(players)}] {sp_name:<25} "
                  f"Rtg:{parsed['rating']:>5.2f}  {g}G {a}A  {parsed['appearances']}場")
        else:
            fail += 1
    print(f"\n  📊 ✅ {ok} / ❌ {fail}")

def cmd_fetch_standings(league_key):
    t = TOURNAMENTS.get(league_key)
    if not t:
        print(f"❌ 不支援的聯賽: {league_key}"); return
    print(f"  🔄 {t['name']} 積分榜...")
    time.sleep(REQUEST_DELAY)
    raw = api_get(f"unique-tournament/{t['tid']}/season/{t['sid']}/standings/total")
    if not ('_error' in raw or 'standings' not in raw):
        rows = raw['standings'][0].get('rows', [])
        if rows:
            con = get_con()
            for r in rows:
                team = r.get('team', {})
                gf, ga = r.get('scoresFor', 0), r.get('scoresAgainst', 0)
                con.execute("""INSERT OR REPLACE INTO standings
                    (league_key, team_name, sportapi_team_id, position, played,
                     wins, draws, losses, goals_for, goals_against, goal_diff,
                     points, form, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    league_key, team.get('name', ''), team.get('id', 0),
                    r.get('position', 0), r.get('matches', 0),
                    r.get('wins', 0), r.get('draws', 0), r.get('losses', 0),
                    gf, ga, gf - ga, r.get('points', 0), r.get('form', ''),
                    datetime.now().isoformat()))
            con.commit()
            con.close()
            print(f"  ✅ {len(rows)} 隊已更新")
        else:
            print("  ⚠️ API 無新數據，顯示本地快取")
    else:
        print(f"  ⚠️ API 暫時無法存取，顯示本地快取")
    cmd_show_standings(league_key)

def cmd_fetch_results(league_key, days=7):
    t = TOURNAMENTS.get(league_key)
    if not t:
        print(f"❌ 不支援的聯賽: {league_key}"); return

    today = datetime.now()
    con = get_con()
    total = 0
    print(f"  🔄 掃描近 {days} 天 {t['name']} 賽果...")

    for d in range(days):
        date = (today - timedelta(days=d)).strftime('%Y-%m-%d')
        time.sleep(REQUEST_DELAY)
        raw = api_get(f"sport/football/scheduled-events/{date}")
        if '_error' in raw or 'events' not in raw:
            continue

        for e in raw['events']:
            tourn = e.get('tournament', {})
            tid = tourn.get('uniqueTournament', {}).get('id', 0) if 'uniqueTournament' in tourn else 0
            if tid != t['tid']:
                continue

            status = e.get('status', {}).get('code', '')
            desc = e.get('status', {}).get('description', '')
            home = e.get('homeTeam', {}).get('name', '')
            away = e.get('awayTeam', {}).get('name', '')
            eid = e.get('id', 0)
            ts = e.get('startTimestamp', 0)
            mdate = datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if ts else date

            if status == 100 or desc.lower() in ('ended', 'finished'):
                hs = e.get('homeScore', {}).get('current', 0)
                as_ = e.get('awayScore', {}).get('current', 0)
                # Get xG
                xg_h, xg_a = 0, 0
                time.sleep(REQUEST_DELAY * 0.5)
                sraw = api_get(f"event/{eid}/statistics")
                if sraw and 'statistics' in sraw:
                    for per in sraw['statistics']:
                        if per.get('period') == 'ALL':
                            for grp in per.get('groups', []):
                                if grp.get('groupName') == 'Match overview':
                                    for it in grp.get('statisticsItems', []):
                                        if it.get('name') == 'Expected goals':
                                            xg_h = float(str(it.get('home', '0')))
                                            xg_a = float(str(it.get('away', '0')))
                con.execute("""INSERT OR REPLACE INTO match_results
                    (sportapi_event_id, league_key, home_team, away_team,
                     home_score, away_score, home_xg, away_xg, match_date, status, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (eid, league_key, home, away, hs, as_, xg_h, xg_a, mdate, desc,
                     datetime.now().isoformat()))
                total += 1

            elif desc.lower() in ('not_started', 'upcoming'):
                con.execute("""INSERT OR REPLACE INTO fixtures
                    (sportapi_event_id, league_key, home_team, away_team, match_date, fetched_at)
                    VALUES (?,?,?,?,?,?)""",
                    (eid, league_key, home, away, mdate, datetime.now().isoformat()))

    con.commit()
    con.close()
    print(f"  ✅ {total} 場已完賽結果已存入\n")
    cmd_show_results(league_key, days)

# ════════════════════════════════════════════════════
#  SHOW / DISPLAY commands
# ════════════════════════════════════════════════════

def cmd_show_player(name):
    ensure_tables()
    con = get_con()
    rows = con.execute(
        "SELECT * FROM season_stats WHERE player_name LIKE ? ORDER BY fetched_at DESC",
        (f'%{name}%',)).fetchall()
    con.close()
    if not rows:
        print(f"❌ 快取無此球員: {name}\n   嘗試: fetch {name}"); return
    for r in rows:
        print(f"\n{'='*60}")
        print(f"  🏆 {r['player_name']}  —  {r['club_name']} ({r['league_key'].upper()})")
        print(f"  更新: {r['fetched_at'][:19]}")
        print(f"{'='*60}")
        print(f"  Rating              {r['rating']:.2f}")
        print(f"  出場                {r['appearances']}場  ({r['minutes_played']} 分鐘)")
        print(f"\n  進攻")
        print(f"    Goals             {r['goals']}    Assists           {r['assists']}")
        print(f"    Shots             {r['shots_total']}  (on target: {r['shots_on_target']})")
        print(f"    xG                {r['xg']:.2f}   xA                {r['xa']:.2f}")
        print(f"    Key Passes        {r['passes_key']}")
        print(f"\n  傳球")
        print(f"    Total Passes      {r['passes_total']}   Accuracy          {r['passes_accuracy']:.1f}%")
        print(f"    Crosses           {r['crosses_total']}")
        print(f"\n  盤帶")
        dp = (r['dribbles_success']/r['dribbles_attempted']*100) if r['dribbles_attempted'] else 0
        print(f"    Dribbles          {r['dribbles_success']}/{r['dribbles_attempted']} ({dp:.0f}%)")
        print(f"\n  防守/紀律")
        print(f"    Tackles           {r['tackles_total']}   Interceptions     {r['interceptions']}")
        print(f"    Fouls             {r['fouls_committed']} (drawn: {r['fouls_drawn']})")
        print(f"    Cards             🟨{r['yellow_cards']} 🟥{r['red_cards']}")
        mins = r['minutes_played']
        if mins > 0:
            p90 = mins / 90
            print(f"\n  Per 90 分鐘")
            print(f"    Goals/90          {r['goals']/p90:.2f}   Assists/90        {r['assists']/p90:.2f}")
            print(f"    xG/90             {r['xg']/p90:.2f}   xA/90             {r['xa']/p90:.2f}")
            print(f"    Shots/90          {r['shots_total']/p90:.1f}   Dribbles/90       {r['dribbles_success']/p90:.1f}")

def cmd_compare_players(name1, name2):
    ensure_tables()
    con = get_con()
    def get(name):
        return con.execute("SELECT * FROM season_stats WHERE player_name LIKE ? "
                           "ORDER BY fetched_at DESC LIMIT 1", (f'%{name}%',)).fetchone()
    r1, r2 = get(name1), get(name2)
    con.close()
    if not r1 or not r2:
        print(f"❌ 快取不足 — 請先 fetch {name1 if not r1 else name2}"); return

    def p90(val, m):
        return val * 90 / m if m else 0
    m1, m2 = r1['minutes_played'], r2['minutes_played']

    print(f"\n{'='*70}")
    print(f"  {r1['player_name']}  vs  {r2['player_name']}")
    print(f"  {r1['club_name']} ({r1['league_key'].upper()})  vs  "
          f"{r2['club_name']} ({r2['league_key'].upper()})")
    print(f"{'='*70}")
    print(f"\n{'指標':<18} {'左':>20} {'':>4} {'右':>20}")
    print(f"{'─'*18} {'─'*20} {'':>4} {'─'*20}")
    print(f"{'Rating':<18} {r1['rating']:>20.2f} {'vs':>4} {r2['rating']:>20.2f}")
    print(f"{'出場':<18} {r1['appearances']:>20} {'vs':>4} {r2['appearances']:>20}")
    print(f"{'上場分鐘':<18} {m1:>20} {'vs':>4} {m2:>20}")
    print(f"{'─'*18} {'─'*20} {'':>4} {'─'*20}")
    print(f"{'Goals':<18} {r1['goals']:>20} {'vs':>4} {r2['goals']:>20}")
    print(f"{'Assists':<18} {r1['assists']:>20} {'vs':>4} {r2['assists']:>20}")
    print(f"{'G+A':<18} {r1['goals']+r1['assists']:>20} {'vs':>4} {r2['goals']+r2['assists']:>20}")
    print(f"{'xG':<18} {r1['xg']:>20.2f} {'vs':>4} {r2['xg']:>20.2f}")
    print(f"{'xA':<18} {r1['xa']:>20.2f} {'vs':>4} {r2['xa']:>20.2f}")
    print(f"\n  ── Per 90 分鐘 ──")
    print(f"{'Goals/90':<18} {p90(r1['goals'],m1):>20.2f} {'vs':>4} {p90(r2['goals'],m2):>20.2f}")
    print(f"{'Assists/90':<18} {p90(r1['assists'],m1):>20.2f} {'vs':>4} {p90(r2['assists'],m2):>20.2f}")
    print(f"{'xG/90':<18} {p90(r1['xg'],m1):>20.2f} {'vs':>4} {p90(r2['xg'],m2):>20.2f}")
    print(f"{'xA/90':<18} {p90(r1['xa'],m1):>20.2f} {'vs':>4} {p90(r2['xa'],m2):>20.2f}")
    print(f"{'─'*18} {'─'*20} {'':>4} {'─'*20}")
    print(f"{'Shots':<18} {r1['shots_total']:>20} {'vs':>4} {r2['shots_total']:>20}")
    print(f"{'Key Passes':<18} {r1['passes_key']:>20} {'vs':>4} {r2['passes_key']:>20}")
    print(f"{'Crosses':<18} {r1['crosses_total']:>20} {'vs':>4} {r2['crosses_total']:>20}")
    d1 = (r1['dribbles_success']/r1['dribbles_attempted']*100) if r1['dribbles_attempted'] else 0
    d2 = (r2['dribbles_success']/r2['dribbles_attempted']*100) if r2['dribbles_attempted'] else 0
    print(f"{'Dribbles (succ%)':<18} {r1['dribbles_success']:>4}/{r1['dribbles_attempted']:<4} ({d1:.0f}%) {'vs':>2} "
          f"{r2['dribbles_success']:>4}/{r2['dribbles_attempted']:<4} ({d2:.0f}%)")
    print(f"{'Tackles':<18} {r1['tackles_total']:>20} {'vs':>4} {r2['tackles_total']:>20}")
    print(f"{'Fouls Drawn':<18} {r1['fouls_drawn']:>20} {'vs':>4} {r2['fouls_drawn']:>20}")

def cmd_show_standings(league_key):
    ensure_tables()
    con = get_con()
    rows = con.execute(
        "SELECT * FROM standings WHERE league_key = ? ORDER BY position",
        (league_key,)).fetchall()
    con.close()
    if not rows:
        print(f"📭 無快取 — 嘗試: standings {league_key}"); return
    t = TOURNAMENTS.get(league_key, {})
    print(f"\n  {t.get('name', league_key.upper())}  —  Matchday {rows[0]['played']}")
    print(f"  {'#':>2} {'Team':<18} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>3} {'GA':>3} "
          f"{'GD':>4} {'Pts':>4}")
    print(f"  {'─'*54}")
    for r in rows:
        print(f"  {r['position']:>2} {r['team_name']:<18} {r['played']:>3} {r['wins']:>3} "
              f"{r['draws']:>3} {r['losses']:>3} {r['goals_for']:>3} {r['goals_against']:>3} "
              f"{r['goal_diff']:>+4} {r['points']:>4}")

def cmd_show_results(league_key, days=7):
    ensure_tables()
    con = get_con()
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    rows = con.execute(
        "SELECT * FROM match_results WHERE league_key = ? AND match_date >= ? "
        "ORDER BY match_date DESC", (league_key, cutoff)).fetchall()
    con.close()
    if not rows:
        print(f"📭 近 {days} 天無比賽結果快取"); return
    t = TOURNAMENTS.get(league_key, {})
    print(f"\n  {t.get('name', league_key.upper())}  —  近 {days} 天賽果\n")
    for r in rows:
        xg_str = f" (xG {r['home_xg']:.1f}-{r['away_xg']:.1f})" if r['home_xg'] or r['away_xg'] else ""
        print(f"  {r['match_date']}  {r['home_team']:<18} {r['home_score']}-{r['away_score']:<4} "
              f"{r['away_team']:<18}{xg_str}")

def cmd_show_fixtures(league_key, days=7):
    ensure_tables()
    con = get_con()
    cutoff = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    rows = con.execute(
        "SELECT * FROM fixtures WHERE league_key = ? AND match_date <= ? "
        "ORDER BY match_date ASC", (league_key, cutoff)).fetchall()
    con.close()
    if not rows:
        print(f"📭 未來 {days} 天無賽程快取"); return
    t = TOURNAMENTS.get(league_key, {})
    print(f"\n  {t.get('name', league_key.upper())}  —  未來賽程\n")
    for r in rows:
        print(f"  {r['match_date']}  {r['home_team']:<18} vs  {r['away_team']}")

def cmd_cached(league=None):
    ensure_tables()
    con = get_con()
    if league:
        rows = con.execute(
            "SELECT player_name, club_name, league_key, appearances, goals, assists, "
            "xg, xa, rating, fetched_at FROM season_stats WHERE league_key = ? "
            "ORDER BY rating DESC", (league,)).fetchall()
    else:
        rows = con.execute(
            "SELECT player_name, club_name, league_key, appearances, goals, assists, "
            "xg, xa, rating, fetched_at FROM season_stats ORDER BY rating DESC").fetchall()
    con.close()
    if not rows:
        print("📭 快取為空"); return
    print(f"\n📦 本地快取: {len(rows)} 位球員\n")
    print(f"{'Name':<22} {'Club':<16} {'LG':<6} {'APP':>4} {'G':>3} {'A':>3} "
          f"{'xG':>5} {'xA':>5} {'Rtg':>5} {'Updated':<11}")
    print('─' * 95)
    for r in rows:
        print(f"{r[0]:<22} {r[1]:<16} {r[2]:<6} {int(r[3]):>4} {int(r[4]):>3} {int(r[5]):>3} "
              f"{r[6]:>5.1f} {r[7]:>5.1f} {r[8]:>5.2f} {r[9][:10]:<11}")

def cmd_export(league=None, output=None):
    ensure_tables()
    con = get_con()
    if league:
        rows = con.execute(
            "SELECT * FROM season_stats WHERE league_key = ? ORDER BY rating DESC",
            (league,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM season_stats ORDER BY rating DESC").fetchall()
    con.close()
    if not rows:
        print("📭 無數據可匯出"); return
    cols = [k for k in rows[0].keys()]
    outpath = output or f"season_stats_{league or 'all'}_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(outpath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
    print(f"✅ 匯出 {len(rows)} 筆至 {outpath}")

def cmd_standings_all():
    for lk in TOURNAMENTS:
        print(f"\n{'═'*58}")
        cmd_show_standings(lk)

# ════════════════════════════════════════════════════
#  Main CLI
# ════════════════════════════════════════════════════

if __name__ == '__main__':
    ensure_tables()
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)

    cmd = args[0].lower()
    rest = args[1:]

    def has_flag(flag):
        return flag in rest

    def flag_val(flag, default=None):
        if flag in rest:
            idx = rest.index(flag)
            return rest[idx + 1] if idx + 1 < len(rest) else default
        return default

    if cmd == 'status':
        check_api()
    elif cmd == 'fetch':
        name = ' '.join([x for x in rest if not x.startswith('--')])
        lk = flag_val('--league')
        cmd_fetch_player(name, lk)
    elif cmd == 'fetch-team':
        name = ' '.join([x for x in rest if not x.startswith('--')])
        lk = flag_val('--league')
        cmd_fetch_team(name, lk)
    elif cmd == 'standings':
        cmd_fetch_standings(rest[0] if rest else 'epl')
    elif cmd == 'standings-all':
        cmd_standings_all()
    elif cmd == 'results':
        lk = rest[0] if rest else 'epl'
        days = int(flag_val('--days', '7') or '7')
        cmd_fetch_results(lk, days)
    elif cmd == 'fixtures':
        lk = rest[0] if rest else 'epl'
        days = int(flag_val('--days', '14') or '14')
        cmd_show_fixtures(lk, days)
    elif cmd == 'show':
        cmd_show_player(' '.join(rest))
    elif cmd == 'compare':
        if len(rest) >= 2:
            cmd_compare_players(rest[0], rest[1])
        else:
            print("Usage: compare <player1> <player2>")
    elif cmd == 'cached':
        lk = flag_val('--league')
        cmd_cached(lk)
    elif cmd == 'export':
        lk = flag_val('--league')
        out = flag_val('--output')
        cmd_export(lk, out)
    else:
        print(f"❌ 未知指令: {cmd}")
        print(__doc__)