#!/usr/bin/env python3
"""
Quick Backtest — Tiingo (stocks + forex) + CCXT/Binance (crypto), pandas engine

Usage:
    uv run python scripts/quick_backtest.py --symbol AAPL --strategy sma_crossover
    uv run python scripts/quick_backtest.py --symbol BTC --strategy rsi --crypto
    uv run python scripts/quick_backtest.py --symbol SPY --strategy macd --days 730
    uv run python scripts/quick_backtest.py --symbol EURUSD --strategy rsi --forex
    uv run python scripts/quick_backtest.py --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell" --symbol AAPL
    uv run python scripts/quick_backtest.py --list-strategies
    uv run python scripts/quick_backtest.py --list-indicators

    # Risk management
    uv run python scripts/quick_backtest.py --symbol AAPL --strategy rsi --stop-loss 0.05 --take-profit 0.15
    uv run python scripts/quick_backtest.py --symbol BTC --strategy macd --crypto --trailing-stop 0.08

    # Charts
    uv run python scripts/quick_backtest.py --symbol SPY --strategy sma_crossover --chart
    uv run python scripts/quick_backtest.py --symbol AAPL --strategy rsi --chart --save-chart chart.png

Strategies: sma_crossover, ema_crossover, rsi, bollinger_bands, macd, momentum, compose
Data:
  Stocks  → Tiingo API (daily, up to 5y)
  Forex   → Tiingo FX API (daily)
  Crypto  → CCXT/Binance (1m–1d timeframes)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from data import fetch_data
from strategies import STRATEGIES, _INDICATOR_MAP
from engine import run_backtest, print_result

STOCK_EXAMPLES = ['AAPL', 'SPY', 'QQQ', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN']
CRYPTO_EXAMPLES = ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE']


def main():
    parser = argparse.ArgumentParser(
        description='Quick Backtest — Tiingo (stocks) + CCXT (crypto)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --symbol AAPL --strategy sma_crossover
  %(prog)s --symbol SPY --strategy rsi --rsi-lower 25 --rsi-upper 75
  %(prog)s --symbol BTC --strategy macd --crypto
  %(prog)s --symbol EURUSD --strategy rsi --forex
  %(prog)s --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell" --symbol AAPL
  %(prog)s --list-strategies
  %(prog)s --list-indicators

  # Risk management
  %(prog)s --symbol AAPL --strategy rsi --stop-loss 0.05 --take-profit 0.15
  %(prog)s --symbol BTC --strategy macd --crypto --trailing-stop 0.08

  # Charts (opens window or saves file)
  %(prog)s --symbol SPY --strategy sma_crossover --chart
  %(prog)s --symbol AAPL --strategy rsi --chart --save-chart aapl_rsi.png
        '''
    )
    parser.add_argument('--symbol', '-s', type=str, help='Symbol (e.g. AAPL, SPY, BTC)')
    parser.add_argument('--strategy', '-t', type=str, default='sma_crossover',
                        help='Strategy name (default: sma_crossover)')
    parser.add_argument('--days', type=int, default=365, help='Lookback period in days (default: 365)')
    parser.add_argument('--capital', '-c', type=float, default=100_000, help='Initial capital')
    parser.add_argument('--commission', type=float, default=0.001, help='Commission rate (default: 0.1%%)')
    parser.add_argument('--crypto', action='store_true', help='Use CCXT/Binance for crypto data')
    parser.add_argument('--forex', action='store_true', help='Use Tiingo FX for forex data (auto-detected for 6-char pairs)')
    parser.add_argument('--timeframe', type=str, default='1d',
                        help='Crypto timeframe: 1m/5m/15m/1h/4h/1d (default: 1d)')
    parser.add_argument('--list-strategies', action='store_true', help='List available strategies')
    parser.add_argument('--list-symbols', action='store_true', help='Show example symbols')

    # Strategy params
    parser.add_argument('--short-ma', type=int, default=10, help='SMA short window (default: 10)')
    parser.add_argument('--long-ma', type=int, default=30, help='SMA long window (default: 30)')
    parser.add_argument('--short-ema', type=int, default=9, help='EMA short window (default: 9)')
    parser.add_argument('--long-ema', type=int, default=21, help='EMA long window (default: 21)')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI period (default: 14)')
    parser.add_argument('--rsi-lower', type=int, default=30, help='RSI oversold threshold (default: 30)')
    parser.add_argument('--rsi-upper', type=int, default=70, help='RSI overbought threshold (default: 70)')
    parser.add_argument('--bb-period', type=int, default=20, help='BB period (default: 20)')
    parser.add_argument('--bb-std', type=float, default=2.0, help='BB std multiplier (default: 2.0)')
    parser.add_argument('--macd-fast', type=int, default=12, help='MACD fast EMA (default: 12)')
    parser.add_argument('--macd-slow', type=int, default=26, help='MACD slow EMA (default: 26)')
    parser.add_argument('--macd-signal', type=int, default=9, help='MACD signal period (default: 9)')
    parser.add_argument('--momentum-lb', type=int, default=20, help='Momentum lookback (default: 20)')
    parser.add_argument('--momentum-threshold', type=float, default=0.02, help='Momentum threshold (default: 0.02)')

    # Risk management
    parser.add_argument('--take-profit', type=float, default=None,
                        help='Take profit threshold, e.g. 0.10 = exit at +10%% from entry')
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='Stop loss threshold, e.g. 0.05 = exit at -5%% from entry')
    parser.add_argument('--trailing-stop', type=float, default=None,
                        help='Trailing stop, e.g. 0.05 = exit when 5%% below peak price')
    parser.add_argument('--min-trades', type=int, default=0,
                        help='Minimum number of trades required (default: 0 = no filter)')

    # Charts
    parser.add_argument('--chart', action='store_true',
                        help='Show equity curve + drawdown chart after backtest')
    parser.add_argument('--save-chart', type=str, default=None,
                        help='Save chart to file (e.g. chart.png) instead of showing window')

    # Compose mode
    parser.add_argument('--compose', nargs='+', metavar='RULE',
                        help='Compose multi-indicator strategy. Rules: "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell"')
    parser.add_argument('--list-indicators', action='store_true', help='List available indicators for --compose')

    args = parser.parse_args()

    if args.list_strategies:
        print('\n📊 Available Strategies:')
        print('-' * 50)
        descs = {
            'sma_crossover':   'SMA golden/death cross (long-only)',
            'ema_crossover':   'EMA golden/death cross (long-only)',
            'rsi':             'RSI mean reversion (oversold buy)',
            'bollinger_bands': 'BB breakout reversal',
            'macd':            'MACD crossover (long-only)',
            'momentum':        'N-day price momentum',
            'compose':         '🧪 Multi-indicator composer (use --compose)',
        }
        for name, desc in descs.items():
            print(f'  {name:<20} {desc}')
        print(f'\n💡 Use --compose for custom multi-indicator strategies:')
        print(f'   %(prog)s --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell" --symbol AAPL')
        return

    if args.list_indicators:
        print('\n📐 Available Indicators for --compose:')
        print('-' * 60)
        indicator_descs = {
            'rsi': 'RSI (14-period), range 0-100',
            'macd': 'MACD line value',
            'macd_signal': 'MACD signal line value',
            'macd_hist': 'MACD histogram (MACD - signal)',
            'macd_cross': '1=golden cross, -1=death cross',
            'bb_pctb': 'Bollinger %B, range 0-1 (below=oversold)',
            'adx': 'ADX trend strength, >25=strong',
            'atr': 'Average True Range (14)',
            'stoch_k': 'Stochastic %K (14), range 0-100',
            'mom': '20-day momentum (% change)',
            'vol_ratio': 'Volume / 20d avg volume',
            'sma5|10|20|50|200': 'Simple Moving Averages',
            'ema9|12|21|26|50': 'Exponential Moving Averages',
            'price_vs_sma20': 'Price / SMA20 ratio',
            'price_vs_sma50': 'Price / SMA50 ratio',
            'close': 'Current close price',
        }
        for name, desc in indicator_descs.items():
            print(f'  {name:<22} {desc}')
        print(f'\n📝 Rule format: "indicator<value:action"')
        print(f'   Operators: <, <=, >, >=, ==, !=')
        print(f'   Actions: buy (AND logic), sell (OR logic)')
        print(f'\n💡 Examples:')
        print(f'   --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell"')
        print(f'   --compose "rsi<25:buy" "adx>25:buy" "bb_pctb<0.1:buy" "rsi>75:sell"')
        print(f'   --compose "stoch_k<20:buy" "vol_ratio>1.5:buy" "stoch_k>80:sell"')
        return

    if args.list_symbols:
        print('\n📈 Stock examples (Tiingo):')
        print('  ' + ', '.join(STOCK_EXAMPLES))
        print('\n🪙 Crypto examples (CCXT/Binance, use --crypto):')
        print('  ' + ', '.join(CRYPTO_EXAMPLES))
        print('\n💱 Forex examples (Tiingo FX, auto-detected):')
        print('  EURUSD, GBPUSD, USDJPY, XAUUSD, XAGUSD')
        return

    if not args.symbol:
        parser.print_help()
        return

    # If --compose is used, override strategy to 'compose'
    if args.compose:
        args.strategy = 'compose'

    if args.strategy not in STRATEGIES and args.strategy != 'compose':
        print(f'❌ Unknown strategy: {args.strategy}')
        print(f'   Run --list-strategies to see available options')
        sys.exit(1)

    src = 'CCXT/Binance' if args.crypto else ('Tiingo FX' if args.forex else 'Tiingo')
    print(f'📡 Fetching {src} data for {args.symbol.upper()} ({args.days}d)...')
    try:
        df = fetch_data(args.symbol, crypto=args.crypto, forex=args.forex,
                        period_days=args.days, timeframe=args.timeframe)
    except Exception as e:
        print(f'❌ Data fetch failed: {e}')
        sys.exit(1)

    print(f'✅ {len(df)} candles  {df.index[0].date()} → {df.index[-1].date()}')

    # Build strategy params
    params: dict = {}
    s = args.strategy
    if s == 'compose':
        compose_rules = args.compose if args.compose else []
        if not compose_rules:
            print('❌ --compose requires at least one rule.')
            print('   Example: --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell"')
            print('   Run --list-indicators to see available indicators.')
            sys.exit(1)
        strategy_label = 'compose: ' + ' & '.join(compose_rules)
        params = {'rule_strings': compose_rules}
    elif s == 'sma_crossover':
        strategy_label = s
        params = {'short_ma': args.short_ma, 'long_ma': args.long_ma}
    elif s == 'ema_crossover':
        strategy_label = s
        params = {'short_ema': args.short_ema, 'long_ema': args.long_ema}
    elif s == 'rsi':
        strategy_label = s
        params = {'rsi_period': args.rsi_period,
                  'rsi_lower': args.rsi_lower, 'rsi_upper': args.rsi_upper}
    elif s == 'bollinger_bands':
        strategy_label = s
        params = {'bb_period': args.bb_period, 'bb_std': args.bb_std}
    elif s == 'macd':
        strategy_label = s
        params = {'fast': args.macd_fast, 'slow': args.macd_slow,
                  'signal_period': args.macd_signal}
    elif s == 'momentum':
        strategy_label = s
        params = {'lookback': args.momentum_lb, 'threshold': args.momentum_threshold}
    else:
        strategy_label = s

    # Show risk management params if any
    risk_used = any([args.take_profit, args.stop_loss, args.trailing_stop])
    if risk_used:
        parts = []
        if args.take_profit:
            parts.append(f'TP={args.take_profit*100:.1f}%')
        if args.stop_loss:
            parts.append(f'SL={args.stop_loss*100:.1f}%')
        if args.trailing_stop:
            parts.append(f'Trail={args.trailing_stop*100:.1f}%')
        print(f'🛡  Risk Mgmt: {" | ".join(parts)}')

    need_series = args.chart or args.save_chart is not None

    df = STRATEGIES[s](df, **params)
    result = run_backtest(
        df,
        symbol=args.symbol.upper(),
        strategy=strategy_label,
        capital=args.capital,
        commission=args.commission,
        take_profit=args.take_profit,
        stop_loss=args.stop_loss,
        trailing_stop=args.trailing_stop,
        store_series=need_series,
    )

    # --min-trades filter
    if args.min_trades > 0 and result.total_trades < args.min_trades:
        print(f'\n⚠️  Skipped — only {result.total_trades} trades (min required: {args.min_trades})')
        return

    print_result(
        result,
        show_risk_params=risk_used,
        take_profit=args.take_profit,
        stop_loss=args.stop_loss,
        trailing_stop=args.trailing_stop,
    )

    # Charts
    if need_series:
        from charts import show_charts
        show_charts(result, save_path=args.save_chart)


if __name__ == '__main__':
    main()
