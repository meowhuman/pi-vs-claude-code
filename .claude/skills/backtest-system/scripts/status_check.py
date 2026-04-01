#!/usr/bin/env python3
"""
Status Check — verify Tiingo API and CCXT connectivity

Usage:
    uv run python scripts/status_check.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def check_tiingo():
    print('\n1️⃣  Tiingo API (stocks)')
    print('-' * 40)
    try:
        from data import fetch_stock_data
        df = fetch_stock_data('SPY', period_days=5)
        if df.empty:
            print('   ❌ No data returned')
            return False
        latest = df.iloc[-1]
        print(f'   ✅ Connected')
        print(f'   📈 SPY latest: ${latest["close"]:.2f}  ({df.index[-1].date()})')
        print(f'   📊 Data rows:  {len(df)}')
        return True
    except Exception as e:
        print(f'   ❌ {e}')
        return False


def check_ccxt():
    print('\n2️⃣  CCXT / Binance (crypto)')
    print('-' * 40)
    try:
        from data import fetch_crypto_data
        df = fetch_crypto_data('BTC', timeframe='1d', limit=5)
        if df.empty:
            print('   ❌ No data returned')
            return False
        latest = df.iloc[-1]
        print(f'   ✅ Connected')
        print(f'   🪙 BTC/USDT latest: ${latest["close"]:,.2f}  ({df.index[-1].date()})')
        print(f'   📊 Data rows:  {len(df)}')
        return True
    except Exception as e:
        print(f'   ❌ {e}')
        return False


def check_strategies():
    print('\n3️⃣  Strategies')
    print('-' * 40)
    try:
        from strategies import STRATEGIES
        print(f'   ✅ {len(STRATEGIES)} strategies loaded')
        for name in sorted(STRATEGIES.keys()):
            print(f'      - {name}')
        return True
    except Exception as e:
        print(f'   ❌ {e}')
        return False


def check_quick_run():
    print('\n4️⃣  Quick backtest smoke test (SPY, sma_crossover, 30d)')
    print('-' * 40)
    try:
        from data import fetch_stock_data
        from strategies import STRATEGIES
        from engine import run_backtest

        df = fetch_stock_data('SPY', period_days=90)
        df = STRATEGIES['sma_crossover'](df)
        r = run_backtest(df, symbol='SPY', strategy='sma_crossover')
        if r.success:
            print(f'   ✅ Backtest ran successfully')
            print(f'   📊 SPY sma_crossover: return={r.total_return:+.2f}%  sharpe={r.sharpe_ratio:.2f}')
        else:
            print(f'   ⚠️  {r.error}')
        return r.success
    except Exception as e:
        print(f'   ❌ {e}')
        return False


def main():
    print('\n📊 Backtest System Status Check (Tiingo + CCXT)')
    print('=' * 50)

    tiingo_ok = check_tiingo()
    ccxt_ok = check_ccxt()
    strat_ok = check_strategies()
    run_ok = check_quick_run()

    print(f'\n{"=" * 50}')
    all_ok = tiingo_ok and ccxt_ok and strat_ok and run_ok
    if all_ok:
        print('✅ All systems operational')
    else:
        print('⚠️  Some checks failed — see above')
        if not tiingo_ok:
            print('   • Tiingo: check TIINGO_API_KEY env var')
        if not ccxt_ok:
            print('   • CCXT: run `uv sync` to install ccxt')
    print('=' * 50)


if __name__ == '__main__':
    main()
