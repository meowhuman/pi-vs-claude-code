#!/usr/bin/env python3
"""
Parameter Optimizer — grid search for best strategy parameters

Usage:
    uv run python scripts/optimize_params.py --symbol AAPL --strategy sma_crossover
    uv run python scripts/optimize_params.py --symbol BTC --strategy rsi --crypto
    uv run python scripts/optimize_params.py --symbol SPY --strategy bollinger_bands --metric max_drawdown

    # Filter by minimum trades
    uv run python scripts/optimize_params.py --symbol AAPL --strategy rsi --min-trades 10

    # Show heatmap (2D param visualization)
    uv run python scripts/optimize_params.py --symbol SPY --strategy bollinger_bands --heatmap
    uv run python scripts/optimize_params.py --symbol AAPL --strategy rsi --heatmap --heatmap-x rsi_period --heatmap-y rsi_lower
    uv run python scripts/optimize_params.py --symbol SPY --strategy sma_crossover --heatmap --save-heatmap heatmap.png
"""

import sys
import os
import argparse
import itertools
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from data import fetch_data
from strategies import STRATEGIES
from engine import run_backtest, BacktestResult

# Parameter grids per strategy
PARAM_GRIDS: dict[str, dict[str, list]] = {
    'sma_crossover': {
        'short_ma': [5, 10, 15, 20],
        'long_ma':  [20, 30, 50, 60],
    },
    'ema_crossover': {
        'short_ema': [5, 9, 12],
        'long_ema':  [21, 26, 50],
    },
    'rsi': {
        'rsi_period': [10, 14, 21],
        'rsi_lower':  [20, 25, 30],
        'rsi_upper':  [65, 70, 75, 80],
    },
    'bollinger_bands': {
        'bb_period': [15, 20, 25],
        'bb_std':    [1.5, 2.0, 2.5],
    },
    'macd': {
        'fast':          [8, 12, 16],
        'slow':          [21, 26, 30],
        'signal_period': [7, 9, 12],
    },
    'momentum': {
        'lookback':  [10, 20, 30],
        'threshold': [0.01, 0.02, 0.03, 0.05],
    },
}

# Default heatmap axis pairs per strategy (param_x, param_y)
DEFAULT_HEATMAP_AXES: dict[str, tuple[str, str]] = {
    'sma_crossover':   ('short_ma', 'long_ma'),
    'ema_crossover':   ('short_ema', 'long_ema'),
    'rsi':             ('rsi_period', 'rsi_lower'),
    'bollinger_bands': ('bb_period', 'bb_std'),
    'macd':            ('fast', 'slow'),
    'momentum':        ('lookback', 'threshold'),
}

METRIC_MAP = {
    'sharpe':       'sharpe_ratio',
    'sharpe_ratio': 'sharpe_ratio',
    'return':       'total_return',
    'total_return': 'total_return',
    'calmar':       'calmar_ratio',
    'calmar_ratio': 'calmar_ratio',
    'max_drawdown': 'max_drawdown',  # minimize — handled below
    'win_rate':     'win_rate',
}

MINIMIZE = {'max_drawdown'}


def grid_search(df_raw, symbol: str, strategy: str, metric: str,
                capital: float, commission: float,
                min_trades: int = 0) -> list[dict]:
    grid = PARAM_GRIDS.get(strategy, {})
    if not grid:
        print(f'⚠️  No param grid defined for {strategy}')
        return []

    keys = list(grid.keys())
    values = list(grid.values())
    combos = list(itertools.product(*values))
    print(f'   Grid: {len(combos)} combinations for {strategy}\n')

    results = []
    for combo in combos:
        params = dict(zip(keys, combo))
        # skip invalid combinations (e.g. short >= long)
        if 'short_ma' in params and 'long_ma' in params and params['short_ma'] >= params['long_ma']:
            continue
        if 'short_ema' in params and 'long_ema' in params and params['short_ema'] >= params['long_ema']:
            continue
        if 'fast' in params and 'slow' in params and params['fast'] >= params['slow']:
            continue
        if 'rsi_lower' in params and 'rsi_upper' in params and params['rsi_lower'] >= params['rsi_upper']:
            continue

        try:
            df = STRATEGIES[strategy](df_raw.copy(), **params)
            r = run_backtest(df, symbol=symbol, strategy=strategy,
                             capital=capital, commission=commission)
            if min_trades > 0 and r.total_trades < min_trades:
                continue
            metric_val = getattr(r, metric)
            results.append({'params': params, 'result': r, 'metric_val': metric_val})
        except Exception:
            pass

    reverse = metric not in MINIMIZE
    results.sort(key=lambda x: x['metric_val'], reverse=reverse)
    return results


def main():
    parser = argparse.ArgumentParser(description='Strategy Parameter Optimizer')
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--strategy', '-t', type=str, default='sma_crossover')
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--capital', type=float, default=100_000)
    parser.add_argument('--commission', type=float, default=0.001)
    parser.add_argument('--crypto', action='store_true')
    parser.add_argument('--forex', action='store_true')
    parser.add_argument('--timeframe', type=str, default='1d')
    parser.add_argument('--metric', type=str, default='sharpe',
                        help='Optimization metric: sharpe, return, calmar, max_drawdown, win_rate')
    parser.add_argument('--top', type=int, default=10, help='Show top N results')
    parser.add_argument('--min-trades', type=int, default=0,
                        help='Minimum number of trades to include a result (default: 0 = no filter)')

    # Heatmap options
    parser.add_argument('--heatmap', action='store_true',
                        help='Show 2D parameter heatmap after optimization')
    parser.add_argument('--heatmap-x', type=str, default=None,
                        help='X-axis parameter name for heatmap (auto-detected if omitted)')
    parser.add_argument('--heatmap-y', type=str, default=None,
                        help='Y-axis parameter name for heatmap (auto-detected if omitted)')
    parser.add_argument('--heatmap-metric', type=str, default=None,
                        help='Metric to color heatmap by (defaults to --metric)')
    parser.add_argument('--save-heatmap', type=str, default=None,
                        help='Save heatmap to file (e.g. heatmap.png)')

    args = parser.parse_args()

    if args.strategy not in STRATEGIES:
        print(f'❌ Unknown strategy: {args.strategy}')
        sys.exit(1)

    metric = METRIC_MAP.get(args.metric.lower())
    if not metric:
        print(f'❌ Unknown metric: {args.metric}  (options: {", ".join(METRIC_MAP)})')
        sys.exit(1)

    src = 'CCXT/Binance' if args.crypto else ('Tiingo FX' if args.forex else 'Tiingo')
    print(f'📡 Fetching {src} data for {args.symbol.upper()} ({args.days}d)...')
    try:
        df_raw = fetch_data(args.symbol, crypto=args.crypto, forex=args.forex,
                            period_days=args.days, timeframe=args.timeframe)
    except Exception as e:
        print(f'❌ {e}')
        sys.exit(1)

    print(f'✅ {len(df_raw)} rows  {df_raw.index[0].date()} → {df_raw.index[-1].date()}')
    filter_str = f'  (min-trades ≥ {args.min_trades})' if args.min_trades > 0 else ''
    print(f'\n🔧 Optimizing {args.strategy} on {args.symbol.upper()} (metric: {args.metric}){filter_str}')

    results = grid_search(df_raw, symbol=args.symbol.upper(), strategy=args.strategy,
                          metric=metric, capital=args.capital, commission=args.commission,
                          min_trades=args.min_trades)

    if not results:
        if args.min_trades > 0:
            print(f'No valid results (all combinations had < {args.min_trades} trades).')
        else:
            print('No valid results.')
        return

    top = results[:args.top]
    print(f'{"═" * 70}')
    print(f'  Top {len(top)} Parameter Combinations')
    print(f'{"═" * 70}')
    print(f'  {"#":>3}  {"Params":<35} {"Sharpe":>7} {"Return":>8} {"MaxDD":>7} {"Trades":>7}')
    print(f'{"─" * 70}')
    for i, row in enumerate(top, 1):
        r = row['result']
        params_str = ', '.join(f'{k}={v}' for k, v in row['params'].items())
        print(f'  {i:>3}  {params_str:<35} {r.sharpe_ratio:>7.2f} {r.total_return:>+7.1f}% '
              f'{r.max_drawdown:>6.1f}% {r.total_trades:>7}')

    print(f'{"═" * 70}')
    best = top[0]
    print(f'\n🏆 Best params: {best["params"]}')
    print(f'   Sharpe={best["result"].sharpe_ratio:.2f}  '
          f'Return={best["result"].total_return:+.1f}%  '
          f'MaxDD={best["result"].max_drawdown:.1f}%  '
          f'Trades={best["result"].total_trades}')

    # Heatmap
    if args.heatmap or args.save_heatmap:
        from charts import show_heatmap

        # Determine heatmap axes
        param_x = args.heatmap_x
        param_y = args.heatmap_y

        if not param_x or not param_y:
            default_axes = DEFAULT_HEATMAP_AXES.get(args.strategy)
            if default_axes:
                param_x = param_x or default_axes[0]
                param_y = param_y or default_axes[1]
            else:
                grid_keys = list(PARAM_GRIDS.get(args.strategy, {}).keys())
                if len(grid_keys) >= 2:
                    param_x = param_x or grid_keys[0]
                    param_y = param_y or grid_keys[1]
                else:
                    print('⚠️  Cannot auto-detect heatmap axes for this strategy. '
                          'Use --heatmap-x and --heatmap-y to specify.')
                    return

        heatmap_metric_key = args.heatmap_metric or args.metric
        heatmap_metric = METRIC_MAP.get(heatmap_metric_key.lower(), 'sharpe_ratio')

        print(f'\n🗺  Generating heatmap: X={param_x}  Y={param_y}  Color={heatmap_metric}')
        show_heatmap(
            grid_results=results,
            param_x=param_x,
            param_y=param_y,
            metric=heatmap_metric,
            title=f'{args.symbol.upper()} | {args.strategy}',
            save_path=args.save_heatmap,
        )


if __name__ == '__main__':
    main()
