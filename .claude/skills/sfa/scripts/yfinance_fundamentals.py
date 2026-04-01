#!/usr/bin/env python3
"""
YFinance Fundamental Data Extractor
替代 Tiingo API 的免費方案，支援所有美股基本面數據

使用說明:
    python3 yfinance_fundamentals.py get_fundamental_data AAPL
    python3 yfinance_fundamentals.py get_multiple_tickers GOOG AMZN NVDA RDW ASTS RKLB
"""

import sys
import json
import yfinance as yf
from typing import Any, Dict, List, Optional
from datetime import datetime
import argparse

def get_fundamental_data(symbol: str) -> Dict[str, Any]:
    """
    使用 yfinance 獲取基本面數據

    Args:
        symbol: 股票代碼

    Returns:
        基本面數據字典
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # 處理 None 值和單位轉換
        market_cap = info.get('marketCap')
        if market_cap:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap/1e9:.2f}B"
            elif market_cap >= 1e6:
                market_cap_str = f"${market_cap/1e6:.2f}M"
            else:
                market_cap_str = f"${market_cap:,.0f}"
        else:
            market_cap_str = "N/A"

        # 計算財務健康評分
        health_score = 0
        if info.get('currentRatio', 0) > 2:
            health_score += 25
        elif info.get('currentRatio', 0) > 1:
            health_score += 15

        if info.get('debtToEquity', 100) < 0.5:
            health_score += 25
        elif info.get('debtToEquity', 100) < 1.5:
            health_score += 15

        if info.get('profitMargins', 0) > 0.2:
            health_score += 25
        elif info.get('profitMargins', 0) > 0.1:
            health_score += 15

        if info.get('returnOnEquity', 0) > 0.15:
            health_score += 25
        elif info.get('returnOnEquity', 0) > 0.1:
            health_score += 15

        # 計算綜合評級
        pe_ratio = info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        revenue_growth = info.get('revenueGrowth', 0)

        signal = "HOLD"
        score = 50

        if pe_ratio and pe_ratio > 0:
            if pe_ratio < 15 and revenue_growth > 0.1:
                signal = "BUY"
                score = 75
            elif pe_ratio > 40 and revenue_growth < 0.1:
                signal = "SELL"
                score = 25
            elif pe_ratio < 25 and revenue_growth > 0.15:
                signal = "BUY"
                score = 70

        if pb_ratio and pb_ratio > 0:
            if pb_ratio < 1.5 and pe_ratio and pe_ratio < 20:
                score += 10

        return {
            "ticker": symbol,
            "company_name": info.get('shortName', 'N/A'),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "timestamp": datetime.now().isoformat(),
            "valuation": {
                "market_cap": market_cap_str,
                "market_cap_numeric": market_cap,
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "ps_ratio": info.get('priceToSalesTrailing12Months'),
                "enterprise_value": info.get('enterpriseValue'),
                "ev_ebitda": info.get('enterpriseToEbitda')
            },
            "profitability": {
                "roe": info.get('returnOnEquity'),
                "roa": info.get('returnOnAssets'),
                "gross_margin": info.get('grossMargins'),
                "operating_margin": info.get('operatingMargins'),
                "profit_margin": info.get('profitMargins'),
                "rating": "EXCELLENT" if info.get('profitMargins', 0) > 0.2 else
                         "GOOD" if info.get('profitMargins', 0) > 0.1 else
                         "AVERAGE" if info.get('profitMargins', 0) > 0.05 else "WEAK"
            },
            "financial_health": {
                "debt_to_equity": info.get('debtToEquity'),
                "current_ratio": info.get('currentRatio'),
                "quick_ratio": info.get('quickRatio'),
                "interest_coverage": info.get('interestCoverage'),
                "health_score": health_score,
                "rating": "STRONG" if health_score > 75 else
                         "GOOD" if health_score > 50 else
                         "WEAK" if health_score > 25 else "POOR"
            },
            "growth": {
                "revenue_growth_yoy": info.get('revenueGrowth'),
                "earnings_growth_yoy": info.get('earningsGrowth'),
                "earnings_quarterly_growth_yoy": info.get('earningsQuarterlyGrowth'),
                "revenue_growth_5y": info.get('revenueGrowthAnnual'),
                "growth_score": min(100, max(0, (revenue_growth * 200 + info.get('earningsGrowth', 0) * 100)))
            },
            "dividend": {
                "yield": info.get('dividendYield'),
                "payout_ratio": info.get('payoutRatio'),
                "dividend_rate": info.get('dividendRate')
            },
            "overall_signal": signal,
            "fundamental_score": score
        }

    except Exception as e:
        return {
            "ticker": symbol,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def get_multiple_tickers(symbols: List[str]) -> Dict[str, Any]:
    """
    獲取多個股票的基本面數據

    Args:
        symbols: 股票代碼列表

    Returns:
        包含所有股票數據的字典
    """
    results = {}

    for symbol in symbols:
        print(f"獲取 {symbol} 數據...", file=sys.stderr)
        results[symbol] = get_fundamental_data(symbol)

    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(symbols),
        "data": results
    }

def format_table_output(symbols: List[str]) -> str:
    """
    格式化輸出為表格形式

    Args:
        symbols: 股票代碼列表

    Returns:
        格式化的表格字符串
    """
    # 獲取數據
    results = get_multiple_tickers(symbols)

    # 表格標題
    header = f"{'股票代碼':<8} {'公司名稱':<30} {'市值':<12} {'PE比率':<8} {'PB比率':<8} {'營收成長':<10} {'ROE':<8} {'評級':<6} {'信號':<6}"
    separator = "-" * len(header)

    lines = [header, separator]

    for symbol, data in results["data"].items():
        if "error" in data:
            lines.append(f"{symbol:<8} {'錯誤':<30} {'N/A':<12} {'N/A':<8} {'N/A':<8} {'N/A':<10} {'N/A':<8} {'N/A':<6} {'ERROR':<6}")
        else:
            company_name = data["company_name"][:27] + "..." if len(data["company_name"]) > 30 else data["company_name"]
            market_cap = data["valuation"]["market_cap"]
            pe = f"{data['valuation']['pe_ratio']:.1f}" if data['valuation']['pe_ratio'] else "N/A"
            pb = f"{data['valuation']['pb_ratio']:.1f}" if data['valuation']['pb_ratio'] else "N/A"
            revenue_growth = f"{data['growth']['revenue_growth_yoy']*100:.1f}%" if data['growth']['revenue_growth_yoy'] else "N/A"
            roe = f"{data['profitability']['roe']*100:.1f}%" if data['profitability']['roe'] else "N/A"
            rating = data["overall_signal"]

            lines.append(f"{symbol:<8} {company_name:<30} {market_cap:<12} {pe:<8} {pb:<8} {revenue_growth:<10} {roe:<8} {rating:<6} {rating:<6}")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="使用 yfinance 獲取股票基本面數據")
    parser.add_argument("command", choices=["get_fundamental_data", "get_multiple_tickers", "table"])
    parser.add_argument("symbols", nargs="+", help="股票代碼")
    parser.add_argument("--format", choices=["json", "table"], default="json", help="輸出格式")

    args = parser.parse_args()

    if args.command == "get_fundamental_data" and len(args.symbols) == 1:
        result = get_fundamental_data(args.symbols[0])
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    elif args.command == "get_multiple_tickers":
        result = get_multiple_tickers(args.symbols)
        if args.format == "table":
            print(format_table_output(args.symbols))
        else:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    elif args.command == "table":
        print(format_table_output(args.symbols))

    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()