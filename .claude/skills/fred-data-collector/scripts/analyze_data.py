#!/usr/bin/env python3
"""
Druckenmiller-style Economic Analysis
Analyzes collected FRED data for macro trading insights
"""

import os
import sys
import datetime
import pandas as pd

# Load environment
cwd = os.getcwd()
env_file = os.path.join(cwd, '.env')

if os.path.exists(env_file):
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")

from fredapi import Fred

def calculate_cpi_yoy():
    """Calculate CPI Year-over-Year inflation率"""
    cpi_file = "datas/fred/economic/CPIAUCSL_history.csv"
    if os.path.exists(cpi_file):
        cpi = pd.read_csv(cpi_file, index_col=0, parse_dates=True)
        check_staleness(cpi, "CPI")
        cpi_yoy = cpi.pct_change(12) * 100  # 12 months for YoY
        latest = cpi_yoy.iloc[-1].iloc[0]
        return {
            'cpi_yoy': latest,
            'date': cpi_yoy.index[-1].strftime('%Y-%m-%d')
        }
    return None

def check_staleness(df, name, threshold_days=45):
    """檢查數據是否過期"""
    last_date = pd.to_datetime(df.index[-1])
    days_diff = (datetime.datetime.now() - last_date).days

    status = "✅"
    if days_diff > threshold_days:
        status = "🔴 STALE (過期)"
        print(f"⚠️ WARNING: {name} data is {days_diff} days old! Last date: {last_date.date()}")

    return status, days_diff

def analyze_labour_market():
    """分析 labour market conditions"""
    unrate_file = "datas/fred/economic/UNRATE_history.csv"
    payems_file = "datas/fred/economic/PAYEMS_history.csv"

    analysis = {}

    if os.path.exists(unrate_file):
        unrate = pd.read_csv(unrate_file, index_col=0, parse_dates=True)
        check_staleness(unrate, "Unemployment Rate")
        current_unrate = unrate.iloc[-1].iloc[0]
        analysis['unemployment_rate'] = current_unrate
        analysis['unemployment_date'] = unrate.index[-1].strftime('%Y-%m-%d')

        # 最近3個月趨勢
        if len(unrate) >= 3:
            recent = unrate.tail(3)
            trend = '↑' if recent.iloc[-1].iloc[0] > recent.iloc[0].iloc[0] else '↓' if recent.iloc[-1].iloc[0] < recent.iloc[0].iloc[0] else '→'
            analysis['unemployment_trend'] = trend

    if os.path.exists(payems_file):
        payems = pd.read_csv(payems_file, index_col=0, parse_dates=True)

        # 加入檢查
        status, age = check_staleness(payems, "Non-Farm Payrolls")

        current_payems = payems.iloc[-1].iloc[0]
        analysis['nonfarm_payrolls'] = current_payems
        analysis['data_quality'] = status  # 將狀態加入報告

        # 計算最近兩個月嘅變化
        if len(payems) >= 2:
            payems_change = payems.iloc[-1].iloc[0] - payems.iloc[-2].iloc[0]
            analysis['payrolls_change'] = payems_change

    return analysis

def analyze_yield_curve():
    """分析收益率曲線形態"""
    rates_2y_file = "datas/fred/rates/DGS2_history.csv"
    rates_10y_file = "datas/fred/rates/DGS10_history.csv"

    analysis = {}

    if os.path.exists(rates_2y_file) and os.path.exists(rates_10y_file):
        rates_2y = pd.read_csv(rates_2y_file, index_col=0, parse_dates=True)
        rates_10y = pd.read_csv(rates_10y_file, index_col=0, parse_dates=True)

        latest_2y = rates_2y.iloc[-1].iloc[0]
        latest_10y = rates_10y.iloc[-1].iloc[0]
        spread = latest_10y - latest_2y

        analysis['treasury_2y'] = latest_2y
        analysis['treasury_10y'] = latest_10y
        analysis['yield_spread'] = spread
        analysis['yield_date'] = rates_10y.index[-1].strftime('%Y-%m-%d')

        # 判斷曲線形態
        if spread < 0:
            analysis['curve_status'] = 'INVERTED'
            analysis['curve_emoji'] = '🔴'
        elif spread < 0.5:
            analysis['curve_status'] = 'FLATTENING'
            analysis['curve_emoji'] = '🟡'
        else:
            analysis['curve_status'] = 'NORMAL'
            analysis['curve_emoji'] = '🟢'

    return analysis

def analyze_fed_policy():
    """分析 Fed 政策立場"""
    fed_funds_file = "datas/fred/rates/DFF_history.csv"

    if os.path.exists(fed_funds_file):
        fed_funds = pd.read_csv(fed_funds_file, index_col=0, parse_dates=True)
        current_rate = fed_funds.iloc[-1].iloc[0]
        return {
            'fed_funds_rate': current_rate,
            'fed_date': fed_funds.index[-1].strftime('%Y-%m-%d')
        }
    return None

def analyze_liquidity():
    """分析流動性狀況"""
    m2_file = "datas/fred/money/M2SL_history.csv"
    balance_sheet_file = "datas/fred/money/WALCL_history.csv"

    analysis = {}

    if os.path.exists(m2_file):
        m2 = pd.read_csv(m2_file, index_col=0, parse_dates=True)
        check_staleness(m2, "M2 Money Supply")
        current_m2 = m2.iloc[-1].iloc[0]
        analysis['m2_money'] = current_m2

        if len(m2) >= 12:
            m2_growth = ((current_m2 / m2.iloc[-12].iloc[0]) - 1) * 100
            analysis['m2_growth_yoy'] = m2_growth

    if os.path.exists(balance_sheet_file):
        balance_sheet = pd.read_csv(balance_sheet_file, index_col=0, parse_dates=True)
        check_staleness(balance_sheet, "Fed Balance Sheet", threshold_days=14)
        current_size = balance_sheet.iloc[-1].iloc[0]
        analysis['fed_balance_sheet'] = current_size

        if len(balance_sheet) >= 3:
            recent_change = current_size - balance_sheet.iloc[-3].iloc[0]
            analysis['fed_balance_change_3m'] = recent_change

    return analysis

def generate_druckenmiller_report():
    """生成 Druckenmiller 風格宏觀報告"""

    print("🚀 Generating Druckenmiller-style Macro Report...")
    print("="*70)

    # 收集所有分析
    cpi = calculate_cpi_yoy()
    labour = analyze_labour_market()
    yield_curve = analyze_yield_curve()
    fed_policy = analyze_fed_policy()
    liquidity = analyze_liquidity()

    # 生成報告
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report = []

    report.append(f"# Druckenmiller Style Macro Analysis")
    report.append(f"**Generated:** {timestamp}\n")
    report.append(f"**Framework:** Stanley Druckenmiller Macro Trading\n")

    # Check for data staleness to trigger "Shutdown Mode"
    is_data_stale = False
    if labour and 'data_quality' in labour and "STALE" in labour['data_quality']:
        is_data_stale = True

    if is_data_stale:
        report.append("⚠️ **CRITICAL WARNING: DATA BLACKOUT DETECTED**")
        report.append("由於政府停擺 (Government Shutdown) 或數據延遲，目前處於「數據真空期」。")
        report.append("傳統宏觀指標可能失效，建議轉向個股 Alpha。")
        report.append("")

    # 1. 流動性分析 (Druckenmiller 最重視)
    report.append("## 1. 流動性狀況 (Liquidity)🔴⚠️")
    report.append("\n### Fed 政策立場")
    if fed_policy:
        rate = fed_policy['fed_funds_rate']
        report.append(f"- **Fed Funds Rate:** {rate:.2f}%")
        if rate > 4.0:
            report.append("  - Fed 處於緊縮周期 ⚠️")
            report.append("  - 對風險資產不利")
        elif rate < 1.0:
            report.append("  - Fed 處於寬松周期 ✅")
            report.append("  - 流動性充裕")
        else:
            report.append("  - Fed 處於中性區間")

    report.append("\n### 貨幣供應")
    if 'm2_growth_yoy' in liquidity:
        m2_growth = liquidity['m2_growth_yoy']
        report.append(f"- **M2 YoY Growth:** {m2_growth:.1f}%")
        if m2_growth < 0:
            report.append("  - 貨幣供應收縮 🟡")
        elif m2_growth > 10:
            report.append("  - 貨幣供應快速增長 🔥")

    if 'fed_balance_change_3m' in liquidity:
        change = liquidity['fed_balance_change_3m']
        report.append(f"- **Fed Balance Sheet (3M change):** {change:,.0f}M")
        if change > 0:
            report.append("  - 正在擴表 (QE) ✅")
        else:
            report.append("  - 正在縮表 (QT) 🟡")

    # 2. 宏觀經濟狀況
    report.append("\n## 2. 宏觀經濟狀況 (Economic Growth)")

    report.append("\n### 通脹狀況")
    if cpi:
        inflation = cpi['cpi_yoy']
        report.append(f"- **CPI YoY:** {inflation:.1f}%")
        if inflation >= 5:
            report.append("  - 高通脹環境 🔴")
            report.append("  - Fab 需要繼續緊縮")
        elif inflation >= 3:
            report.append("  - 通脹高企 🟡")
        elif inflation >= 2:
            report.append("  - 通脹接近目標 🟢")
        else:
            report.append("  - 通脹受控 ✅")

    # 3. Labour Market
    report.append("\n### 勞動市場狀況")
    if labour:
        unrate = labour['unemployment_rate']
        report.append(f"- **Unemployment Rate:** {unrate:.1f}%")

        if 'unemployment_trend' in labour:
            trend = labour['unemployment_trend']
            report.append(f"  - 趨勢: {trend}")

        if 'payrolls_change' in labour:
            pay_change = labour['payrolls_change']
            report.append(f"- **Payrolls Change (M/M):** {pay_change:,.0f}k (Thousands)")
            if pay_change > 300000:
                report.append("  - 勞動市場強勁 🟢")
            elif pay_change < 0:
                report.append("  - 勞動市場惡化 🔴")

    # 4. 收益率曲線 (Yield Curve) - 非常重要嘅衰退指標
    report.append("\n## 3. 收益率曲線 (Yield Curve)⚠️")
    if yield_curve:
        report.append(f"- **10Y-2Y Spread:** {yield_curve['yield_spread']:.2f}%")

        if yield_curve['curve_status'] == 'INVERTED':
            report.append(f"{yield_curve['curve_emoji']} Curve INVERTED - 12-18 months recession risk!")
            report.append("  - 預示經濟衰退可能")
            report.append("  - 歷史上準確率極高")
        elif yield_curve['curve_status'] == 'FLATTENING':
            report.append(f"{yield_curve['curve_emoji']} Curve Flattening - Watch for inversion!")
        else:
            report.append(f"{yield_curve['curve_emoji']} Curve NORMAL - No immediate recession signal")

    # 5. 整體評估
    report.append("\n## 4. 綜合評估 (Bottom Line + Conviction)")

    # 計算風險指標
    risk_signals = []

    if fed_policy and fed_policy['fed_funds_rate'] > 4.0:
        risk_signals.append("Fed 緊縮 🔴")

    if cpi and cpi['cpi_yoy'] > 3.0:
        risk_signals.append("通脹高企 🟡")

    if yield_curve and yield_curve['curve_status'] == 'INVERTED':
        risk_signals.append("收益率倒掛 🔴")

    if labour and 'payrolls_change' in labour:
        if labour['payrolls_change'] < 0:
            risk_signals.append("就業負增長 🔴")

    # 判斷整體狀況
    report.append("\n### 風險概況")
    risk_count = len(risk_signals)

    if risk_count >= 3:
        report.append("🟢 HIGH RISK ENVIRONMENT")
        report.append("- Multiple recession signals")
        report.append("- Risk-off positioning recommended")
        conviction = "High Conviction Short"
    elif risk_count >= 1:
        report.append("🟡 MODERATE RISK ENVIRONMENT")
        report.append("- Some warning signals")
        report.append("- Stay vigilant")
        conviction = "Neutral - Wait for Clarity"
    else:
        report.append("✅ LOW RISK ENVIRONMENT")
        report.append("- Risk-on positioning OK")
        conviction = "Moderate Conviction Long"

    # Override conviction if in Shutdown Mode
    if is_data_stale:
        conviction = "Long Innovation, Hedge Macro"
        report.append("\n> **SHUTDOWN ADJUSTMENT:**")
        report.append("> Data is stale due to Government Shutdown. Shifting to Stock Picking.")
        report.append("> **Focus:** Biotech & AI Application Layer (Natera, Insmed, Meta)")

    report.append(f"\n### 投資立場 (Conviction)")
    report.append(f"**{conviction}**")

    report.append(f"\n### 風險信號 (共 {risk_count}個)")
    for signal in risk_signals:
        report.append(f"- {signal}")

    # 6. 需要監察嘅關鍵指標
    report.append("\n## 5. 關鍵監察指標 (Key Things to Watch)")
    report.append("\n### 即將發布 (High Impact):")

    # NFP 發布時間 (通常每月第一個星期五)
    report.append("- **Non-Farm Payrolls** - Watch for < 100k or negative")
    report.append("- **CPI Data** - Any acceleration above 3%")
    report.append("- **Fed Meeting** - Dot plot and Powell comments")
    report.append("- **Initial Claims** - Trending above 250k")

    report.append("\n### 技術面確認:")
    report.append("- S&P 500 breaking below 200-day moving average")
    report.append("- Credit spreads widening (HY spreads > 500bp)")
    report.append("- VIX > 30 (panic level)")

    # 7. 風險管理
    report.append("\n## 6. 風險管理 (Risk Management)")
    report.append(f"\n**Position Sizing:** Based on {risk_count} risk signals")

    if risk_count >= 3:
        report.append("- Reduce equity exposure to 30-50%")
        report.append("- Increase cash/bonds allocation")
        report.append("- Consider short positions in cyclicals")
        report.append("- Use VIX calls for portfolio protection")
    elif risk_count >= 1:
        report.append("- Moderate equity exposure to 60-70%")
        report.append("- Hold some cash for opportunities")
        report.append("- Focus on quality/defensive names")
    else:
        report.append("- Focus on cyclical/value names")
        report.append("- Use dips as buying opportunities")

    # Override Risk Management if in Shutdown Mode
    if is_data_stale:
        report.append("\n**⚠️ SHUTDOWN STRATEGY:**")
        report.append("- **Focus on High Conviction Growth (Biotech/Software)**")
        report.append("- **Hedge with Put Options on Cyclicals**")
        report.append("- Avoid pure defensive names, seek Alpha in innovation")

    report.append(f"\n**Stop Loss:**")
    report.append("- Mental stop at -5% portfolio level")
    report.append("- Reassess thesis if unemployment jumps > 0.5%")
    report.append("- Exit if yield curve steepens after inversion")

    # 8. Druckenmiller 金句
    report.append("\n## 💡 Druckenmiller Wisdom")
    report.append(f"\n> *\"He who lives by the crystal ball will eat shattered glass.\"*")
    report.append(">")
    report.append(f"> **Current Call:** {conviction} based on:")

    if cpi and cpi.get('cpi_yoy') is not None:
        inflation_val = cpi['cpi_yoy']
        report.append(f"> - Inflation trend: {inflation_val:.1f}% YoY")
    else:
        report.append("> - Inflation trend: Data limited")

    if fed_policy:
        fed_rate = fed_policy['fed_funds_rate']
        liquidity_status = 'Tight' if fed_rate > 4 else 'Accommodative'
        report.append(f"> - Liquidity conditions: {liquidity_status}")

    if labour and 'payrolls_change' in labour:
        pay_change = labour['payrolls_change']
        if pay_change > 200000:
            labour_status = 'Strong'
        elif pay_change < 0:
            labour_status = 'Weakening'
        else:
            labour_status = 'Stable'
        report.append(f"> - Labour market: {labour_status}")

    yield_status = yield_curve['curve_status'] if yield_curve else 'Unknown'
    report.append(f"> - Yield curve: {yield_status}")

    return "\n".join(report)

if __name__ == "__main__":
    report = generate_druckenmiller_report()

    # Save to file
    os.makedirs("datas/fred/analysis", exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    report_file = f"datas/fred/analysis/druckenmiller_report_{timestamp}.md"
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\n" + "="*70)
    print(f"✅ Report generated: {report_file}")
    print("="*70)

    # Also print to console
    print(report)
