#!/bin/bash
# Launch Backtest Dashboard (placeholder)
# This skill uses CLI tools; dashboard UI is not implemented yet.
# For quick backtest, use: uv run scripts/quick_backtest.py

echo "📊 Backtest System (Tiingo + CCXT)"
echo ""
echo "Available commands:"
echo "  uv run scripts/status_check.py         # Verify connectivity"
echo "  uv run scripts/quick_backtest.py --help # Single backtest"
echo "  uv run scripts/strategy_scanner.py      # Multi-strategy scan"
echo "  uv run scripts/optimize_params.py       # Grid search"
echo ""
echo "Example:"
echo "  uv run scripts/quick_backtest.py --symbol SPY --strategy sma_crossover"
