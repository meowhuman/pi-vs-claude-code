#!/usr/bin/env python3
"""Cloudbet Odds CLI — 從 Cloudbet API 獲取足球賠率。

用法:
    python3 fetch_cloudbet_odds.py list --league epl
    python3 fetch_cloudbet_odds.py list --all
    python3 fetch_cloudbet_odds.py odds --event-id 33550037
    python3 fetch_cloudbet_odds.py report --event-id 33550037
    python3 fetch_cloudbet_odds.py compare --league epl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

CLOUDBET_BASE = 'https://sports-api.cloudbet.com'

LEAGUE_KEYS: dict[str, str] = {
    'epl': 'soccer-england-premier-league',
    'laliga': 'soccer-spain-laliga',
    'bundesliga': 'soccer-germany-bundesliga',
    'seriea': 'soccer-italy-serie-a',
    'ligue1': 'soccer-france-ligue-1',
}

ODDS_API_SPORTS: dict[str, str] = {
    'epl': 'soccer_epl',
    'laliga': 'soccer_spain_la_liga',
    'bundesliga': 'soccer_germany_bundesliga',
    'seriea': 'soccer_italy_serie_a',
    'ligue1': 'soccer_france_ligue_one',
}

LEAGUE_NAMES: dict[str, str] = {
    'epl': 'English Premier League',
    'laliga': 'La Liga',
    'bundesliga': 'Bundesliga',
    'seriea': 'Serie A',
    'ligue1': 'Ligue 1',
}

KEY_MARKETS = [
    'soccer.match_odds',
    'soccer.asian_handicap',
    'soccer.total_goals',
    'soccer.both_teams_to_score',
    'soccer.draw_no_bet',
]

FT_PERIOD = ('period=ft', 'period=1h&period=ft')


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_token() -> str:
    token = os.getenv('CLOUDBET_API_TOKEN', '')
    if not token:
        # Fallback: load from project root .env
        env_path = Path(os.getcwd()).resolve().parent.parent.parent.parent / '.env'
        for p in [env_path, Path(os.getcwd()) / '.env']:
            if p.is_file():
                for line in p.read_text().splitlines():
                    if line.startswith('CLOUDBET_API_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
                if token:
                    break
    return token


def get_odds_api_key() -> str:
    key = os.getenv('ODDS_API_KEY', '')
    if not key:
        env_path = Path(os.getcwd()).resolve().parent.parent.parent.parent / '.env'
        for p in [env_path, Path(os.getcwd()) / '.env']:
            if p.is_file():
                for line in p.read_text().splitlines():
                    if line.startswith('ODDS_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        break
                if key:
                    break
    return key


def cloudbet_get(path: str) -> dict:
    token = get_token()
    if not token:
        print('ERROR: CLOUDBET_API_TOKEN not set', file=sys.stderr)
        sys.exit(1)
    url = f'{CLOUDBET_BASE}{path}'
    req = urllib.request.Request(url, headers={'X-API-Key': token})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def fmt_time(iso: str) -> str:
    if not iso:
        return '-'
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%m-%d %H:%M')
    except (ValueError, AttributeError):
        return iso[:16].replace('T', ' ')


def margin(prices: list[float]) -> float:
    return sum(1.0 / p for p in prices if p > 0) - 1.0


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> None:
    leagues = list(LEAGUE_KEYS.keys()) if args.all else [args.league]

    for lg in leagues:
        comp_key = LEAGUE_KEYS[lg]
        print(f'\n{"="*72}')
        print(f'  {LEAGUE_NAMES[lg]} ({comp_key})')
        print(f'{"="*72}')

        try:
            data = cloudbet_get(f'/pub/v2/odds/competitions/{comp_key}')
        except Exception as e:
            print(f'  ERROR: {e}', file=sys.stderr)
            continue

        events = [
            e for e in data.get('events', [])
            if e.get('home') and e.get('away')
        ]
        events.sort(key=lambda x: x.get('cutoffTime', ''))

        print(f'  {"ID":>10s}  {"Home":<25s} {"Away":<25s} {"Time":>10s}')
        print(f'  {"-"*10}  {"-"*25} {"-"*25} {"-"*10}')

        for e in events:
            eid = e['id']
            home = e['home']['name']
            away = e['away']['name']
            start = fmt_time(e.get('cutoffTime', ''))
            print(f'  {eid:>10}  {home:<25s} {away:<25s} {start:>10s}')

        print(f'\n  Total: {len(events)} events')


def cmd_odds(args: argparse.Namespace) -> None:
    data = cloudbet_get(f'/pub/v2/odds/events/{args.event_id}')

    home_name = data.get('home', {}).get('name', 'Home')
    away_name = data.get('away', {}).get('name', 'Away')
    kickoff = fmt_time(data.get('cutoffTime', ''))
    status = data.get('status', '?')

    print(f'\n{"="*72}')
    print(f'  {home_name} vs {away_name}')
    print(f'  Status: {status} | Kickoff: {kickoff} UTC')
    print(f'{"="*72}\n')

    markets = data.get('markets', {})

    for mkey in KEY_MARKETS:
        if mkey not in markets:
            continue

        mdata = markets[mkey]
        subs = mdata.get('submarkets', {})

        for subkey, subdata in subs.items():
            is_ft = any(p in subkey for p in FT_PERIOD)
            if not is_ft:
                continue

            sels = subdata.get('selections', [])
            if not sels:
                continue

            # Filter out zero prices (suspended markets)
            active = [s for s in sels if s.get('price', 0) > 0]
            if not active:
                continue

            params_str = subkey.split('period=ft', 1)[-1].strip('& ')
            label = mkey
            if params_str:
                label = f'{mkey} ({params_str})'

            print(f'  [{label}]')
            prices = []
            for s in active:
                outcome = s.get('outcome', '?')
                price = s.get('price', '?')
                ms = s.get('maxStake', '?')
                mu = s.get('marketUrl', '')
                prices.append(float(price))
                print(f'    {outcome:<20s} @{price!s:<8s}  max:{ms!s:<8s}  {mu}')

            if prices:
                m = margin(prices)
                print(f'    {"":20s}  margin: {m:.1%}')
            print()


def cmd_report(args: argparse.Namespace) -> None:
    data = cloudbet_get(f'/pub/v2/odds/events/{args.event_id}')

    home_name = data.get('home', {}).get('name', 'Home')
    away_name = data.get('away', {}).get('name', 'Away')
    kickoff = fmt_time(data.get('cutoffTime', ''))
    status = data.get('status', '?')

    markets = data.get('markets', {})

    def get_ft_sels(mkey: str) -> dict[str, str]:
        m = markets.get(mkey, {})
        for sk, sv in m.get('submarkets', {}).items():
            if 'period=ft' in sk:
                return {
                    s['outcome']: s['price']
                    for s in sv.get('selections', [])
                    if s.get('price', 0) > 0
                }
        return {}

    mo = get_ft_sels('soccer.match_odds')
    ah = get_ft_sels('soccer.asian_handicap')
    tg = get_ft_sels('soccer.total_goals')
    btts = get_ft_sels('soccer.both_teams_to_score')
    dnb = get_ft_sels('soccer.draw_no_bet')

    # Match odds margin
    mo_prices = [float(v) for v in mo.values()]
    mo_margin = margin(mo_prices) if mo_prices else 0

    print(f'\n【Cloudbet 賠率報告】{home_name} vs {away_name}')
    print(f'開賽：{kickoff} UTC | 狀態：{status}')
    print()

    print(f'全場勝負 (1X2):  主勝 {mo.get("home", "?")}  平局 {mo.get("draw", "?")}  客勝 {mo.get("away", "?")}  margin {mo_margin:.1%}')

    if ah:
        ah_prices = [float(v) for v in ah.values()]
        ah_margin = margin(ah_prices)
        print(f'讓球 (AH):      {ah_margin:.1%} margin')
        for outcome, price in ah.items():
            print(f'  {outcome}: {price}')

    print(f'大小球 (2.5):    大球 {tg.get("over", "?")}  小球 {tg.get("under", "?")}')
    print(f'兩隊進球 (BTTS): 是  {btts.get("yes", "?")}  否  {btts.get("no", "?")}')

    if dnb:
        print(f'平手注返 (DNB): 主隊 {dnb.get("home", "?")}  客隊 {dnb.get("away", "?")}')

    # Compare with fair odds (1/margin normalized)
    if mo_prices and mo_margin < 1:
        fair = [1.0 / ((1.0 / p) / (1 + mo_margin)) for p in mo_prices]
        print(f'\n公平賠率（去 margin）: 主勝 {fair[0]:.2f}  平局 {fair[1]:.2f}  客勝 {fair[2]:.2f}')


def cmd_compare(args: argparse.Namespace) -> None:
    league = args.league
    cb_key = LEAGUE_KEYS[league]
    odds_key = ODDS_API_SPORTS[league]
    odds_api_key = get_odds_api_key()

    # 1) Fetch Cloudbet events
    cb_data = cloudbet_get(f'/pub/v2/odds/competitions/{cb_key}')
    cb_events: dict[str, dict] = {}
    for e in cb_data.get('events', []):
        if not (e.get('home') and e.get('away')):
            continue
        home = e['home']['name']
        away = e['away']['name']
        cb_events[f'{home} vs {away}'] = {
            'id': e['id'],
            'home': home,
            'away': away,
            'kickoff': fmt_time(e.get('cutoffTime', '')),
        }

    # 2) Fetch The Odds API
    odds_results: dict[str, dict] = {}
    if odds_api_key:
        try:
            url = (
                f'https://api.the-odds-api.com/v4/sports/{odds_key}/odds/'
                f'?apiKey={odds_api_key}&regions=uk,eu&markets=h2h,totals'
                f'&oddsFormat=decimal'
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as r:
                odds_data = json.loads(r.read())
                remaining = r.headers.get('x-requests-remaining', '?')
                used = r.headers.get('x-requests-used', '?')
                print(f'(The Odds API: {used} used, {remaining} remaining)\n')

                for ev in odds_data:
                    match_key = f"{ev['home_team']} vs {ev['away_team']}"
                    best_h2h: dict[str, tuple[str, float]] = {}
                    for book in ev.get('bookmakers', []):
                        for m in book.get('markets', []):
                            if m['key'] == 'h2h':
                                for sel in m.get('outcomes', []):
                                    name = sel['name']
                                    price = float(sel['price'])
                                    if name not in best_h2h or price > best_h2h[name][1]:
                                        best_h2h[name] = (book['title'], price)
                    odds_results[match_key] = best_h2h
        except Exception as e:
            print(f'(The Odds API error: {e})\n')
    else:
        print('(ODDS_API_KEY not set, Cloudbet only)\n')

    # 3) Fetch Cloudbet odds for each event
    print(f'{"="*90}')
    print(f'  {LEAGUE_NAMES[league]} — Cloudbet vs The Odds API')
    print(f'{"="*90}\n')

    all_matches = sorted(set(list(cb_events.keys()) + list(odds_results.keys())))

    for match_key in all_matches:
        parts = match_key.split(' vs ')
        home = parts[0] if len(parts) > 0 else '?'
        away = parts[1] if len(parts) > 1 else '?'

        cb_info = cb_events.get(match_key)
        cb_odds: dict[str, str] = {}
        if cb_info:
            try:
                ev = cloudbet_get(f'/pub/v2/odds/events/{cb_info["id"]}')
                markets = ev.get('markets', {})
                mo = markets.get('soccer.match_odds', {})
                for sk, sv in mo.get('submarkets', {}).items():
                    if 'period=ft' in sk:
                        cb_odds = {
                            s['outcome']: s['price']
                            for s in sv.get('selections', [])
                            if s.get('price', 0) > 0
                        }
                        break
            except Exception:
                pass

        best_odds = odds_results.get(match_key, {})

        # Build comparison table
        has_data = cb_odds or best_odds
        if not has_data:
            continue

        kickoff_str = cb_info['kickoff'] if cb_info else '?'
        print(f'{home} vs {away}  ({kickoff_str})')

        outcomes = []
        if cb_odds:
            outcomes = list(cb_odds.keys())
        if best_odds:
            for name in best_odds:
                if name not in outcomes:
                    outcomes.append(name)

        print(f'  {"Outcome":<15s} {"Cloudbet":>10s} {"Best (Odds API)":>18s}')
        print(f'  {"-"*15} {"-"*10} {"-"*18}')

        cb_prices = []
        best_prices = []
        for name in outcomes:
            cb_p = cb_odds.get(name, '-')
            best_info = best_odds.get(name)
            best_p = f'{best_info[1]:.2f} @{best_info[0]}' if best_info else '-'
            if isinstance(cb_p, str) and cb_p != '-':
                cb_prices.append(float(cb_p))
            if best_info:
                best_prices.append(best_info[1])
            print(f'  {name:<15s} {str(cb_p):>10s} {str(best_p):>18s}')

        # Margin comparison
        if cb_prices:
            cb_m = margin(cb_prices)
            print(f'  {"":15s} {"margin: ":>10s}{cb_m:.1%}', end='')
            if best_prices and len(best_prices) >= 2:
                bm = margin(best_prices)
                print(f'  {"margin: ":>10s}{bm:.1%}', end='')
            print()
        print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Cloudbet Odds CLI',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # list
    p_list = sub.add_parser('list', help='列出可投注賽事')
    lg_group = p_list.add_mutually_exclusive_group(required=True)
    lg_group.add_argument('--league', choices=list(LEAGUE_KEYS.keys()), help='指定聯賽')
    lg_group.add_argument('--all', action='store_true', help='所有五大聯賽')

    # odds
    p_odds = sub.add_parser('odds', help='查詢單場完整賠率')
    p_odds.add_argument('--event-id', required=True, help='Cloudbet Event ID')

    # report
    p_report = sub.add_parser('report', help='快速賠率報告')
    p_report.add_argument('--event-id', required=True, help='Cloudbet Event ID')

    # compare
    p_compare = sub.add_parser('compare', help='Cloudbet vs The Odds API 比較')
    p_compare.add_argument('--league', required=True, choices=list(LEAGUE_KEYS.keys()))

    args = parser.parse_args()

    cmds = {
        'list': cmd_list,
        'odds': cmd_odds,
        'report': cmd_report,
        'compare': cmd_compare,
    }
    cmds[args.command](args)


if __name__ == '__main__':
    main()
