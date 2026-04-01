#!/usr/bin/env python3
"""
Backtest engine — signal-based P&L calculation (pure pandas).
signal: 1=long, -1=cash/short, 0=hold previous

Supports:
  - Take Profit  (--take-profit 0.10  = exit when +10%)
  - Stop Loss    (--stop-loss 0.05    = exit when -5%)
  - Trailing Stop (--trailing-stop 0.05 = exit when 5% below peak)
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_RISK_FREE_RATE = 0.0  # Set to e.g. 0.04 for textbook Sharpe


@dataclass
class BacktestResult:
    symbol: str
    strategy: str
    period: str
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    calmar_ratio: float
    # Benchmark (Buy & Hold)
    bh_total_return: float = 0.0
    bh_annualized_return: float = 0.0
    bh_sharpe: float = 0.0
    bh_max_drawdown: float = 0.0
    alpha: float = 0.0  # strategy annualized - benchmark annualized
    success: bool = True
    error: Optional[str] = None
    # Chart data (optional)
    equity_curve: Optional[pd.Series] = field(default=None, repr=False)
    bh_equity_curve: Optional[pd.Series] = field(default=None, repr=False)
    drawdown_series: Optional[pd.Series] = field(default=None, repr=False)


def apply_risk_management(
    df: pd.DataFrame,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    trailing_stop: Optional[float] = None,
) -> pd.DataFrame:
    """
    Apply TP/SL/trailing stop to a position series (modifies 'pos' column in-place).

    After a forced exit (TP/SL/trail triggered), re-entry is blocked until the
    original signal resets to 0 then back to 1 (prevents double-counting same trade).

    Args:
        df: DataFrame with 'pos' (0/1) and 'close' columns
        take_profit: Exit when price >= entry * (1 + take_profit)
        stop_loss: Exit when price <= entry * (1 - stop_loss)
        trailing_stop: Exit when price <= peak * (1 - trailing_stop)
    """
    if not any([take_profit, stop_loss, trailing_stop]):
        return df

    positions = df['pos'].values.copy().astype(float)
    closes = df['close'].values

    in_trade = False
    forced_exit = False
    entry_price = 0.0
    peak_price = 0.0

    for i in range(len(positions)):
        orig_pos = positions[i]

        if forced_exit:
            positions[i] = 0.0
            if orig_pos == 0:  # original signal reset → allow re-entry next time
                forced_exit = False
                in_trade = False
            continue

        if not in_trade and orig_pos == 1:
            in_trade = True
            entry_price = closes[i]
            peak_price = closes[i]
        elif in_trade and orig_pos == 0:
            in_trade = False
        elif in_trade and orig_pos == 1:
            # Update trailing peak
            if closes[i] > peak_price:
                peak_price = closes[i]

            exit_triggered = False
            if take_profit and closes[i] >= entry_price * (1.0 + take_profit):
                exit_triggered = True
            if stop_loss and closes[i] <= entry_price * (1.0 - stop_loss):
                exit_triggered = True
            if trailing_stop and closes[i] <= peak_price * (1.0 - trailing_stop):
                exit_triggered = True

            if exit_triggered:
                positions[i] = 0.0
                forced_exit = True
                in_trade = False

    df = df.copy()
    df['pos'] = positions
    return df


def run_backtest(
    df: pd.DataFrame,
    symbol: str,
    strategy: str,
    capital: float = 100_000,
    commission: float = 0.001,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    trailing_stop: Optional[float] = None,
    store_series: bool = False,
) -> BacktestResult:
    """
    Run signal-based backtest (long-only) with Buy & Hold benchmark.
    df must contain 'close' and 'signal' columns.

    Args:
        take_profit: Float e.g. 0.10 = exit at +10% from entry
        stop_loss: Float e.g. 0.05 = exit at -5% from entry
        trailing_stop: Float e.g. 0.05 = exit when 5% below peak
        store_series: If True, attach equity_curve/drawdown_series to result (for charting)
    """
    df = df.dropna(subset=['close', 'signal']).copy()

    if len(df) < 20:
        return BacktestResult(
            symbol=symbol, strategy=strategy, period='', initial_capital=capital,
            final_capital=capital, total_return=0, annualized_return=0,
            sharpe_ratio=0, max_drawdown=0, win_rate=0, total_trades=0,
            profit_factor=0, calmar_ratio=0, success=False, error='Not enough data'
        )

    rf_daily = risk_free_rate / 252

    # ── Position (long-only, shifted by 1 to avoid look-ahead) ──
    df['pos'] = df['signal'].shift(1).clip(lower=0).fillna(0)

    # ── Apply risk management (TP/SL/trailing) ──
    if any([take_profit, stop_loss, trailing_stop]):
        df = apply_risk_management(df, take_profit=take_profit,
                                   stop_loss=stop_loss, trailing_stop=trailing_stop)

    df['daily_ret'] = df['close'].pct_change()
    df['pos_change'] = df['pos'].diff().abs()
    df['cost'] = df['pos_change'] * commission
    df['strat_ret'] = df['pos'] * df['daily_ret'] - df['cost']

    # Equity curve
    valid_ret = df['strat_ret'].fillna(0)
    df['equity'] = capital * (1 + valid_ret).cumprod()

    period_days = len(df)
    final_capital = float(df['equity'].iloc[-1])
    total_return = (final_capital / capital - 1) * 100
    years = period_days / 252
    annualized = ((final_capital / capital) ** (1 / max(years, 0.01)) - 1) * 100

    # Sharpe
    daily = df['strat_ret'].dropna()
    excess = daily.mean() - rf_daily
    sharpe = float((excess / daily.std()) * 252 ** 0.5) if daily.std() > 0 else 0.0

    # Max drawdown
    roll_max = df['equity'].cummax()
    dd = (df['equity'] - roll_max) / roll_max * 100
    max_dd = float(dd.min())
    calmar = annualized / abs(max_dd) if max_dd != 0 else 0.0

    # Trades
    trades: list[float] = []
    in_trade = False
    entry = 0.0
    for row in df.itertuples():
        p = row.pos
        c = row.close
        if not in_trade and p == 1:
            in_trade, entry = True, c
        elif in_trade and p == 0:
            in_trade = False
            trades.append(c / entry - 1)
    if in_trade:
        trades.append(float(df['close'].iloc[-1]) / entry - 1)

    total_trades = len(trades)
    win_rate = sum(1 for t in trades if t > 0) / total_trades * 100 if total_trades else 0.0
    wins = sum(t for t in trades if t > 0)
    losses = sum(-t for t in trades if t < 0)
    profit_factor = wins / losses if losses > 0 else float('inf')
    period_str = f'{df.index[0].date()} to {df.index[-1].date()}'

    # ── Buy & Hold Benchmark ──
    bh_ret = df['daily_ret'].fillna(0)
    bh_equity = capital * (1 + bh_ret).cumprod()
    bh_final = float(bh_equity.iloc[-1])
    bh_total_return = (bh_final / capital - 1) * 100
    bh_annualized = ((bh_final / capital) ** (1 / max(years, 0.01)) - 1) * 100
    bh_excess = bh_ret.mean() - rf_daily
    bh_sharpe = float((bh_excess / bh_ret.std()) * 252 ** 0.5) if bh_ret.std() > 0 else 0.0
    bh_roll_max = bh_equity.cummax()
    bh_dd = (bh_equity - bh_roll_max) / bh_roll_max * 100
    bh_max_dd = float(bh_dd.min())
    alpha = annualized - bh_annualized

    return BacktestResult(
        symbol=symbol, strategy=strategy, period=period_str,
        initial_capital=capital, final_capital=final_capital,
        total_return=total_return, annualized_return=annualized,
        sharpe_ratio=sharpe, max_drawdown=max_dd, win_rate=win_rate,
        total_trades=total_trades, profit_factor=profit_factor, calmar_ratio=calmar,
        bh_total_return=bh_total_return, bh_annualized_return=bh_annualized,
        bh_sharpe=bh_sharpe, bh_max_drawdown=bh_max_dd, alpha=alpha,
        equity_curve=df['equity'] if store_series else None,
        bh_equity_curve=bh_equity if store_series else None,
        drawdown_series=dd if store_series else None,
    )


def print_result(r: BacktestResult, show_risk_params: bool = False,
                 take_profit: Optional[float] = None,
                 stop_loss: Optional[float] = None,
                 trailing_stop: Optional[float] = None) -> None:
    if not r.success:
        print(f'❌ Backtest failed: {r.error}')
        return
    print(f'\n{"═" * 65}')
    print(f'  {r.symbol} │ {r.strategy}')
    print(f'{"═" * 65}')
    print(f'  Period:       {r.period}')
    print(f'  Capital:      ${r.initial_capital:,.0f} → ${r.final_capital:,.0f}')
    if show_risk_params:
        parts = []
        if take_profit:
            parts.append(f'TP={take_profit*100:.1f}%')
        if stop_loss:
            parts.append(f'SL={stop_loss*100:.1f}%')
        if trailing_stop:
            parts.append(f'Trail={trailing_stop*100:.1f}%')
        if parts:
            print(f'  Risk Mgmt:    {" | ".join(parts)}')
    print(f'{"─" * 65}')
    print(f'  {"":<16} {"Strategy":>12} {"Buy&Hold":>12}')
    print(f'  {"─"*16} {"─"*12} {"─"*12}')
    print(f'  {"Total Return":<16} {r.total_return:>+11.2f}% {r.bh_total_return:>+11.2f}%')
    print(f'  {"Annualized":<16} {r.annualized_return:>+11.2f}% {r.bh_annualized_return:>+11.2f}%')
    print(f'  {"Sharpe":<16} {r.sharpe_ratio:>12.2f} {r.bh_sharpe:>12.2f}')
    print(f'  {"Max Drawdown":<16} {r.max_drawdown:>11.2f}% {r.bh_max_drawdown:>11.2f}%')
    print(f'  {"Calmar":<16} {r.calmar_ratio:>12.2f} {"":>12}')
    print(f'{"─" * 65}')
    print(f'  Alpha:        {r.alpha:+.2f}%  ({"outperforms" if r.alpha > 0 else "underperforms"} benchmark)')
    print(f'{"─" * 65}')
    print(f'  Win Rate:     {r.win_rate:.1f}%')
    print(f'  Trades:       {r.total_trades}')
    print(f'  Profit Factor:{r.profit_factor:.2f}')
    print(f'{"─" * 65}')
    if r.sharpe_ratio >= 1.0 and r.alpha > 0:
        print('  ✅ PASS — Sharpe ≥ 1.0 & Alpha > 0')
    elif r.sharpe_ratio >= 1.0:
        print('  🟡 GOOD Sharpe but negative Alpha')
    elif r.sharpe_ratio >= 0.5:
        print('  🟡 MAYBE — Sharpe 0.5-1.0')
    else:
        print('  ❌ FAIL — Sharpe < 0.5')
    print(f'{"═" * 65}')
