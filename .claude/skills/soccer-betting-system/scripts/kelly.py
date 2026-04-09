#!/usr/bin/env python3
from __future__ import annotations

import argparse


def kelly_fraction(prob: float, odds: float, fraction: float) -> float:
    q = 1 - prob
    b = odds - 1
    if b <= 0:
        return 0.0
    raw = (prob * b - q) / b
    return max(0.0, raw * fraction)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--prob', type=float, required=True)
    parser.add_argument('--odds', type=float, required=True)
    parser.add_argument('--bankroll', type=float, required=True)
    parser.add_argument('--fraction', type=float, default=0.25)
    args = parser.parse_args()

    stake_fraction = kelly_fraction(args.prob, args.odds, args.fraction)
    stake = args.bankroll * stake_fraction

    print(f'prob={args.prob:.3f}')
    print(f'odds={args.odds:.2f}')
    print(f'kelly_fraction={stake_fraction:.4f}')
    print(f'recommended_stake={stake:.2f}')


if __name__ == '__main__':
    main()
