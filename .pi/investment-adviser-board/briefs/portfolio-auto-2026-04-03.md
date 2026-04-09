# 分析主題
使用者目前真實投資組合的全自動委員會分析

# 目標
請以「現在該怎麼做」為核心，而不只是描述市場觀點。請在內部收斂為三輪：
1. 第一輪：各委員提出 current market view 與對現有持倉的初步影響
2. 第二輪：聚焦組合重疊曝險、最該先處理的部位、現在不該做的事
3. 第三輪：收斂成具體 action now 與 reaction plan

# 使用者背景
- 這些券商帳戶資金是主要股票交易資金
- 銀行存款是生活預備金，不納入本次風險資本
- 報告請優先使用 USD 視角；若某些部位為 HKD 或未知幣別且無法安全換算，請保留原幣別並如實說明

# 最新投資組合 pointer JSON
```json
{
  "latest_snapshot_date": "2026-04-03",
  "latest_snapshot_json_path": ".pi/investment-adviser-board/portfolio-records/2026-04-03/portfolio-snapshot-user-2026-04-03.json",
  "latest_snapshot_md_path": ".pi/investment-adviser-board/portfolio-records/2026-04-03/portfolio-snapshot-user-2026-04-03.md",
  "rules": {
    "storage_pattern": ".pi/investment-adviser-board/portfolio-records/YYYY-MM-DD/portfolio-snapshot-user-YYYY-MM-DD.json",
    "reporting_currency_preference": "USD",
    "agent_priority": "Agents should use the dated JSON snapshot first, then consult the dated markdown snapshot only for human notes or ambiguity."
  }
}
```

# 最新 positions.json 內容
```json
{
  "positions": [
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "09988", "asset_type": "stock", "currency": "HKD", "quantity": 300, "last_price": 118.5, "cost_basis": 129.0, "market_value": 35550.0},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "01299", "asset_type": "stock", "currency": "HKD", "quantity": 1, "last_price": 86.15, "cost_basis": 70.6, "market_value": 86.15},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "AMZN", "asset_type": "stock", "currency": "USD", "quantity": 24, "last_price": 209.77, "cost_basis": 222.292, "market_value": 5034.48},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "GLD", "asset_type": "etf", "currency": "USD", "quantity": 14, "last_price": 429.41, "cost_basis": 278.15, "market_value": 6011.74},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "GOOG", "asset_type": "stock", "currency": "USD", "quantity": 9, "last_price": 294.46, "cost_basis": 167.0, "market_value": 2650.14},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "INDA", "asset_type": "etf", "currency": "USD", "quantity": 58, "last_price": 46.65, "cost_basis": 49.669, "market_value": 2705.7},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "OKLO", "asset_type": "stock", "currency": "USD", "quantity": 19, "last_price": 48.13, "cost_basis": 105.483, "market_value": 914.47},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "SPY", "asset_type": "etf", "currency": "USD", "quantity": 8, "last_price": 655.83, "cost_basis": 578.155, "market_value": 5246.64},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "TSLA", "asset_type": "stock", "currency": "USD", "quantity": 7, "last_price": 360.59, "cost_basis": 384.0, "market_value": 2524.13},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "VOO", "asset_type": "etf", "currency": "USD", "quantity": 33, "last_price": 602.99, "cost_basis": 565.327, "market_value": 19898.67},
    {"account_id": "broker_a_futu_2130", "broker": "Futu", "symbol": "XLK", "asset_type": "etf", "currency": "USD", "quantity": 53, "last_price": 135.99, "cost_basis": 123.776, "market_value": 7207.47},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "DX", "asset_type": "future", "currency": "UNKNOWN", "quantity": -1, "last_price": 99.855, "pnl": -5.0},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "IONQ", "asset_type": "stock", "currency": "USD", "quantity": 55, "last_price": 29.2, "market_value": 1606.0, "pnl": 77.55},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "SLV", "asset_type": "etf", "currency": "USD", "quantity": 31, "last_price": 65.81, "market_value": 2040.11, "pnl": -72.22},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "TSLA", "asset_type": "stock", "currency": "USD", "quantity": 3, "last_price": 361.26, "market_value": 1083.78, "pnl": -60.0},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "VOO", "asset_type": "etf", "currency": "USD", "quantity": 24, "last_price": 602.95, "market_value": 14470.8, "pnl": 15.6},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "XLK", "asset_type": "etf", "currency": "USD", "quantity": 30, "last_price": 135.83, "market_value": 4074.9, "pnl": 27.6},
    {"account_id": "broker_b_ibkr_u6822296", "broker": "IBKR", "symbol": "XLY", "asset_type": "etf", "currency": "USD", "quantity": 20, "last_price": 108.11, "market_value": 2162.2, "pnl": -33.8}
  ],
  "aggregate_known_positions": [
    {"symbol": "VOO", "total_quantity": 57, "currency": "USD"},
    {"symbol": "XLK", "total_quantity": 83, "currency": "USD"},
    {"symbol": "SPY", "total_quantity": 8, "currency": "USD"},
    {"symbol": "XLY", "total_quantity": 20, "currency": "USD"},
    {"symbol": "INDA", "total_quantity": 58, "currency": "USD"},
    {"symbol": "GLD", "total_quantity": 14, "currency": "USD"},
    {"symbol": "SLV", "total_quantity": 31, "currency": "USD"},
    {"symbol": "AMZN", "total_quantity": 24, "currency": "USD"},
    {"symbol": "GOOG", "total_quantity": 9, "currency": "USD"},
    {"symbol": "TSLA", "total_quantity": 10, "currency": "USD"},
    {"symbol": "OKLO", "total_quantity": 19, "currency": "USD"},
    {"symbol": "IONQ", "total_quantity": 55, "currency": "USD"},
    {"symbol": "09988", "total_quantity": 300, "currency": "HKD"},
    {"symbol": "01299", "total_quantity": 1, "currency": "HKD"},
    {"symbol": "DX", "total_quantity": -1, "currency": "UNKNOWN"}
  ]
}
```

# 報告要求
請輸出：
- Current Market View
- Portfolio Risk Concentration
- Top Priority Actions（現在先做的 3 件事）
- What Not To Do Now
- Reaction Plan（若市場上行 / 下行 / 震盪）
- 按持倉分類：Add / Hold / Trim / Exit-Avoid / Wait
- HTML 報告
