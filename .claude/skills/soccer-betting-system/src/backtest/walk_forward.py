from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..db import connect
from ..models.poisson import match_probabilities


@dataclass
class BacktestSummary:
    league: str
    season: str
    matches_seen: int
    bets: int
    wins: int
    losses: int
    bankroll_start: float
    bankroll_end: float
    roi_pct: float
    yield_pct: float
    avg_edge_pct: float


def _poisson_p(lam: float, k: int) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _market_probs(home_odds: float, draw_odds: float, away_odds: float) -> tuple[float, float, float] | None:
    if min(home_odds, draw_odds, away_odds) <= 1.01:
        return None
    raw = [(1 / home_odds), (1 / draw_odds), (1 / away_odds)]
    total = sum(raw)
    if total <= 0:
        return None
    return raw[0] / total, raw[1] / total, raw[2] / total


def _ensure_ordered_matches(con: Any, league: str, season: str) -> list[Any]:
    return con.execute(
        """
        SELECT date, home_team, away_team, ft_hg, ft_ag, ft_result, b365_h, b365_d, b365_a
        FROM historical_matches
        WHERE league_key = ?
          AND season = ?
          AND home_team IS NOT NULL
          AND away_team IS NOT NULL
          AND ft_result IN ('H', 'D', 'A')
          AND b365_h IS NOT NULL
          AND b365_d IS NOT NULL
          AND b365_a IS NOT NULL
        ORDER BY substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2), rowid
        """,
        (league, season),
    ).fetchall()


def run_walk_forward_backtest(
    league: str,
    season: str = '2024-25',
    initial_bankroll: float = 1000.0,
    train_matches: int = 80,
    edge_threshold: float = 0.03,
    stake_fraction: float = 0.03,
    home_adv: float = 1.15,
) -> BacktestSummary:
    con = connect()
    rows = _ensure_ordered_matches(con, league, season)
    con.close()

    team_stats: dict[str, dict[str, float]] = {}
    bankroll = initial_bankroll
    bets = wins = losses = 0
    total_edge = 0.0

    for idx, row in enumerate(rows):
        home = row['home_team']
        away = row['away_team']
        hg = row['ft_hg']
        ag = row['ft_ag']
        result = row['ft_result']
        home_odds = float(row['b365_h'])
        draw_odds = float(row['b365_d'])
        away_odds = float(row['b365_a'])

        if idx >= train_matches:
            if home in team_stats and away in team_stats:
                home_played = team_stats[home]['played']
                away_played = team_stats[away]['played']
                if home_played > 0 and away_played > 0:
                    total_played = sum(v['played'] for v in team_stats.values())
                    total_gf = sum(v['gf'] for v in team_stats.values())
                    total_ga = sum(v['ga'] for v in team_stats.values())
                    if total_played > 0 and total_gf > 0 and total_ga > 0:
                        avg_gpg = total_gf / total_played
                        avg_gpa = total_ga / total_played

                        home_attack = (team_stats[home]['gf'] / home_played) / avg_gpg
                        home_defense = (team_stats[home]['ga'] / home_played) / avg_gpa
                        away_attack = (team_stats[away]['gf'] / away_played) / avg_gpg
                        away_defense = (team_stats[away]['ga'] / away_played) / avg_gpa

                        lam_h = avg_gpg * home_attack * away_defense * home_adv
                        lam_a = avg_gpg * away_attack * home_defense
                        model_h, model_d, model_a, _ = match_probabilities(lam_h, lam_a)
                        market = _market_probs(home_odds, draw_odds, away_odds)

                        if market:
                            candidates = [
                                ('H', model_h - market[0], model_h, home_odds),
                                ('D', model_d - market[1], model_d, draw_odds),
                                ('A', model_a - market[2], model_a, away_odds),
                            ]
                            candidates.sort(key=lambda item: item[1], reverse=True)
                            side, edge, _, odds = candidates[0]
                            if edge >= edge_threshold:
                                stake = max(10.0, bankroll * stake_fraction)
                                won = side == result
                                bankroll += stake * (odds - 1) if won else -stake
                                bets += 1
                                wins += 1 if won else 0
                                losses += 0 if won else 1
                                total_edge += edge

        for team, gf, ga in ((home, hg, ag), (away, ag, hg)):
            if team not in team_stats:
                team_stats[team] = {'gf': 0.0, 'ga': 0.0, 'played': 0.0}
            team_stats[team]['gf'] += gf
            team_stats[team]['ga'] += ga
            team_stats[team]['played'] += 1

    roi_pct = ((bankroll - initial_bankroll) / initial_bankroll * 100) if initial_bankroll else 0.0
    total_staked = bets * max(10.0, initial_bankroll * stake_fraction) if bets else 0.0
    yield_pct = ((bankroll - initial_bankroll) / total_staked * 100) if total_staked else 0.0
    avg_edge_pct = (total_edge / bets * 100) if bets else 0.0

    return BacktestSummary(
        league=league,
        season=season,
        matches_seen=len(rows),
        bets=bets,
        wins=wins,
        losses=losses,
        bankroll_start=initial_bankroll,
        bankroll_end=bankroll,
        roi_pct=roi_pct,
        yield_pct=yield_pct,
        avg_edge_pct=avg_edge_pct,
    )
