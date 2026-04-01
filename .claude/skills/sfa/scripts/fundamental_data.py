#!/usr/bin/env python3
"""
Stock Fundamental Analyzer - Tiingo API Bridge
連接 Claude Code skill 到 Tiingo Fundamentals API

使用說明:
    python3 fundamental_data.py get_fundamental_data AAPL
    python3 fundamental_data.py get_financial_statements MSFT income quarterly
    python3 fundamental_data.py compare_fundamentals AAPL MSFT GOOGL

Note: 需要 TIINGO_API_KEY 環境變數。獲取免費 API key:
    https://www.tiingo.com/
"""

# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "requests>=2.28.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

import sys
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Try to find .env file in project root
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent  # Go up to Obsidian root
    env_file = project_root / '.env'

    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded .env from {env_file}", file=sys.stderr)
    else:
        # Try loading from current directory or parent directories
        load_dotenv()
except ImportError:
    print("提示: 安裝 python-dotenv 以自動讀取 .env 文件", file=sys.stderr)
    print("pip install python-dotenv", file=sys.stderr)

# Tiingo API configuration
TIINGO_BASE_URL = "https://api.tiingo.com/tiingo"
TIINGO_API_KEY = os.environ.get("TIINGO_API_KEY")

if not TIINGO_API_KEY:
    print("警告: TIINGO_API_KEY 環境變數未設置", file=sys.stderr)
    print("請在 .env 文件中添加: TIINGO_API_KEY=your_api_key", file=sys.stderr)
    print("或設置環境變數: export TIINGO_API_KEY='your_api_key'", file=sys.stderr)


def call_tiingo_api(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    調用 Tiingo API

    Args:
        endpoint: API endpoint (e.g., '/fundamentals/AAPL/daily')
        params: Query parameters

    Returns:
        API response as dictionary
    """
    if not TIINGO_API_KEY:
        return {"error": "TIINGO_API_KEY not set in environment"}

    url = f"{TIINGO_BASE_URL}{endpoint}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}'
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return {"error": "Unauthorized - check your TIINGO_API_KEY"}
        elif response.status_code == 404:
            return {"error": f"Data not found for endpoint: {endpoint}"}
        else:
            return {"error": f"HTTP {response.status_code}: {str(e)}"}
    except requests.exceptions.Timeout:
        return {"error": "Request timeout - Tiingo API not responding"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response from API"}


def get_fundamental_data(symbol: str) -> Dict[str, Any]:
    """
    獲取股票的基本面數據概覽

    Args:
        symbol: 股票代碼 (e.g., AAPL, MSFT)

    Returns:
        包含所有關鍵基本面指標的字典
    """
    symbol = symbol.upper()

    # 獲取最新的每日基本面數據
    endpoint = f"/fundamentals/{symbol}/daily"
    params = {
        'startDate': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    }

    data = call_tiingo_api(endpoint, params)

    if "error" in data:
        return data

    if not data or len(data) == 0:
        return {"error": f"No fundamental data available for {symbol}"}

    # 獲取最新的數據點
    latest = data[0] if isinstance(data, list) else data

    # 提取關鍵指標
    result = {
        "ticker": symbol,
        "timestamp": latest.get("date", ""),
        "valuation": {
            "market_cap": latest.get("marketCap"),
            "enterprise_value": latest.get("enterpriseVal"),
            "pe_ratio": latest.get("peRatio"),
            "pb_ratio": latest.get("pbRatio"),
            "ps_ratio": latest.get("priceToSalesRatio"),
        },
        "profitability": {
            "roe": latest.get("roe"),
            "roa": latest.get("roa"),
            "gross_margin": latest.get("grossMargin"),
            "operating_margin": latest.get("operatingMargin"),
            "profit_margin": latest.get("profitMargin"),
        },
        "financial_health": {
            "debt_to_equity": latest.get("debtToEquity"),
            "current_ratio": latest.get("currentRatio"),
            "quick_ratio": latest.get("quickRatio"),
        },
        "per_share": {
            "eps": latest.get("eps"),
            "book_value_per_share": latest.get("bookValuePerShare"),
            "revenue_per_share": latest.get("revenuePerShare"),
        },
        "dividend": {
            "yield": latest.get("dividendYield"),
        }
    }

    # 計算基本面分數 (0-100)
    score = calculate_fundamental_score(result)
    result["fundamental_score"] = score
    result["overall_signal"] = get_signal_from_score(score)

    return result


def get_financial_statements(
    symbol: str,
    statement_type: str = "income",
    frequency: str = "quarterly"
) -> Dict[str, Any]:
    """
    獲取財務報表

    Args:
        symbol: 股票代碼
        statement_type: 報表類型 ('income', 'balance', 'cash')
        frequency: 頻率 ('quarterly', 'annual')

    Returns:
        財務報表數據
    """
    symbol = symbol.upper()
    statement_type = statement_type.lower()
    frequency = frequency.lower()

    # 映射報表類型到 API endpoint
    statement_map = {
        "income": "incomeStatement",
        "balance": "balanceSheet",
        "cash": "cashFlow"
    }

    if statement_type not in statement_map:
        return {
            "error": f"Invalid statement type: {statement_type}. Use 'income', 'balance', or 'cash'"
        }

    endpoint = f"/fundamentals/{symbol}/statements"
    params = {}

    data = call_tiingo_api(endpoint, params)

    if "error" in data:
        return data

    if not data or len(data) == 0:
        return {"error": f"No financial statements available for {symbol}"}

    # 過濾出指定頻率的數據
    freq_key = "quarter" if frequency == "quarterly" else "year"

    result = {
        "ticker": symbol,
        "statement_type": statement_type,
        "frequency": frequency,
        "statements": []
    }

    # 解析並返回報表數據
    for item in data:
        if freq_key in item:
            statement_data = item.get(statement_map[statement_type], {})
            result["statements"].append({
                "period": item.get("date"),
                "data": statement_data
            })

    # 限制返回數量 (quarterly 8個, annual 5個)
    limit = 8 if frequency == "quarterly" else 5
    result["statements"] = result["statements"][:limit]

    return result


def get_valuation_metrics(symbol: str) -> Dict[str, Any]:
    """
    獲取估值指標

    Args:
        symbol: 股票代碼

    Returns:
        估值指標和信號
    """
    # 使用 get_fundamental_data 獲取基本數據
    data = get_fundamental_data(symbol)

    if "error" in data:
        return data

    valuation = data.get("valuation", {})
    profitability = data.get("profitability", {})

    # 計算額外的估值指標
    pe = valuation.get("pe_ratio")
    roe = profitability.get("roe")

    # 估算 PEG ratio (需要成長率，這裡簡化處理)
    peg_ratio = None
    if pe and roe:
        # 簡化: 使用 ROE 作為成長代理
        peg_ratio = pe / roe if roe > 0 else None

    result = {
        "ticker": symbol,
        "timestamp": data.get("timestamp"),
        "valuation_metrics": {
            "pe_ratio": pe,
            "peg_ratio": peg_ratio,
            "pb_ratio": valuation.get("pb_ratio"),
            "ps_ratio": valuation.get("ps_ratio"),
            "market_cap": valuation.get("market_cap"),
            "enterprise_value": valuation.get("enterprise_value"),
        },
        "interpretation": interpret_valuation(valuation, peg_ratio),
        "signal": get_valuation_signal(valuation, peg_ratio)
    }

    return result


def get_growth_metrics(symbol: str) -> Dict[str, Any]:
    """
    獲取成長指標

    Args:
        symbol: 股票代碼

    Returns:
        營收和盈利成長率
    """
    symbol = symbol.upper()

    # 獲取歷史數據來計算成長率
    endpoint = f"/fundamentals/{symbol}/daily"
    params = {
        'startDate': (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')  # 2 years
    }

    data = call_tiingo_api(endpoint, params)

    if "error" in data:
        return data

    if not data or len(data) < 2:
        return {"error": f"Insufficient data to calculate growth for {symbol}"}

    # 計算 YoY 成長率
    latest = data[0]
    year_ago = data[-1] if len(data) > 365 else data[-1]

    result = {
        "ticker": symbol,
        "timestamp": latest.get("date"),
        "growth_metrics": {
            "revenue_latest": latest.get("revenue"),
            "revenue_year_ago": year_ago.get("revenue"),
            "revenue_growth_yoy": calculate_growth_rate(
                year_ago.get("revenue"),
                latest.get("revenue")
            ),
            "eps_latest": latest.get("eps"),
            "eps_year_ago": year_ago.get("eps"),
            "earnings_growth_yoy": calculate_growth_rate(
                year_ago.get("eps"),
                latest.get("eps")
            ),
        },
        "growth_rating": rate_growth(
            calculate_growth_rate(year_ago.get("revenue"), latest.get("revenue"))
        )
    }

    return result


def get_dividend_info(symbol: str) -> Dict[str, Any]:
    """
    獲取股息資訊

    Args:
        symbol: 股票代碼

    Returns:
        股息率和歷史
    """
    data = get_fundamental_data(symbol)

    if "error" in data:
        return data

    dividend_yield = data.get("dividend", {}).get("yield")

    result = {
        "ticker": symbol,
        "timestamp": data.get("timestamp"),
        "dividend": {
            "yield": dividend_yield,
            "yield_percentage": f"{dividend_yield * 100:.2f}%" if dividend_yield else None,
        },
        "interpretation": interpret_dividend(dividend_yield)
    }

    return result


def get_financial_health(symbol: str) -> Dict[str, Any]:
    """
    獲取財務健康指標

    Args:
        symbol: 股票代碼

    Returns:
        債務和流動性比率
    """
    data = get_fundamental_data(symbol)

    if "error" in data:
        return data

    health = data.get("financial_health", {})

    result = {
        "ticker": symbol,
        "timestamp": data.get("timestamp"),
        "financial_health": {
            "debt_to_equity": health.get("debt_to_equity"),
            "current_ratio": health.get("current_ratio"),
            "quick_ratio": health.get("quick_ratio"),
        },
        "health_score": calculate_health_score(health),
        "interpretation": interpret_financial_health(health)
    }

    return result


def get_profitability_metrics(symbol: str) -> Dict[str, Any]:
    """
    獲取獲利能力指標

    Args:
        symbol: 股票代碼

    Returns:
        ROE, ROA, 利潤率等
    """
    data = get_fundamental_data(symbol)

    if "error" in data:
        return data

    profitability = data.get("profitability", {})

    result = {
        "ticker": symbol,
        "timestamp": data.get("timestamp"),
        "profitability": profitability,
        "profitability_rating": rate_profitability(profitability),
        "interpretation": interpret_profitability(profitability)
    }

    return result


def get_company_overview(symbol: str) -> Dict[str, Any]:
    """
    獲取公司概況

    Args:
        symbol: 股票代碼

    Returns:
        公司元數據和業務資訊
    """
    symbol = symbol.upper()

    # 獲取公司元數據
    endpoint = f"/fundamentals/{symbol}/meta"

    data = call_tiingo_api(endpoint)

    if "error" in data:
        return data

    result = {
        "ticker": symbol,
        "company_name": data.get("name"),
        "description": data.get("description"),
        "sector": data.get("sector"),
        "industry": data.get("industry"),
        "exchange": data.get("exchange"),
        "currency": data.get("currency"),
        "employees": data.get("employees"),
        "headquarters": data.get("location"),
        "website": data.get("website"),
    }

    return result


def compare_fundamentals(symbols: List[str]) -> Dict[str, Any]:
    """
    比較多檔股票的基本面

    Args:
        symbols: 股票代碼列表

    Returns:
        並排比較結果
    """
    comparison = {
        "symbols": symbols,
        "timestamp": datetime.now().isoformat(),
        "comparison": {}
    }

    # 獲取每檔股票的基本面數據
    for symbol in symbols:
        data = get_fundamental_data(symbol)
        if "error" not in data:
            comparison["comparison"][symbol] = {
                "valuation": data.get("valuation"),
                "profitability": data.get("profitability"),
                "financial_health": data.get("financial_health"),
                "fundamental_score": data.get("fundamental_score"),
                "signal": data.get("overall_signal")
            }

    # 添加排名
    comparison["rankings"] = rank_stocks(comparison["comparison"])

    return comparison


def get_combined_fundamental_analysis(symbol: str) -> Dict[str, Any]:
    """
    獲取完整的基本面分析報告

    Args:
        symbol: 股票代碼

    Returns:
        綜合基本面分析
    """
    result = {
        "ticker": symbol,
        "timestamp": datetime.now().isoformat(),
        "analysis": {}
    }

    # 獲取所有分析
    result["analysis"]["fundamental_data"] = get_fundamental_data(symbol)
    result["analysis"]["valuation"] = get_valuation_metrics(symbol)
    result["analysis"]["growth"] = get_growth_metrics(symbol)
    result["analysis"]["dividend"] = get_dividend_info(symbol)
    result["analysis"]["financial_health"] = get_financial_health(symbol)
    result["analysis"]["profitability"] = get_profitability_metrics(symbol)

    # 計算總體評分和建議
    overall_score = result["analysis"]["fundamental_data"].get("fundamental_score", 50)
    result["overall_score"] = overall_score
    result["recommendation"] = get_investment_recommendation(overall_score, result["analysis"])

    return result


# Helper functions

def calculate_growth_rate(old_value: Optional[float], new_value: Optional[float]) -> Optional[float]:
    """計算成長率 (%)"""
    if old_value is None or new_value is None or old_value == 0:
        return None
    return ((new_value - old_value) / abs(old_value)) * 100


def calculate_fundamental_score(data: Dict[str, Any]) -> int:
    """計算基本面分數 (0-100)"""
    score = 50  # 基準分數

    valuation = data.get("valuation", {})
    profitability = data.get("profitability", {})
    health = data.get("financial_health", {})

    # 估值分數 (PE ratio)
    pe = valuation.get("pe_ratio")
    if pe:
        if pe < 15:
            score += 10
        elif pe > 30:
            score -= 10

    # 獲利能力分數 (ROE)
    roe = profitability.get("roe")
    if roe:
        if roe > 15:
            score += 15
        elif roe < 10:
            score -= 10

    # 利潤率分數
    margin = profitability.get("profit_margin")
    if margin:
        if margin > 0.2:  # 20%
            score += 10
        elif margin < 0.05:  # 5%
            score -= 10

    # 財務健康分數
    debt_to_equity = health.get("debt_to_equity")
    if debt_to_equity is not None:
        if debt_to_equity < 0.5:
            score += 10
        elif debt_to_equity > 2.0:
            score -= 15

    current_ratio = health.get("current_ratio")
    if current_ratio:
        if current_ratio > 2:
            score += 5
        elif current_ratio < 1:
            score -= 10

    return max(0, min(100, score))


def calculate_health_score(health: Dict[str, Any]) -> int:
    """計算財務健康分數 (0-100)"""
    score = 50

    debt_to_equity = health.get("debt_to_equity")
    if debt_to_equity is not None:
        if debt_to_equity < 0.5:
            score += 25
        elif debt_to_equity < 1.0:
            score += 10
        elif debt_to_equity > 2.0:
            score -= 20

    current_ratio = health.get("current_ratio")
    if current_ratio:
        if current_ratio > 2:
            score += 15
        elif current_ratio > 1.5:
            score += 5
        elif current_ratio < 1:
            score -= 20

    quick_ratio = health.get("quick_ratio")
    if quick_ratio:
        if quick_ratio > 1.5:
            score += 10
        elif quick_ratio < 0.5:
            score -= 10

    return max(0, min(100, score))


def get_signal_from_score(score: int) -> str:
    """根據分數返回投資信號"""
    if score >= 80:
        return "STRONG BUY"
    elif score >= 65:
        return "BUY"
    elif score >= 45:
        return "HOLD"
    elif score >= 30:
        return "SELL"
    else:
        return "STRONG SELL"


def interpret_valuation(valuation: Dict[str, Any], peg_ratio: Optional[float]) -> str:
    """解釋估值指標"""
    pe = valuation.get("pe_ratio")

    if not pe:
        return "Insufficient data for valuation assessment"

    if pe < 15:
        return "Undervalued - PE ratio below 15 suggests the stock may be cheap"
    elif pe > 30:
        if peg_ratio and peg_ratio < 1.5:
            return "High PE but justified by growth (low PEG)"
        return "Potentially overvalued - High PE ratio suggests premium pricing"
    else:
        return "Fair valuation - PE ratio in reasonable range"


def get_valuation_signal(valuation: Dict[str, Any], peg_ratio: Optional[float]) -> str:
    """獲取估值信號"""
    pe = valuation.get("pe_ratio")

    if not pe:
        return "HOLD"

    if pe < 15:
        return "BUY"
    elif pe > 30:
        if peg_ratio and peg_ratio < 1.0:
            return "HOLD"
        return "SELL"
    else:
        return "HOLD"


def rate_growth(growth_rate: Optional[float]) -> str:
    """評級成長率"""
    if growth_rate is None:
        return "N/A"

    if growth_rate > 20:
        return "HIGH GROWTH"
    elif growth_rate > 10:
        return "MODERATE GROWTH"
    elif growth_rate > 0:
        return "SLOW GROWTH"
    else:
        return "DECLINING"


def interpret_dividend(dividend_yield: Optional[float]) -> str:
    """解釋股息率"""
    if not dividend_yield:
        return "No dividend or data not available"

    yield_pct = dividend_yield * 100

    if yield_pct > 5:
        return "High dividend yield - May indicate value or high risk"
    elif yield_pct > 2:
        return "Moderate dividend yield - Decent income component"
    elif yield_pct > 0:
        return "Low dividend yield - Growth-focused company"
    else:
        return "No dividend"


def interpret_financial_health(health: Dict[str, Any]) -> str:
    """解釋財務健康"""
    debt_to_equity = health.get("debt_to_equity")
    current_ratio = health.get("current_ratio")

    interpretations = []

    if debt_to_equity is not None:
        if debt_to_equity < 0.5:
            interpretations.append("Conservative debt levels")
        elif debt_to_equity > 2.0:
            interpretations.append("High leverage - monitor debt carefully")
        else:
            interpretations.append("Moderate debt levels")

    if current_ratio:
        if current_ratio > 2:
            interpretations.append("Strong liquidity position")
        elif current_ratio < 1:
            interpretations.append("Liquidity concerns")
        else:
            interpretations.append("Adequate liquidity")

    return "; ".join(interpretations) if interpretations else "Insufficient data"


def rate_profitability(profitability: Dict[str, Any]) -> str:
    """評級獲利能力"""
    roe = profitability.get("roe")
    margin = profitability.get("profit_margin")

    if not roe:
        return "N/A"

    if roe > 20 and margin and margin > 0.15:
        return "EXCELLENT"
    elif roe > 15:
        return "GOOD"
    elif roe > 10:
        return "AVERAGE"
    else:
        return "BELOW AVERAGE"


def interpret_profitability(profitability: Dict[str, Any]) -> str:
    """解釋獲利能力"""
    roe = profitability.get("roe")
    margin = profitability.get("profit_margin")

    interpretations = []

    if roe:
        if roe > 15:
            interpretations.append(f"Strong ROE of {roe:.1f}%")
        elif roe < 10:
            interpretations.append(f"Weak ROE of {roe:.1f}%")

    if margin:
        margin_pct = margin * 100
        if margin_pct > 20:
            interpretations.append(f"Excellent profit margin of {margin_pct:.1f}%")
        elif margin_pct < 5:
            interpretations.append(f"Low profit margin of {margin_pct:.1f}%")

    return "; ".join(interpretations) if interpretations else "Insufficient data"


def rank_stocks(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """對股票進行排名"""
    rankings = {
        "by_score": [],
        "by_valuation": [],
        "by_profitability": []
    }

    for symbol, data in comparison.items():
        score = data.get("fundamental_score", 0)
        pe = data.get("valuation", {}).get("pe_ratio")
        roe = data.get("profitability", {}).get("roe")

        rankings["by_score"].append((symbol, score))
        if pe:
            rankings["by_valuation"].append((symbol, pe))
        if roe:
            rankings["by_profitability"].append((symbol, roe))

    # 排序
    rankings["by_score"].sort(key=lambda x: x[1], reverse=True)
    rankings["by_valuation"].sort(key=lambda x: x[1])  # Lower PE is better
    rankings["by_profitability"].sort(key=lambda x: x[1], reverse=True)

    return rankings


def get_investment_recommendation(score: int, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """獲取投資建議"""
    signal = get_signal_from_score(score)

    strengths = []
    weaknesses = []

    # 分析優勢和劣勢
    profitability = analysis.get("profitability", {}).get("profitability", {})
    if profitability.get("roe", 0) > 15:
        strengths.append("Strong return on equity")
    elif profitability.get("roe", 0) < 10:
        weaknesses.append("Weak return on equity")

    health = analysis.get("financial_health", {}).get("financial_health", {})
    if health.get("debt_to_equity", 999) < 0.5:
        strengths.append("Conservative debt levels")
    elif health.get("debt_to_equity", 0) > 2.0:
        weaknesses.append("High leverage")

    return {
        "signal": signal,
        "score": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "summary": f"{signal} with fundamental score of {score}/100"
    }


def print_help():
    """顯示幫助資訊"""
    help_text = """
Stock Fundamental Analyzer - Tiingo API Bridge

用法:
  python3 fundamental_data.py <command> [symbol] [options]

可用指令:
  get_fundamental_data <symbol>              獲取基本面數據概覽
  get_financial_statements <symbol> <type> <freq>  獲取財務報表
    - type: income, balance, cash
    - freq: quarterly, annual
  get_valuation_metrics <symbol>             獲取估值指標
  get_growth_metrics <symbol>                獲取成長指標
  get_dividend_info <symbol>                 獲取股息資訊
  get_financial_health <symbol>              獲取財務健康指標
  get_profitability_metrics <symbol>         獲取獲利能力指標
  get_company_overview <symbol>              獲取公司概況
  compare_fundamentals <sym1> <sym2> ...     比較多檔股票
  get_combined_fundamental_analysis <symbol> 綜合分析

例:
  python3 fundamental_data.py get_fundamental_data AAPL
  python3 fundamental_data.py get_financial_statements MSFT income quarterly
  python3 fundamental_data.py compare_fundamentals AAPL MSFT GOOGL
  python3 fundamental_data.py get_combined_fundamental_analysis TSLA

Note:
  - 需要設置環境變數: export TIINGO_API_KEY='your_api_key'
  - 免費註冊: https://www.tiingo.com/
    """
    print(help_text)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        return

    command = sys.argv[1]

    try:
        if command == 'get_fundamental_data':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_fundamental_data(symbol)

        elif command == 'get_financial_statements':
            if len(sys.argv) < 5:
                print("用法: get_financial_statements <symbol> <type> <freq>", file=sys.stderr)
                print("type: income, balance, cash", file=sys.stderr)
                print("freq: quarterly, annual", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            stmt_type = sys.argv[3]
            frequency = sys.argv[4]
            result = get_financial_statements(symbol, stmt_type, frequency)

        elif command == 'get_valuation_metrics':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_valuation_metrics(symbol)

        elif command == 'get_growth_metrics':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_growth_metrics(symbol)

        elif command == 'get_dividend_info':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_dividend_info(symbol)

        elif command == 'get_financial_health':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_financial_health(symbol)

        elif command == 'get_profitability_metrics':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_profitability_metrics(symbol)

        elif command == 'get_company_overview':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_company_overview(symbol)

        elif command == 'compare_fundamentals':
            if len(sys.argv) < 4:
                print("需要至少 2 個股票代碼進行比較", file=sys.stderr)
                sys.exit(1)
            symbols = [s.upper() for s in sys.argv[2:]]
            result = compare_fundamentals(symbols)

        elif command == 'get_combined_fundamental_analysis':
            if len(sys.argv) < 3:
                print("需要指定股票代碼", file=sys.stderr)
                sys.exit(1)
            symbol = sys.argv[2]
            result = get_combined_fundamental_analysis(symbol)

        else:
            print(f"未知指令: {command}", file=sys.stderr)
            print_help()
            sys.exit(1)

        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "command": command
        }, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
