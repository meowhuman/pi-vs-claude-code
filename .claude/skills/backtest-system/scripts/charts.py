#!/usr/bin/env python3
"""
Chart functions for backtest visualization.

Functions:
  show_equity_curve(result)  — Equity Curve vs Buy & Hold
  show_drawdown(result)      — Drawdown over time
  show_charts(result)        — Both equity + drawdown (2-panel)
  show_heatmap(...)          — 2D parameter optimization heatmap
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any, Optional

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def _require_matplotlib() -> None:
    if not HAS_MPL:
        raise ImportError(
            'matplotlib not installed. Run: uv add matplotlib'
        )


def show_equity_curve(result: Any, save_path: Optional[str] = None) -> None:
    """
    Plot equity curve (strategy vs Buy & Hold).
    Requires result.equity_curve and result.bh_equity_curve to be set
    (pass store_series=True to run_backtest).
    """
    _require_matplotlib()

    if result.equity_curve is None or result.bh_equity_curve is None:
        print('❌ No equity curve data. Run backtest with store_series=True.')
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(result.equity_curve.index, result.equity_curve.values,
            label=f'Strategy ({result.strategy})', color='#2196F3', linewidth=1.5)
    ax.plot(result.bh_equity_curve.index, result.bh_equity_curve.values,
            label='Buy & Hold', color='#FF9800', linewidth=1.2, linestyle='--', alpha=0.8)

    ax.axhline(y=result.initial_capital, color='gray', linestyle=':', linewidth=0.8, alpha=0.6)

    ax.set_title(
        f'📈 Equity Curve — {result.symbol} | {result.strategy}\n'
        f'Return: {result.total_return:+.2f}%  Sharpe: {result.sharpe_ratio:.2f}  '
        f'MaxDD: {result.max_drawdown:.2f}%  Alpha: {result.alpha:+.2f}%',
        fontsize=10, loc='left'
    )
    ax.set_ylabel('Portfolio Value ($)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'💾 Equity curve saved → {save_path}')
    else:
        plt.show()
    plt.close(fig)


def show_drawdown(result: Any, save_path: Optional[str] = None) -> None:
    """
    Plot drawdown chart.
    Requires result.drawdown_series to be set (pass store_series=True to run_backtest).
    """
    _require_matplotlib()

    if result.drawdown_series is None:
        print('❌ No drawdown data. Run backtest with store_series=True.')
        return

    fig, ax = plt.subplots(figsize=(12, 3))
    dd = result.drawdown_series
    ax.fill_between(dd.index, dd.values, 0, color='#F44336', alpha=0.4, label='Drawdown')
    ax.plot(dd.index, dd.values, color='#D32F2F', linewidth=0.8)
    ax.axhline(y=result.max_drawdown, color='#B71C1C', linestyle='--',
               linewidth=1, label=f'Max DD: {result.max_drawdown:.2f}%')

    ax.set_title(f'📉 Drawdown — {result.symbol} | Max: {result.max_drawdown:.2f}%',
                 fontsize=10, loc='left')
    ax.set_ylabel('Drawdown (%)')
    ax.legend(loc='lower left')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'💾 Drawdown chart saved → {save_path}')
    else:
        plt.show()
    plt.close(fig)


def show_charts(result: Any, save_path: Optional[str] = None) -> None:
    """
    Show both equity curve and drawdown in a 2-panel figure.
    """
    _require_matplotlib()

    if result.equity_curve is None or result.drawdown_series is None:
        print('❌ No chart data. Run backtest with store_series=True.')
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7),
                                    gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(
        f'{result.symbol}  |  {result.strategy}  |  {result.period}',
        fontsize=11, fontweight='bold'
    )

    # — Panel 1: Equity Curve —
    ax1.plot(result.equity_curve.index, result.equity_curve.values,
             label=f'Strategy  ret={result.total_return:+.1f}%  sharpe={result.sharpe_ratio:.2f}',
             color='#2196F3', linewidth=1.5)
    ax1.plot(result.bh_equity_curve.index, result.bh_equity_curve.values,
             label=f'Buy&Hold  ret={result.bh_total_return:+.1f}%',
             color='#FF9800', linewidth=1.2, linestyle='--', alpha=0.8)
    ax1.axhline(y=result.initial_capital, color='gray', linestyle=':', linewidth=0.8, alpha=0.5)
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    alpha_str = f'Alpha: {result.alpha:+.1f}%  Trades: {result.total_trades}  WinRate: {result.win_rate:.1f}%'
    ax1.set_title(alpha_str, fontsize=9, loc='right', color='gray')

    # — Panel 2: Drawdown —
    dd = result.drawdown_series
    ax2.fill_between(dd.index, dd.values, 0, color='#F44336', alpha=0.4)
    ax2.plot(dd.index, dd.values, color='#D32F2F', linewidth=0.8)
    ax2.axhline(y=result.max_drawdown, color='#B71C1C', linestyle='--',
                linewidth=1, label=f'Max DD: {result.max_drawdown:.2f}%')
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend(loc='lower left', fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'💾 Charts saved → {save_path}')
    else:
        plt.show()
    plt.close(fig)


def show_heatmap(
    grid_results: list[dict],
    param_x: str,
    param_y: str,
    metric: str = 'sharpe_ratio',
    title: str = '',
    save_path: Optional[str] = None,
) -> None:
    """
    2D Parameter Optimization Heatmap.

    X-axis = param_x values, Y-axis = param_y values, color = metric (Sharpe by default).

    Args:
        grid_results: list of {'params': dict, 'result': BacktestResult, 'metric_val': float}
        param_x: Name of the X-axis parameter (e.g. 'bb_period', 'rsi_period')
        param_y: Name of the Y-axis parameter (e.g. 'bb_std', 'rsi_lower')
        metric: Metric to color by ('sharpe_ratio', 'total_return', etc.)
        title: Plot title prefix
        save_path: If set, save to file instead of showing
    """
    _require_matplotlib()

    # Build pivot table
    rows = []
    for entry in grid_results:
        p = entry['params']
        r = entry['result']
        if param_x in p and param_y in p:
            rows.append({
                param_x: p[param_x],
                param_y: p[param_y],
                metric: getattr(r, metric, entry['metric_val']),
                'trades': r.total_trades,
            })

    if not rows:
        print(f'❌ No data for params {param_x} × {param_y}')
        return

    df = pd.DataFrame(rows)
    pivot = df.pivot_table(index=param_y, columns=param_x, values=metric, aggfunc='mean')

    # Sort axes
    pivot = pivot.sort_index(ascending=False)  # Y: larger values on top
    pivot = pivot.sort_index(axis=1)           # X: ascending

    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.0 + 2),
                                    max(5, len(pivot.index) * 0.8 + 2)))

    metric_label = metric.replace('_', ' ').title()
    cmap = 'RdYlGn'  # Red (bad) → Yellow → Green (good)
    if metric == 'max_drawdown':
        cmap = 'RdYlGn_r'  # Reverse: smaller (less negative) is better

    vmin = pivot.values[~np.isnan(pivot.values)].min() if not pivot.empty else None
    vmax = pivot.values[~np.isnan(pivot.values)].max() if not pivot.empty else None

    im = ax.imshow(pivot.values, cmap=cmap, aspect='auto', vmin=vmin, vmax=vmax)

    # Axes labels
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(v) for v in pivot.columns], fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([str(v) for v in pivot.index], fontsize=9)
    ax.set_xlabel(param_x, fontsize=10)
    ax.set_ylabel(param_y, fontsize=10)

    # Annotate cells
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                suffix = '%' if 'return' in metric or 'drawdown' in metric else ''
                fmt = f'{val:+.2f}{suffix}' if 'return' in metric or 'alpha' in metric else f'{val:.2f}{suffix}'
                text_color = 'black' if 0.3 < (val - (vmin or 0)) / max((vmax or 1) - (vmin or 0), 1e-9) < 0.7 else 'white'
                ax.text(j, i, fmt, ha='center', va='center', fontsize=8, color=text_color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label(metric_label, fontsize=9)

    best_idx = np.nanargmax(pivot.values) if metric != 'max_drawdown' else np.nanargmin(pivot.values)
    best_i, best_j = np.unravel_index(best_idx, pivot.values.shape)
    ax.add_patch(plt.Rectangle((best_j - 0.5, best_i - 0.5), 1, 1,
                                fill=False, edgecolor='gold', linewidth=2.5, label='Best'))
    ax.legend(loc='upper right', fontsize=8)

    t = title or f'Parameter Heatmap'
    ax.set_title(f'🗺 {t}\nX={param_x}  Y={param_y}  Color={metric_label}', fontsize=10)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'💾 Heatmap saved → {save_path}')
    else:
        plt.show()
    plt.close(fig)
