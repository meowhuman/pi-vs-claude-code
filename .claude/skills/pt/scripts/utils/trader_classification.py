#!/usr/bin/env python3
"""
Market Maker & Smart Money Detection Functions
整合自 polymarket-analyzer 嘅進階分析功能
"""


def is_likely_market_maker(wallet_data: dict) -> tuple:
    """
    判斷一個錢包係咪 Market Maker
    
    Args:
        wallet_data: {
            'market_trades': int,      # 該市場交易次數
            'global_trades': int,      # 全球總交易次數
            'market_pnl': float,       # 該市場盈虧
            'total_volume': float      # 總交易額
        }
    
    Returns:
        (is_mm: bool, confidence: str, reasons: list)
    """
    reasons = []
    score = 0
    
    market_trades = wallet_data.get('market_trades', 0)
    global_trades = wallet_data.get('global_trades', 0)
    market_pnl = wallet_data.get('market_pnl', 0)
    
    # 🆕 持倉平衡度檢查 (MM 應該雙邊持倉平衡)
    yes_value = wallet_data.get('yes_value', 0)
    no_value = wallet_data.get('no_value', 0)
    total_value = yes_value + no_value
    
    if total_value > 0:
        balance_ratio = min(yes_value, no_value) / max(yes_value, no_value) if max(yes_value, no_value) > 0 else 0
    else:
        balance_ratio = 0
    
    # 單邊持倉者 (balance_ratio < 0.2) 唔太可能係 MM
    if balance_ratio < 0.2 and total_value > 1000:
        # 明顯單邊，唔係 MM
        return False, "EXCLUDED", [f"單邊持倉 ({balance_ratio:.0%})"]
    
    # 條件 1: 超高頻市場交易 (>100 筆/市場) + 需要平衡持倉
    if market_trades > 200 and balance_ratio > 0.3:
        score += 3
        reasons.append(f"極高頻交易 ({market_trades} trades) + 平衡持倉")
    elif market_trades > 100 and balance_ratio > 0.3:
        score += 2
        reasons.append(f"高頻交易 ({market_trades} trades) + 平衡持倉")
    elif market_trades > 100:
        score += 1  # 高頻但單邊，減少分數
        reasons.append(f"高頻交易 ({market_trades} trades)")
    
    # 條件 2: 全球交易量巨大 (>100萬) - 保持不變
    if global_trades > 5_000_000:
        score += 3
        reasons.append(f"超級大戶 ({global_trades:,} global trades)")
    elif global_trades > 1_000_000:
        score += 2
        reasons.append(f"大額交易者 ({global_trades:,} global trades)")
    elif global_trades > 500_000:  # 提高門檻
        score += 1
        reasons.append(f"活躍交易者 ({global_trades:,} global trades)")
    
    # 條件 3: 巨額虧損 (MM 經常承受庫存風險) - 保持不變
    if market_pnl < -100000:
        score += 2
        reasons.append(f"巨額庫存虧損 (${abs(market_pnl):,.0f})")
    elif market_pnl < -10000:
        score += 1
        reasons.append(f"顯著虧損 (${abs(market_pnl):,.0f})")
    
    # 判斷 (提高門檻)
    if score >= 5:
        return True, "HIGH", reasons
    elif score >= 4:  # 提高 MEDIUM 門檻
        return True, "MEDIUM", reasons
    elif score >= 3:
        return False, "POSSIBLE", reasons
    else:
        return False, "LOW", reasons


def is_smart_money(wallet_data: dict) -> tuple:
    """
    判斷一個錢包係咪 Smart Money (真正有實力嘅交易者)
    
    Args:
        wallet_data: {
            'market_pnl': float,
            'market_trades': int,
            'global_trades': int,
            'is_market_maker': bool
        }
    
    Returns:
        (is_sm: bool, confidence: str, reasons: list)
    """
    reasons = []
    score = 0
    
    market_pnl = wallet_data.get('market_pnl', 0)
    market_trades = wallet_data.get('market_trades', 0)
    global_trades = wallet_data.get('global_trades', 0)
    is_mm = wallet_data.get('is_market_maker', False)
    
    # 排除 Market Maker
    if is_mm:
        return False, "EXCLUDED", ["Market Maker - 唔計入 Smart Money"]
    
    # 必須係贏家
    if market_pnl <= 0:
        return False, "EXCLUDED", ["非贏家 - 唔符合 Smart Money 定義"]
    
    # 條件 1: 有實際獲利
    if market_pnl > 10000:
        score += 3
        reasons.append(f"顯著獲利 (+${market_pnl:,.0f})")
    elif market_pnl > 3000:
        score += 2
        reasons.append(f"良好獲利 (+${market_pnl:,.0f})")
    elif market_pnl > 500:
        score += 1
        reasons.append(f"正收益 (+${market_pnl:,.0f})")
    
    # 條件 2: 適度交易頻率 (唔係一次性運氣)
    if 10 <= market_trades <= 100:
        score += 2
        reasons.append(f"主動管理倉位 ({market_trades} trades)")
    elif 5 <= market_trades < 10:
        score += 1
        reasons.append(f"多次交易 ({market_trades} trades)")
    elif market_trades == 1:
        score -= 1  # 只買一次可能係運氣
        reasons.append("⚠️ 單次交易 (可能係運氣)")
    elif market_trades > 100:
        score += 1  # 高頻但唔係 MM
        reasons.append(f"高頻操作 ({market_trades} trades)")
    
    # 條件 3: 有足夠經驗 (跨市場表現)
    if 5000 <= global_trades <= 100000:
        score += 2
        reasons.append(f"資深交易者 ({global_trades:,} total)")
    elif 1000 <= global_trades < 5000:
        score += 1
        reasons.append(f"有經驗 ({global_trades:,} total)")
    elif global_trades > 1000000:
        score -= 1  # 太多可能係 Bot
        reasons.append("⚠️ 超高頻 (可能係 Bot)")
    elif global_trades < 1000:
        score -= 1
        reasons.append("⚠️ 新手 (經驗不足)")
    
    # 判斷 (放寬門檻)
    if score >= 5:
        return True, "HIGH", reasons
    elif score >= 3:
        return True, "MEDIUM", reasons
    elif score >= 2:  # 放寬: 2 分就算 Smart Money (LOW confidence)
        return True, "LOW", reasons
    else:
        return False, "N/A", reasons


def is_retailer(wallet_data: dict) -> tuple:
    """
    判斷一個錢包係咪 Retailer (小額散戶)
    
    Args:
        wallet_data: {
            'total_value': float,      # 當前持倉價值
            'market_trades': int,      # 交易次數
            'global_trades': int,      # 全球交易
            'is_market_maker': bool
        }
    
    Returns:
        (is_retailer: bool, confidence: str, reasons: list)
    """
    reasons = []
    
    total_value = wallet_data.get('total_value', 0)
    market_trades = wallet_data.get('market_trades', 0)
    global_trades = wallet_data.get('global_trades', 0)
    is_mm = wallet_data.get('is_market_maker', False)
    
    # 排除 Market Maker
    if is_mm:
        return False, "EXCLUDED", ["Market Maker - 唔係散戶"]
    
    # Retailer 定義：持倉小 + 交易經驗少（放寬標準）
    is_small_holder = total_value < 3000  # 提高到 $3k
    is_inexperienced = global_trades < 100  # 提高到 100 筆
    
    if is_small_holder and is_inexperienced:
        reasons.append(f"小額持倉 (${total_value:,.0f})")
        reasons.append(f"新手/散戶 ({global_trades} total trades)")
        return True, "HIGH", reasons
    elif is_small_holder:
        reasons.append(f"小額持倉 (${total_value:,.0f})")
        return True, "MEDIUM", reasons
    elif is_inexperienced and total_value < 5000:
        reasons.append(f"新手 ({global_trades} trades)")
        return True, "LOW", reasons
    else:
        return False, "N/A", []


def classify_trader_role(wallet_data: dict) -> dict:
    """
    綜合判斷交易者角色
    
    Returns:
        {
            'role': str,           # MARKET_MAKER, SMART_MONEY, WHALE, RETAILER, LOSER, REGULAR
            'emoji': str,
            'confidence': str,
            'reasons': list
        }
    """
    is_mm, mm_conf, mm_reasons = is_likely_market_maker(wallet_data)
    is_sm, sm_conf, sm_reasons = is_smart_money(wallet_data)
    is_ret, ret_conf, ret_reasons = is_retailer(wallet_data)
    
    market_pnl = wallet_data.get('market_pnl', 0)
    total_value = wallet_data.get('total_value', 0)
    
    # Market Maker (優先判斷)
    if is_mm and mm_conf in ["HIGH", "MEDIUM"]:
        return {
            'role': 'MARKET_MAKER',
            'emoji': '🏦',
            'confidence': mm_conf,
            'reasons': mm_reasons
        }
    
    # Smart Money (聰明錢)
    if is_sm and sm_conf in ["HIGH", "MEDIUM"]:
        return {
            'role': 'SMART_MONEY',
            'emoji': '🧠',
            'confidence': sm_conf,
            'reasons': sm_reasons
        }
    
    # Whale (大戶但未必聰明)
    if total_value > 10000 and market_pnl > 0:
        return {
            'role': 'WHALE',
            'emoji': '🐋',
            'confidence': 'HIGH',
            'reasons': [f"大額持倉 (${total_value:,.0f})", f"盈利中 (+${market_pnl:,.0f})"]
        }
    
    # Loser (虧損者) - 排除 Retailer
    if market_pnl < -1000 and not is_mm and not (is_ret and ret_conf == "HIGH"):
        return {
            'role': 'LOSER',
            'emoji': '📉',
            'confidence': 'HIGH',
            'reasons': [f"虧損 (${market_pnl:,.0f})"]
        }
    
    # Retailer (小額散戶)
    if is_ret and ret_conf in ["HIGH", "MEDIUM"]:
        return {
            'role': 'RETAILER',
            'emoji': '🎰',
            'confidence': ret_conf,
            'reasons': ret_reasons
        }
    
    # Regular Trader
    return {
        'role': 'REGULAR',
        'emoji': '👤',
        'confidence': 'N/A',
        'reasons': ['普通交易者']
    }
