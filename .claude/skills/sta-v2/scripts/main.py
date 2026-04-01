#!/usr/bin/env python3
"""
sta-v2: Self-contained Stock Technical Analyzer
Bundled tools, no external MCP server dependency.
Usage: uv run scripts/main.py <command> <SYMBOL> [period]
"""
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from dotenv import load_dotenv

# Load .env: skill root first, then MCP server path as fallback
_SKILL_ROOT = Path(__file__).parent.parent
_MCP_SERVER_PATH = Path(os.getenv("STA_MCP_PATH", "/Volumes/Ketomuffin_mac/AI/mcpserver/mcp-stock-ta"))
load_dotenv(_SKILL_ROOT / ".env")  # skill-local .env takes priority
load_dotenv(_MCP_SERVER_PATH / ".env", override=False)  # fallback

# Add bundled tools to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from tools.advanced_indicators import (
        calculate_accumulation_distribution,
        calculate_chaikin_oscillator,
        calculate_ease_of_movement,
        calculate_force_index,
        calculate_ichimoku_cloud,
        calculate_keltner_channels,
        calculate_klinger_oscillator,
        calculate_mfi,
        calculate_negative_volume_index,
        calculate_obv,
        calculate_parabolic_sar,
        calculate_positive_volume_index,
        calculate_trix,
        calculate_volume_oscillator,
        calculate_volume_weighted_moving_average,
        calculate_vwap,
    )
    from tools.stock_ta_tool import (
        get_stock_data,
        get_technical_indicators,
        is_forex_ticker,
        momentum_stock_score,
    )
    from tools.volume_indicators import get_volume_indicators_analysis
except ImportError as e:
    print(json.dumps({"error": f"Failed to import bundled tools: {e}"}))
    sys.exit(1)

STANDARD_INDICATORS = [
    "SMA", "EMA", "RSI", "MACD", "BOLLINGER",
    "ATR", "STOCHASTIC", "ADX", "WILLIAMS_R", "CCI",
]

ADVANCED_INDICATORS = [
    "VWAP", "OBV", "MFI", "Volume_Oscillator", "AD_Line",
    "Chaikin_Oscillator", "TRIX", "Parabolic_SAR", "Keltner_Channels",
    "Ichimoku_Cloud", "Force_Index", "Ease_of_Movement", "NVI", "PVI",
    "VWMA", "Klinger_Oscillator",
]

# 外匯不支援的成交量相關進階指標
FOREX_UNSUPPORTED_INDICATORS = [
    "OBV", "MFI", "Volume_Oscillator", "AD_Line",
    "Chaikin_Oscillator", "Force_Index", "NVI", "PVI",
    "VWMA", "Klinger_Oscillator",
]

ALL_INDICATORS = STANDARD_INDICATORS + ADVANCED_INDICATORS


def run_quiet(func, *args, **kwargs):
    """Run function suppressing stdout/stderr to keep JSON output clean."""
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


def calc_advanced(df, name: str) -> dict:
    """Calculate a single advanced indicator, return dict result."""
    try:
        if name == "VWAP":
            return {"VWAP": float(calculate_vwap(df).iloc[-1])}

        elif name == "OBV":
            s = calculate_obv(df)
            return {"OBV": float(s.iloc[-1]), "OBV_trend": "UP" if s.iloc[-1] > s.iloc[-5] else "DOWN"}

        elif name == "MFI":
            v = float(calculate_mfi(df).iloc[-1])
            return {"MFI": round(v, 2), "signal": "OVERBOUGHT" if v > 80 else "OVERSOLD" if v < 20 else "NEUTRAL"}

        elif name == "Volume_Oscillator":
            v = float(calculate_volume_oscillator(df).iloc[-1])
            return {"Volume_Oscillator": round(v, 2), "signal": "INCREASING" if v > 0 else "DECREASING"}

        elif name == "AD_Line":
            s = calculate_accumulation_distribution(df)
            return {"AD_Line": float(s.iloc[-1]), "trend": "UP" if s.iloc[-1] > s.iloc[-5] else "DOWN"}

        elif name == "Chaikin_Oscillator":
            s = calculate_chaikin_oscillator(df)
            cur, prev = float(s.iloc[-1]), float(s.iloc[-2]) if len(s) > 1 else 0
            sig = "BUY" if cur > 0 and prev <= 0 else "SELL" if cur < 0 and prev >= 0 else "NEUTRAL"
            return {"Chaikin_Oscillator": round(cur, 2), "signal": sig}

        elif name == "TRIX":
            return {"TRIX": round(float(calculate_trix(df["close"]).iloc[-1]), 4)}

        elif name == "Parabolic_SAR":
            sar = float(calculate_parabolic_sar(df).iloc[-1])
            price = float(df["close"].iloc[-1])
            return {"Parabolic_SAR": round(sar, 2), "signal": "BULLISH" if sar < price else "BEARISH"}

        elif name == "Keltner_Channels":
            kc = calculate_keltner_channels(df)
            price = float(df["close"].iloc[-1])
            upper, lower, mid = float(kc["upper"].iloc[-1]), float(kc["lower"].iloc[-1]), float(kc["middle"].iloc[-1])
            pos = "ABOVE_UPPER" if price > upper else "BELOW_LOWER" if price < lower else "WITHIN"
            return {"Keltner_Upper": round(upper, 2), "Keltner_Middle": round(mid, 2), "Keltner_Lower": round(lower, 2), "position": pos}

        elif name == "Ichimoku_Cloud":
            ichi = calculate_ichimoku_cloud(df)
            chikou = round(float(ichi["chikou_span"].iloc[-26]), 2) if len(ichi["chikou_span"]) > 26 else None
            return {
                "Tenkan_Sen": round(float(ichi["tenkan_sen"].iloc[-1]), 2),
                "Kijun_Sen": round(float(ichi["kijun_sen"].iloc[-1]), 2),
                "Senkou_Span_A": round(float(ichi["senkou_span_a"].iloc[-1]), 2),
                "Senkou_Span_B": round(float(ichi["senkou_span_b"].iloc[-1]), 2),
                "Chikou_Span": chikou,
            }

        elif name == "Force_Index":
            v = float(calculate_force_index(df).iloc[-1])
            return {"Force_Index": round(v, 2), "signal": "BUY" if v > 0 else "SELL" if v < 0 else "NEUTRAL"}

        elif name == "Ease_of_Movement":
            v = float(calculate_ease_of_movement(df).iloc[-1])
            return {"Ease_of_Movement": round(v, 4), "signal": "BULLISH" if v > 0 else "BEARISH"}

        elif name == "NVI":
            s = calculate_negative_volume_index(df)
            return {"NVI": float(s.iloc[-1]), "trend": "UP" if s.iloc[-1] > s.iloc[-5] else "DOWN"}

        elif name == "PVI":
            s = calculate_positive_volume_index(df)
            return {"PVI": float(s.iloc[-1]), "trend": "UP" if s.iloc[-1] > s.iloc[-5] else "DOWN"}

        elif name == "VWMA":
            v = float(calculate_volume_weighted_moving_average(df["close"], df["volume"]).iloc[-1])
            price = float(df["close"].iloc[-1])
            return {"VWMA": round(v, 2), "signal": "ABOVE" if price > v else "BELOW"}

        elif name == "Klinger_Oscillator":
            ko = calculate_klinger_oscillator(df)
            k, s = float(ko["klinger"].iloc[-1]), float(ko["signal"].iloc[-1])
            return {
                "Klinger": round(k, 2),
                "Signal": round(s, 2),
                "Histogram": round(float(ko["histogram"].iloc[-1]), 2),
                "direction": "BULLISH" if k > s else "BEARISH",
            }

        return {"error": f"Unknown indicator: {name}"}

    except Exception as e:
        return {"error": str(e)}


def get_all_indicators(ticker: str, period: str = "365d") -> dict:
    result = run_quiet(get_technical_indicators, ticker, indicators=STANDARD_INDICATORS, time_period=period)
    try:
        df = run_quiet(get_stock_data, ticker, period)
        
        # 外匯無成交量，跳過成交量相關進階指標
        is_forex = is_forex_ticker(ticker)
        available_advanced = [
            ind for ind in ADVANCED_INDICATORS
            if not (is_forex and ind in FOREX_UNSUPPORTED_INDICATORS)
        ]
        
        advanced = {ind: calc_advanced(df, ind) for ind in available_advanced}
        
        if is_forex:
            advanced["_forex_note"] = "外匯無成交量，成交量相關指標已跳過"
        
        if "indicators" in result:
            result["indicators"].update(advanced)
        else:
            result["advanced_indicators"] = advanced
        
        if not is_forex:
            vol = run_quiet(get_volume_indicators_analysis, df)
            if "analysis" in vol:
                result["volume_analysis"] = vol["analysis"]
        else:
            result["volume_analysis"] = {"note": "外匯市場無成交量數據，跳過成交量分析"}
    except Exception as e:
        result["advanced_indicators_error"] = str(e)
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: main.py <command> [ticker] [period]"}))
        sys.exit(1)

    command = sys.argv[1]
    ticker = sys.argv[2] if len(sys.argv) > 2 else None
    period = sys.argv[3] if len(sys.argv) > 3 else "365d"

    cmd_aliases = {
        "get_indicators": "indicators",
        "get_momentum": "momentum",
        "get_price": "price",
        "list_indicators": "list",
    }
    cmd = cmd_aliases.get(command, command)

    try:
        result: dict = {}

        if cmd == "indicators":
            if not ticker:
                result = {"error": "ticker required"}
            else:
                result = get_all_indicators(ticker, period)

        elif cmd == "momentum":
            result = run_quiet(momentum_stock_score, ticker, time_period=period)

        elif cmd == "price":
            result = run_quiet(momentum_stock_score, ticker, time_period="5d")

        elif cmd == "combined":
            tech = get_all_indicators(ticker, period)
            mom = run_quiet(momentum_stock_score, ticker, time_period=period)
            result = {
                "ticker": ticker,
                "analysis_type": "comprehensive",
                "technical_indicators": tech.get("indicators", {}),
                "momentum": {
                    "score": mom.get("momentum_score"),
                    "signal": mom.get("signal"),
                    "trend": mom.get("trend"),
                    "confidence": mom.get("confidence"),
                },
                "current_price": mom.get("current_price"),
                "company_name": mom.get("company_name"),
                "timestamp": mom.get("timestamp"),
                "volume_analysis": tech.get("volume_analysis", {}),
            }

        elif cmd == "volume":
            if ticker and is_forex_ticker(ticker):
                result = {
                    "ticker": ticker.upper(),
                    "note": "外匯市場無成交量數據，跳過成交量分析"
                }
            else:
                df = run_quiet(get_stock_data, ticker, period)
                vol = run_quiet(get_volume_indicators_analysis, df)
                result = {
                    "ticker": ticker,
                    "volume_indicators": {
                        k: str(v.iloc[-1]) if hasattr(v, "iloc") else v
                        for k, v in vol.items() if k != "analysis"
                    },
                    "volume_analysis": vol.get("analysis", {}),
                }

        elif cmd == "trend":
            df = run_quiet(get_stock_data, ticker, period)
            result = {
                "ticker": ticker,
                "trend_indicators": {
                    "Parabolic_SAR": calc_advanced(df, "Parabolic_SAR"),
                    "Ichimoku": calc_advanced(df, "Ichimoku_Cloud"),
                    "TRIX": calc_advanced(df, "TRIX"),
                },
            }

        elif cmd == "list":
            result = {
                "standard_indicators": STANDARD_INDICATORS,
                "advanced_indicators": ADVANCED_INDICATORS,
                "total_count": len(ALL_INDICATORS),
            }

        elif cmd == "health":
            # Quick sanity check without network call
            result = {
                "status": "ok",
                "tools_path": str(Path(__file__).parent / "tools"),
                "tiingo_key_set": bool(os.getenv("TIINGO_API_KEY")),
                "available_commands": ["indicators", "momentum", "price", "combined", "volume", "trend", "list"],
            }

        else:
            result = {"error": f"Unknown command: {command}"}

        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        sys.stdout.flush()

    except Exception as e:
        print(json.dumps({"error": "Execution failed", "details": str(e)}, ensure_ascii=False))
        sys.stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
