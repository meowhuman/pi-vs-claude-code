#!/usr/bin/env python3
"""
Strategy Scanner — scan multiple strategies × symbols, rank by Sharpe

Usage:
    uv run python scripts/strategy_scanner.py --symbols SPY,QQQ,AAPL
    uv run python scripts/strategy_scanner.py --symbols BTC,ETH --crypto
    uv run python scripts/strategy_scanner.py --symbols SPY,AAPL --strategies sma_crossover,macd
    uv run python scripts/strategy_scanner.py --symbols SPY,QQQ,AAPL --top 5
    uv run python scripts/strategy_scanner.py --symbols SPY,TSLA --export results.csv
"""

import sys
import os
import argparse
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from data import fetch_data
from strategies import STRATEGIES
from engine import run_backtest, BacktestResult


def scan(symbols: list[str], strategy_names: list[str], days: int = 365,
         capital: float = 100_000, commission: float = 0.001,
         crypto: bool = False, forex: bool = False, timeframe: str = '1d') -> list[BacktestResult]:

    results = []
    total = len(symbols) * len(strategy_names)
    done = 0

    for sym in symbols:
        try:
            src = 'CCXT' if crypto else ('Tiingo FX' if forex else 'Tiingo')
            print(f'  📡 [{src}] Fetching {sym}...', end=' ', flush=True)
            df_raw = fetch_data(sym, crypto=crypto, forex=forex, period_days=days, timeframe=timeframe)
            print(f'{len(df_raw)} rows')
        except Exception as e:
            print(f'❌ {e}')
            done += len(strategy_names)
            continue

        for strat in strategy_names:
            done += 1
            try:
                df = STRATEGIES[strat](df_raw.copy())
                r = run_backtest(df, symbol=sym, strategy=strat,
                                 capital=capital, commission=commission)
                results.append(r)
                status = '✅' if r.sharpe_ratio >= 1 else ('🟡' if r.sharpe_ratio >= 0.5 else '❌')
                print(f'  {status} {sym:<8} {strat:<20} '
                      f'ret={r.total_return:+.1f}%  sharpe={r.sharpe_ratio:.2f}  '
                      f'dd={r.max_drawdown:.1f}%  alpha={r.alpha:+.1f}%')
            except Exception as e:
                print(f'  ⚠️  {sym} / {strat}: {e}')

    return results


def main():
    parser = argparse.ArgumentParser(description='Strategy Scanner')
    parser.add_argument('--symbols', type=str, default='SPY,QQQ,AAPL',
                        help='Comma-separated symbols (default: SPY,QQQ,AAPL)')
    parser.add_argument('--strategies', type=str, default='all',
                        help='Comma-separated strategies or "all" (default: all)')
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--capital', type=float, default=100_000)
    parser.add_argument('--commission', type=float, default=0.001)
    parser.add_argument('--crypto', action='store_true', help='Use CCXT for all symbols')
    parser.add_argument('--forex', action='store_true', help='Use Tiingo FX for forex pairs')
    parser.add_argument('--timeframe', type=str, default='1d')
    parser.add_argument('--top', type=int, default=0, help='Show top N by Sharpe')
    parser.add_argument('--export', type=str, help='Export results to CSV')
    parser.add_argument('--min-trades', type=int, default=0,
                        help='Minimum number of trades to include a result (default: 0 = no filter)')
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(',') if s.strip()]
    if args.strategies == 'all':
        strategy_names = list(STRATEGIES.keys())
    else:
        strategy_names = [s.strip() for s in args.strategies.split(',') if s.strip()]

    unknown = [s for s in strategy_names if s not in STRATEGIES]
    if unknown:
        print(f'❌ Unknown strategies: {", ".join(unknown)}')
        print(f'   Available: {", ".join(STRATEGIES.keys())}')
        sys.exit(1)

    print(f'\n🔍 Scanning {len(symbols)} symbols × {len(strategy_names)} strategies...')
    print(f'   Symbols:    {", ".join(symbols)}')
    print(f'   Strategies: {", ".join(strategy_names)}')
    print(f'   Period:     {args.days}d\n')

    results = scan(symbols, strategy_names, days=args.days, capital=args.capital,
                   commission=args.commission, crypto=args.crypto, forex=args.forex,
                   timeframe=args.timeframe)

    if not results:
        print('No results.')
        return

    # Apply --min-trades filter
    if args.min_trades > 0:
        before = len(results)
        results = [r for r in results if r.total_trades >= args.min_trades]
        filtered = before - len(results)
        if filtered:
            print(f'  (Filtered {filtered} results with < {args.min_trades} trades)')

    if not results:
        print(f'No results after min-trades filter (≥ {args.min_trades}).')
        return

    # Sort by Sharpe
    results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
    top = results[:args.top] if args.top > 0 else results

    print(f'\n{"═" * 90}')
    print(f'  Scan Results — Top by Sharpe Ratio')
    print(f'{"═" * 90}')
    print(f'  {"Symbol":<8} {"Strategy":<22} {"Return":>8} {"Sharpe":>7} {"MaxDD":>8} {"Alpha":>8} {"WinRate":>8} {"Trades":>7}')
    print(f'{"─" * 90}')
    for r in top:
        flag = '✅' if r.sharpe_ratio >= 1 else ('🟡' if r.sharpe_ratio >= 0.5 else '❌')
        print(f'  {flag}{r.symbol:<7} {r.strategy:<22} '
              f'{r.total_return:>+7.1f}% {r.sharpe_ratio:>7.2f} '
              f'{r.max_drawdown:>7.1f}% {r.alpha:>+7.1f}% {r.win_rate:>7.1f}% {r.total_trades:>7}')
    print(f'{"═" * 90}')
    alpha_pos = sum(1 for r in results if r.alpha > 0)
    print(f'  Total scanned: {len(results)}  |  Pass (Sharpe≥1): {sum(1 for r in results if r.sharpe_ratio >= 1)}  |  Alpha>0: {alpha_pos}')

    if args.export:
        rows = [{
            'symbol': r.symbol, 'strategy': r.strategy, 'period': r.period,
            'total_return': r.total_return, 'annualized_return': r.annualized_return,
            'sharpe_ratio': r.sharpe_ratio, 'max_drawdown': r.max_drawdown,
            'win_rate': r.win_rate, 'total_trades': r.total_trades,
            'profit_factor': r.profit_factor, 'calmar_ratio': r.calmar_ratio,
            'bh_total_return': r.bh_total_return, 'bh_sharpe': r.bh_sharpe,
            'alpha': r.alpha,
        } for r in results]
        pd.DataFrame(rows).to_csv(args.export, index=False)
        print(f'\n  📁 Exported to {args.export}')


if __name__ == '__main__':
    main()
