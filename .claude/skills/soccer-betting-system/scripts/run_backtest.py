#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtest.walk_forward import run_walk_forward_backtest
from src.models.poisson import backtest_alignment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--league', required=True)
    parser.add_argument('--mode', choices=['alignment', 'walk-forward'], default='walk-forward')
    parser.add_argument('--season', default='2024-25')
    parser.add_argument('--train-matches', type=int, default=80)
    parser.add_argument('--edge-threshold', type=float, default=0.03)
    parser.add_argument('--stake-fraction', type=float, default=0.03)
    parser.add_argument('--bankroll', type=float, default=1000.0)
    args = parser.parse_args()

    if args.mode == 'alignment':
        result = backtest_alignment(args.league)
        if result['total'] == 0:
            print('status=error')
            print('reason=no standings data available for requested league')
            raise SystemExit(1)
        print('mode=alignment')
        print(f'league={args.league}')
        print(f'alignment={result["alignment"]:.2f}%')
        print(f'bps_correct={result["bps_correct"]}')
        print(f'total={result["total"]}')
        return

    summary = run_walk_forward_backtest(
        league=args.league,
        season=args.season,
        initial_bankroll=args.bankroll,
        train_matches=args.train_matches,
        edge_threshold=args.edge_threshold,
        stake_fraction=args.stake_fraction,
    )
    print('mode=walk-forward')
    print(f'league={summary.league}')
    print(f'season={summary.season}')
    print(f'matches_seen={summary.matches_seen}')
    print(f'bets={summary.bets}')
    print(f'wins={summary.wins}')
    print(f'losses={summary.losses}')
    print(f'bankroll_start={summary.bankroll_start:.2f}')
    print(f'bankroll_end={summary.bankroll_end:.2f}')
    print(f'roi_pct={summary.roi_pct:.2f}')
    print(f'yield_pct={summary.yield_pct:.2f}')
    print(f'avg_edge_pct={summary.avg_edge_pct:.2f}')


if __name__ == '__main__':
    main()
