#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.poisson import get_team_ratings, implied_odds, predict_match


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--league', required=True)
    parser.add_argument('--home', required=True)
    parser.add_argument('--away', required=True)
    args = parser.parse_args()

    ratings = get_team_ratings(args.league)
    pred = predict_match(args.home, args.away, ratings)

    if not pred:
        print('status=error')
        print('reason=missing team ratings or standings data')
        print(f'league={args.league}')
        print(f'home={args.home}')
        print(f'away={args.away}')
        raise SystemExit(1)

    print('soccer-betting-system prediction entrypoint')
    print(f'league={args.league}')
    print(f'match={args.home} vs {args.away}')
    print(f'home_prob={pred["home_prob"]:.3f} fair_odds={implied_odds(pred["home_prob"]):.2f}')
    print(f'draw_prob={pred["draw_prob"]:.3f} fair_odds={implied_odds(pred["draw_prob"]):.2f}')
    print(f'away_prob={pred["away_prob"]:.3f} fair_odds={implied_odds(pred["away_prob"]):.2f}')
    print(f'over_2_5_prob={pred["over_prob"]:.3f}')
    print(f'under_2_5_prob={pred["under_prob"]:.3f}')
    print(f'expected_score={pred["expected_score"]}')
    print('top_scores=')
    for score, prob in pred['top_scores']:
        print(f'  - {score}: {prob:.3%}')


if __name__ == '__main__':
    main()
