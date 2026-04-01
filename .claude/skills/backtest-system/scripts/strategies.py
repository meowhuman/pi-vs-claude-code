#!/usr/bin/env python3
"""
Strategy library — pure pandas/numpy, no TA-Lib dependency.
Each strategy adds a 'signal' column: 1=long, -1=short/cash, 0=neutral.
"""

import pandas as pd
import numpy as np


def sma_crossover(df: pd.DataFrame, short_ma: int = 10, long_ma: int = 30) -> pd.DataFrame:
    """SMA 黃金/死叉：短線上穿長線做多"""
    df = df.copy()
    df['sma_short'] = df['close'].rolling(short_ma).mean()
    df['sma_long'] = df['close'].rolling(long_ma).mean()
    df['signal'] = np.where(df['sma_short'] > df['sma_long'], 1, -1)
    return df


def ema_crossover(df: pd.DataFrame, short_ema: int = 9, long_ema: int = 21) -> pd.DataFrame:
    """EMA 黃金/死叉"""
    df = df.copy()
    df['ema_short'] = df['close'].ewm(span=short_ema, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_ema, adjust=False).mean()
    df['signal'] = np.where(df['ema_short'] > df['ema_long'], 1, -1)
    return df


def rsi_strategy(df: pd.DataFrame, rsi_period: int = 14,
                 rsi_lower: int = 30, rsi_upper: int = 70) -> pd.DataFrame:
    """RSI 均值回歸：低買高賣"""
    df = df.copy()
    delta = df['close'].diff()
    # Wilder EMA (equivalent to ewm with com=period-1)
    gain = delta.clip(lower=0).ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
    loss = (-delta).clip(lower=0).ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
    rs = gain / (loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['signal'] = 0
    df.loc[df['rsi'] < rsi_lower, 'signal'] = 1
    df.loc[df['rsi'] > rsi_upper, 'signal'] = -1
    df['signal'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    return df


def bollinger_bands_strategy(df: pd.DataFrame, bb_period: int = 20,
                              bb_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands：觸下軌買，觸上軌賣"""
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(bb_period).mean()
    std = df['close'].rolling(bb_period).std()
    df['bb_upper'] = df['bb_mid'] + bb_std * std
    df['bb_lower'] = df['bb_mid'] - bb_std * std
    df['signal'] = 0
    df.loc[df['close'] < df['bb_lower'], 'signal'] = 1
    df.loc[df['close'] > df['bb_upper'], 'signal'] = -1
    df['signal'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    return df


def macd_strategy(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                  signal_period: int = 9) -> pd.DataFrame:
    """MACD：MACD 線上穿 Signal 線做多"""
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    df['signal'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
    return df


def momentum_strategy(df: pd.DataFrame, lookback: int = 20,
                      threshold: float = 0.02) -> pd.DataFrame:
    """動量策略：N 日漲幅超過閾值做多"""
    df = df.copy()
    df['momentum'] = df['close'].pct_change(lookback)
    df['signal'] = 0
    df.loc[df['momentum'] > threshold, 'signal'] = 1
    df.loc[df['momentum'] < -threshold, 'signal'] = -1
    df['signal'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    return df


# ─── Indicator Computation Helpers ────────────────────────────────────

def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute all indicators used by compose_strategy."""
    # RSI (14)
    delta = df['close'].diff()
    gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
    loss = (-delta).clip(lower=0).ewm(com=13, min_periods=14).mean()
    df['_rsi'] = 100 - (100 / (1 + gain / (loss + 1e-10)))

    # MACD (12/26/9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['_macd'] = ema12 - ema26
    df['_macd_signal'] = df['_macd'].ewm(span=9, adjust=False).mean()
    df['_macd_hist'] = df['_macd'] - df['_macd_signal']
    # MACD cross: 1 = golden cross (MACD > signal), -1 = death cross
    df['_macd_cross'] = np.where(df['_macd'] > df['_macd_signal'], 1, -1)

    # Bollinger Bands (20, 2σ)
    bb_mid = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['_bb_upper'] = bb_mid + 2 * bb_std
    df['_bb_lower'] = bb_mid - 2 * bb_std
    df['_bb_pctb'] = (df['close'] - df['_bb_lower']) / (df['_bb_upper'] - df['_bb_lower'] + 1e-10)

    # Moving Averages
    for p in [5, 10, 20, 50, 200]:
        df[f'_sma{p}'] = df['close'].rolling(p).mean()
    for p in [9, 12, 21, 26, 50]:
        df[f'_ema{p}'] = df['close'].ewm(span=p, adjust=False).mean()

    # Price vs MA ratios
    df['_price_vs_sma20'] = df['close'] / (df['_sma20'] + 1e-10)
    df['_price_vs_sma50'] = df['close'] / (df['_sma50'] + 1e-10)

    # ADX (14) — approximation without TA-Lib
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    df['_atr'] = tr.rolling(14).mean()

    plus_dm = np.where((high - high.shift()) > (low.shift() - low), np.maximum(high - high.shift(), 0), 0)
    minus_dm = np.where((low.shift() - low) > (high - high.shift()), np.maximum(low.shift() - low, 0), 0)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).mean() / (df['_atr'] + 1e-10)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).mean() / (df['_atr'] + 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    df['_adx'] = dx.rolling(14).mean()

    # Volume ratio (volume / 20-day MA volume)
    if 'volume' in df.columns and df['volume'].sum() > 0:
        df['_vol_ratio'] = df['volume'] / (df['volume'].rolling(20).mean() + 1e-10)
    else:
        df['_vol_ratio'] = 1.0

    # Momentum (20-day)
    df['_mom'] = df['close'].pct_change(20)

    # Stochastic %K (14)
    low14 = df['low'].rolling(14).min()
    high14 = df['high'].rolling(14).max()
    df['_stoch_k'] = 100 * (df['close'] - low14) / (high14 - low14 + 1e-10)

    return df


def parse_compose_rules(rule_strings: list[str]) -> list[dict]:
    """
    Parse compose rule strings into structured dicts.

    Format: "indicator<value:action" or "indicator>value:action"
    Examples:
        "rsi<30:buy"       → RSI below 30 → buy signal
        "rsi>70:sell"      → RSI above 70 → sell signal
        "macd_cross==1:buy" → MACD golden cross → buy signal
        "adx>25:buy"       → ADX strong trend → buy signal
        "bb_pctb<0.1:buy"  → Near lower Bollinger Band → buy signal
        "vol_ratio>1.5:buy" → Volume spike → buy signal
        "stoch_k<20:buy"   → Stochastic oversold → buy signal
    """
    import re
    rules = []
    for s in rule_strings:
        s = s.strip()
        if ':' not in s:
            print(f'⚠️  Skipping invalid rule (no colon): {s}')
            continue

        expr, action = s.rsplit(':', 1)
        action = action.strip().lower()
        if action not in ('buy', 'sell'):
            print(f'⚠️  Skipping invalid action (must be buy/sell): {s}')
            continue

        # Parse operator and value
        m = re.match(r'^([a-z_0-9]+)\s*(<=|>=|<|>|==|!=)\s*(.+)$', expr.strip())
        if not m:
            print(f'⚠️  Skipping invalid expression: {expr}')
            continue

        indicator = m.group(1)
        operator = m.group(2)
        try:
            value = float(m.group(3))
        except ValueError:
            value = m.group(3)  # String value for == comparisons

        rules.append({
            'indicator': indicator,
            'operator': operator,
            'value': value,
            'action': action,
        })

    return rules


def _eval_condition(series: pd.Series, operator: str, value) -> pd.Series:
    """Evaluate a condition on a pandas Series."""
    if operator == '<':
        return series < value
    elif operator == '<=':
        return series <= value
    elif operator == '>':
        return series > value
    elif operator == '>=':
        return series >= value
    elif operator == '==':
        return series == value
    elif operator == '!=':
        return series != value
    return pd.Series(False, index=series.index)


# Mapping from rule indicator names → computed column names
_INDICATOR_MAP = {
    'rsi': '_rsi',
    'macd': '_macd',
    'macd_signal': '_macd_signal',
    'macd_hist': '_macd_hist',
    'macd_cross': '_macd_cross',
    'bb_pctb': '_bb_pctb',
    'bb_upper': '_bb_upper',
    'bb_lower': '_bb_lower',
    'sma5': '_sma5', 'sma10': '_sma10', 'sma20': '_sma20',
    'sma50': '_sma50', 'sma200': '_sma200',
    'ema9': '_ema9', 'ema12': '_ema12', 'ema21': '_ema21',
    'ema26': '_ema26', 'ema50': '_ema50',
    'price_vs_sma20': '_price_vs_sma20',
    'price_vs_sma50': '_price_vs_sma50',
    'adx': '_adx', 'atr': '_atr',
    'vol_ratio': '_vol_ratio',
    'mom': '_mom',
    'stoch_k': '_stoch_k',
    'close': 'close', 'volume': 'volume',
}


def compose_strategy(df: pd.DataFrame, rules: list[dict] = None,
                     rule_strings: list[str] = None) -> pd.DataFrame:
    """
    多指標聯合策略組合器。

    買入條件：所有 buy rules 全部滿足時做多（AND 邏輯）
    賣出條件：任一 sell rule 滿足時平倉（OR 邏輯）

    Args:
        df: OHLCV DataFrame
        rules: List of rule dicts with keys: indicator, operator, value, action
        rule_strings: List of rule strings (alternative to rules), e.g. ["rsi<30:buy", "macd_cross==1:buy"]

    Returns:
        DataFrame with 'signal' column added
    """
    df = df.copy()

    # Parse rule strings if provided
    if rule_strings and not rules:
        rules = parse_compose_rules(rule_strings)

    if not rules:
        raise ValueError('No rules provided for compose_strategy. '
                         'Use --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell"')

    # Compute all indicators
    df = _compute_indicators(df)

    # Evaluate buy/sell masks
    buy_mask = pd.Series(True, index=df.index)
    sell_mask = pd.Series(False, index=df.index)
    has_buy = False
    has_sell = False

    for rule in rules:
        col_name = _INDICATOR_MAP.get(rule['indicator'])
        if col_name is None or col_name not in df.columns:
            print(f'⚠️  Unknown indicator: {rule["indicator"]}')
            print(f'   Available: {", ".join(sorted(_INDICATOR_MAP.keys()))}')
            continue

        cond = _eval_condition(df[col_name], rule['operator'], rule['value'])

        if rule['action'] == 'buy':
            buy_mask = buy_mask & cond  # AND logic for buy
            has_buy = True
        elif rule['action'] == 'sell':
            sell_mask = sell_mask | cond  # OR logic for sell
            has_sell = True

    if not has_buy:
        raise ValueError('No buy rules found. At least one buy rule is required.')

    # Generate signals
    df['signal'] = 0
    df.loc[buy_mask, 'signal'] = 1
    if has_sell:
        df.loc[sell_mask, 'signal'] = -1
    else:
        # If no sell rules, use inverse of buy as sell
        df.loc[~buy_mask, 'signal'] = -1

    df['signal'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    return df


STRATEGIES = {
    'sma_crossover': sma_crossover,
    'ema_crossover': ema_crossover,
    'rsi': rsi_strategy,
    'bollinger_bands': bollinger_bands_strategy,
    'macd': macd_strategy,
    'momentum': momentum_strategy,
    'compose': compose_strategy,
}
