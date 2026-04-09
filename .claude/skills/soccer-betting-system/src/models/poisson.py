from __future__ import annotations

import math
from typing import Any

from ..db import connect

ODDS_SPORTS = {
    'epl': 'soccer_epl',
    'laliga': 'soccer_spain_la_liga',
    'seriea': 'soccer_italy_serie_a',
    'bundesliga': 'soccer_germany_bundesliga',
    'ligue1': 'soccer_france_ligue_one',
}


def poisson_prob(lam: float, k: int) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def poisson_matrix(lambda_home: float, lambda_away: float, max_goals: int = 6) -> dict[tuple[int, int], float]:
    matrix: dict[tuple[int, int], float] = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[(i, j)] = poisson_prob(lambda_home, i) * poisson_prob(lambda_away, j)
    return matrix


def match_probabilities(lambda_home: float, lambda_away: float, max_goals: int = 6) -> tuple[float, float, float, dict[tuple[int, int], float]]:
    matrix = poisson_matrix(lambda_home, lambda_away, max_goals)
    home_win = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i > j)
    draw = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i == j)
    away_win = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i < j)
    return home_win, draw, away_win, matrix


def over_under_prob(lambda_home: float, lambda_away: float, line: float = 2.5, max_goals: int = 6) -> tuple[float, float]:
    matrix = poisson_matrix(lambda_home, lambda_away, max_goals)
    over = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i + j > line)
    under = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i + j < line)
    on_line = sum(matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1) if i + j == line)
    return over + on_line * 0.5, under + on_line * 0.5


def expected_score(matrix: dict[tuple[int, int], float], max_goals: int = 6) -> tuple[float, float]:
    e_home = sum(i * matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1))
    e_away = sum(j * matrix[(i, j)] for i in range(max_goals + 1) for j in range(max_goals + 1))
    return e_home, e_away


def most_likely_scores(matrix: dict[tuple[int, int], float], n: int = 5, max_goals: int = 6) -> list[tuple[tuple[int, int], float]]:
    scores = sorted(matrix.items(), key=lambda x: -x[1])
    return [(s, p) for s, p in scores[:n] if s[0] <= max_goals and s[1] <= max_goals]


def implied_odds(prob: float) -> float:
    return 1.0 / prob if prob > 0 else 999.0


def get_team_ratings(league_key: str = 'epl') -> dict[str, dict[str, Any]]:
    con = connect()
    try:
        rows = con.execute(
            'SELECT team_name, played, goals_for, goals_against, points, position '
            'FROM standings WHERE league_key = ? AND played > 0',
            (league_key,),
        ).fetchall()
    except Exception:
        con.close()
        return {}
    con.close()

    if not rows:
        return {}

    total_gf = sum(r['goals_for'] for r in rows)
    total_ga = sum(r['goals_against'] for r in rows)
    total_played = sum(r['played'] for r in rows)
    avg_gpg = total_gf / total_played if total_played else 0
    avg_gpa = total_ga / total_played if total_played else 0

    ratings: dict[str, dict[str, Any]] = {}
    for r in rows:
        gpg = r['goals_for'] / r['played']
        gpa = r['goals_against'] / r['played']
        attack = gpg / avg_gpg if avg_gpg > 0 else 1.0
        defense = gpa / avg_gpa if avg_gpa > 0 else 1.0
        ratings[r['team_name']] = {
            'position': r['position'],
            'played': r['played'],
            'gf': r['goals_for'],
            'ga': r['goals_against'],
            'gpg': round(gpg, 2),
            'gpa': round(gpa, 2),
            'attack': round(attack, 3),
            'defense': round(defense, 3),
            'points': r['points'],
        }
    return ratings


def predict_match(home: str, away: str, ratings: dict[str, dict[str, Any]], home_adv: float = 1.15, league_avg: float = 1.35) -> dict[str, Any] | None:
    hr = ratings.get(home)
    ar = ratings.get(away)
    if not hr or not ar:
        return None

    lambda_home = league_avg * hr['attack'] * ar['defense'] * home_adv
    lambda_away = league_avg * ar['attack'] * hr['defense']

    h_prob, d_prob, a_prob, matrix = match_probabilities(lambda_home, lambda_away)
    over_prob, under_prob = over_under_prob(lambda_home, lambda_away, 2.5)
    e_home, e_away = expected_score(matrix)
    top_scores = most_likely_scores(matrix)

    return {
        'home': home,
        'away': away,
        'lambda_home': round(lambda_home, 2),
        'lambda_away': round(lambda_away, 2),
        'home_prob': round(h_prob, 3),
        'draw_prob': round(d_prob, 3),
        'away_prob': round(a_prob, 3),
        'over_prob': round(over_prob, 3),
        'under_prob': round(under_prob, 3),
        'expected_home_goals': round(e_home, 2),
        'expected_away_goals': round(e_away, 2),
        'expected_score': f'{e_home:.1f} - {e_away:.1f}',
        'top_scores': [(f'{h}-{a}', p) for (h, a), p in top_scores[:5]],
    }


def backtest_alignment(league_key: str = 'epl', home_adv: float = 1.15) -> dict[str, float | int]:
    ratings = get_team_ratings(league_key)
    if not ratings:
        return {'alignment': 0.0, 'bps_correct': 0, 'total': 0}

    teams = list(ratings.keys())
    total = 0
    bps_correct = 0

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            home = teams[i]
            away = teams[j]
            pred = predict_match(home, away, ratings, home_adv)
            if not pred:
                continue
            hr = ratings[home]
            ar = ratings[away]
            stronger_home = hr['position'] < ar['position']
            model_home_wins = pred['home_prob'] > pred['away_prob']
            model_favors_stronger = (stronger_home and model_home_wins) or (not stronger_home and not model_home_wins)
            if model_favors_stronger:
                bps_correct += 1
            total += 1

    alignment = bps_correct / total * 100 if total else 0.0
    return {'alignment': alignment, 'bps_correct': bps_correct, 'total': total}
