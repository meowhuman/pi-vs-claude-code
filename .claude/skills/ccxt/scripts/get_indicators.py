#!/usr/bin/env python3
"""
CCXT Crypto Technical Indicators
Calculate 26+ technical indicators on crypto OHLCV data.
Supports intraday timeframes (1m, 5m, 15m, 1h, etc.) that Tiingo free doesn't have.

Usage: python get_indicators.py <SYMBOL> [--timeframe TF] [--indicator IND]
"""

import json
import sys
import asyncio
import argparse

try:
    import ccxt.async_support as ccxt
except ImportError:
    print("ERROR: ccxt not installed. Run: uv pip install -r requirements.txt")
    sys.exit(1)

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("ERROR: pandas not installed. Run: uv pip install pandas numpy")
    sys.exit(1)


# =============================================================================
# TECHNICAL INDICATORS
# Adapted from STA skill to work with CCXT OHLCV data
# =============================================================================

class TechnicalIndicators:
    """Calculate technical indicators from OHLCV DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.results = {}

    # ==========================================================================
    # Trend Indicators
    # ==========================================================================

    def sma(self, period: int = 20) -> dict:
        """Simple Moving Average."""
        sma = self.df['close'].rolling(window=period).mean()
        return {
            'value': round(float(sma.iloc[-1]), 4),
            'trend': 'UP' if sma.iloc[-1] > sma.iloc[-5] else 'DOWN'
        }

    def ema(self, period: int = 20) -> dict:
        """Exponential Moving Average."""
        ema = self.df['close'].ewm(span=period, adjust=False).mean()
        return {
            'value': round(float(ema.iloc[-1]), 4),
            'trend': 'UP' if ema.iloc[-1] > ema.iloc[-5] else 'DOWN'
        }

    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """MACD (Moving Average Convergence Divergence)."""
        ema_fast = self.df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            'macd': round(float(macd_line.iloc[-1]), 6),
            'signal': round(float(signal_line.iloc[-1]), 6),
            'histogram': round(float(histogram.iloc[-1]), 6),
            'direction': 'BULLISH' if histogram.iloc[-1] > 0 else 'BEARISH'
        }

    def parabolic_sar(self, af: float = 0.02, max_af: float = 0.2) -> dict:
        """Parabolic SAR."""
        high = self.df['high'].values
        low = self.df['low'].values
        close = self.df['close'].values

        sar = [low[0]]
        ep = high[0]
        trend = 1  # 1 = up, -1 = down
        af_current = af

        for i in range(1, len(high)):
            if trend == 1:  # Uptrend
                sar.append(sar[-1] + af_current * (ep - sar[-1]))
                sar[-1] = min(sar[-1], low[i-1], low[i-2] if i > 1 else low[i-1])

                if low[i] < sar[-1]:
                    trend = -1
                    sar[-1] = ep
                    ep = low[i]
                    af_current = af
                elif high[i] > ep:
                    ep = high[i]
                    af_current = min(af_current + af, max_af)
            else:  # Downtrend
                sar.append(sar[-1] + af_current * (ep - sar[-1]))
                sar[-1] = max(sar[-1], high[i-1], high[i-2] if i > 1 else high[i-1])

                if high[i] > sar[-1]:
                    trend = 1
                    sar[-1] = ep
                    ep = high[i]
                    af_current = af
                elif low[i] < ep:
                    ep = low[i]
                    af_current = min(af_current + af, max_af)

        current_price = close[-1]
        current_sar = sar[-1]

        return {
            'value': round(float(current_sar), 4),
            'position': 'BELOW_PRICE' if current_sar < current_price else 'ABOVE_PRICE',
            'signal': 'BULLISH' if current_sar < current_price else 'BEARISH'
        }

    def trix(self, period: int = 14) -> dict:
        """TRIX (Triple Exponential Moving Average)."""
        ema1 = self.df['close'].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        trix = ((ema3 - ema3.shift(1)) / ema3.shift(1)) * 10000

        return {
            'value': round(float(trix.iloc[-1]), 4),
            'trend': 'UP' if trix.iloc[-1] > trix.iloc[-2] else 'DOWN'
        }

    def ichimoku_cloud(self) -> dict:
        """Ichimoku Cloud."""
        high_9 = self.df['high'].rolling(window=9).max()
        low_9 = self.df['low'].rolling(window=9).min()
        tenkan_sen = (high_9 + low_9) / 2

        high_26 = self.df['high'].rolling(window=26).max()
        low_26 = self.df['low'].rolling(window=26).min()
        kijun_sen = (high_26 + low_26) / 2

        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
        senkou_span_b = ((self.df['high'].rolling(window=52).max() +
                         self.df['low'].rolling(window=52).min()) / 2).shift(26)

        current_price = self.df['close'].iloc[-1]
        cloud_top = max(senkou_span_a.iloc[-1], senkou_span_b.iloc[-1])
        cloud_bottom = min(senkou_span_a.iloc[-1], senkou_span_b.iloc[-1])

        position = 'ABOVE_CLOUD' if current_price > cloud_top else \
                   'BELOW_CLOUD' if current_price < cloud_bottom else 'INSIDE_CLOUD'

        return {
            'tenkan_sen': round(float(tenkan_sen.iloc[-1]), 4),
            'kijun_sen': round(float(kijun_sen.iloc[-1]), 4),
            'senkou_span_a': round(float(senkou_span_a.iloc[-1]), 4),
            'senkou_span_b': round(float(senkou_span_b.iloc[-1]), 4),
            'position': position,
            'signal': 'BULLISH' if position == 'ABOVE_CLOUD' else 'BEARISH' if position == 'BELOW_CLOUD' else 'NEUTRAL'
        }

    # ==========================================================================
    # Momentum Indicators
    # ==========================================================================

    def rsi(self, period: int = 14) -> dict:
        """Relative Strength Index."""
        delta = self.df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        value = float(rsi.iloc[-1])
        return {
            'value': round(value, 2),
            'signal': 'OVERBOUGHT' if value > 70 else 'OVERSOLD' if value < 30 else 'NEUTRAL',
            'trend': 'UP' if rsi.iloc[-1] > rsi.iloc[-2] else 'DOWN'
        }

    def stochastic(self, k_period: int = 14, d_period: int = 3) -> dict:
        """Stochastic Oscillator."""
        low_min = self.df['low'].rolling(window=k_period).min()
        high_max = self.df['high'].rolling(window=k_period).max()
        k = 100 * ((self.df['close'] - low_min) / (high_max - low_min))
        d = k.rolling(window=d_period).mean()

        k_val = float(k.iloc[-1])
        d_val = float(d.iloc[-1])

        return {
            'k': round(k_val, 2),
            'd': round(d_val, 2),
            'signal': 'OVERBOUGHT' if k_val > 80 else 'OVERSOLD' if k_val < 20 else 'NEUTRAL'
        }

    def williams_r(self, period: int = 14) -> dict:
        """Williams %R."""
        high_max = self.df['high'].rolling(window=period).max()
        low_min = self.df['low'].rolling(window=period).min()
        williams = -100 * ((high_max - self.df['close']) / (high_max - low_min))

        value = float(williams.iloc[-1])
        return {
            'value': round(value, 2),
            'signal': 'OVERSOLD' if value < -80 else 'OVERBOUGHT' if value > -20 else 'NEUTRAL'
        }

    def cci(self, period: int = 20) -> dict:
        """Commodity Channel Index."""
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_dev = typical_price.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean())
        cci = (typical_price - sma_tp) / (0.015 * mean_dev)

        value = float(cci.iloc[-1])
        return {
            'value': round(value, 2),
            'signal': 'OVERBOUGHT' if value > 100 else 'OVERSOLD' if value < -100 else 'NEUTRAL'
        }

    # ==========================================================================
    # Volatility Indicators
    # ==========================================================================

    def bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> dict:
        """Bollinger Bands."""
        sma = self.df['close'].rolling(window=period).mean()
        std = self.df['close'].rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        current_price = self.df['close'].iloc[-1]
        upper_val = float(upper.iloc[-1])
        lower_val = float(lower.iloc[-1])
        middle_val = float(sma.iloc[-1])

        position = 'ABOVE_UPPER' if current_price > upper_val else \
                   'BELOW_LOWER' if current_price < lower_val else 'WITHIN_BANDS'

        # %B indicator
        percent_b = (current_price - lower_val) / (upper_val - lower_val) if upper_val != lower_val else 0.5

        return {
            'upper': round(upper_val, 4),
            'middle': round(middle_val, 4),
            'lower': round(lower_val, 4),
            'percent_b': round(float(percent_b), 4),
            'position': position
        }

    def keltner_channels(self, period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> dict:
        """Keltner Channels."""
        ema = self.df['close'].ewm(span=period, adjust=False).mean()
        atr = self._calculate_atr(atr_period)

        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)

        current_price = self.df['close'].iloc[-1]

        return {
            'upper': round(float(upper.iloc[-1]), 4),
            'middle': round(float(ema.iloc[-1]), 4),
            'lower': round(float(lower.iloc[-1]), 4),
            'position': 'ABOVE_UPPER' if current_price > upper.iloc[-1] else \
                       'BELOW_LOWER' if current_price < lower.iloc[-1] else 'WITHIN'
        }

    def _calculate_atr(self, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift())
        low_close = abs(self.df['low'] - self.df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def atr(self, period: int = 14) -> dict:
        """Average True Range."""
        atr = self._calculate_atr(period)
        current_price = self.df['close'].iloc[-1]
        atr_val = float(atr.iloc[-1])

        return {
            'value': round(atr_val, 4),
            'volatility': 'HIGH' if atr_val > current_price * 0.02 else 'LOW'
        }

    def adx(self, period: int = 14) -> dict:
        """Average Directional Index."""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(window=period).mean()

        value = float(adx.iloc[-1])
        return {
            'value': round(value, 2),
            'strength': 'STRONG' if value > 25 else 'MODERATE' if value > 20 else 'WEAK',
            'trend': 'UP' if plus_di.iloc[-1] > minus_di.iloc[-1] else 'DOWN'
        }

    # ==========================================================================
    # Volume Indicators
    # ==========================================================================

    def vwap(self) -> dict:
        """Volume Weighted Average Price."""
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        vwap = (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()

        current_price = self.df['close'].iloc[-1]
        vwap_val = float(vwap.iloc[-1])

        return {
            'value': round(vwap_val, 4),
            'position': 'ABOVE' if current_price > vwap_val else 'BELOW'
        }

    def obv(self) -> dict:
        """On Balance Volume."""
        obv = [self.df['volume'].iloc[0]]

        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.append(obv[-1] + self.df['volume'].iloc[i])
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.append(obv[-1] - self.df['volume'].iloc[i])
            else:
                obv.append(obv[-1])

        return {
            'value': round(float(obv[-1]), 2),
            'trend': 'UP' if obv[-1] > obv[-5] else 'DOWN'
        }

    def mfi(self, period: int = 14) -> dict:
        """Money Flow Index."""
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        raw_money_flow = typical_price * self.df['volume']

        positive_flow = pd.Series(index=self.df.index, dtype='float64')
        negative_flow = pd.Series(index=self.df.index, dtype='float64')

        for i in range(1, len(self.df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = raw_money_flow.iloc[i]
                negative_flow.iloc[i] = 0
            else:
                positive_flow.iloc[i] = 0
                negative_flow.iloc[i] = raw_money_flow.iloc[i]

        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()

        money_flow_ratio = positive_sum / negative_sum
        mfi = 100 - (100 / (1 + money_flow_ratio))

        value = float(mfi.iloc[-1])
        return {
            'value': round(value, 2),
            'signal': 'OVERBOUGHT' if value > 80 else 'OVERSOLD' if value < 20 else 'NEUTRAL'
        }

    def volume_oscillator(self, short_period: int = 5, long_period: int = 10) -> dict:
        """Volume Oscillator."""
        short_vol = self.df['volume'].rolling(window=short_period).mean()
        long_vol = self.df['volume'].rolling(window=long_period).mean()
        vo = ((short_vol - long_vol) / long_vol) * 100

        value = float(vo.iloc[-1])
        return {
            'value': round(value, 2),
            'trend': 'INCREASING' if value > 0 else 'DECREASING'
        }

    def ad_line(self) -> dict:
        """Accumulation/Distribution Line."""
        clv = ((self.df['close'] - self.df['low']) - (self.df['high'] - self.df['close'])) / \
              (self.df['high'] - self.df['low'])
        clv = clv.fillna(0)
        ad_line = (clv * self.df['volume']).cumsum()

        return {
            'value': round(float(ad_line.iloc[-1]), 2),
            'trend': 'UP' if ad_line.iloc[-1] > ad_line.iloc[-5] else 'DOWN'
        }

    def chaikin_oscillator(self, fast_period: int = 3, slow_period: int = 10) -> dict:
        """Chaikin Oscillator."""
        clv = ((self.df['close'] - self.df['low']) - (self.df['high'] - self.df['close'])) / \
              (self.df['high'] - self.df['low'])
        clv = clv.fillna(0)
        ad_line = (clv * self.df['volume']).cumsum()

        fast_ema = ad_line.ewm(span=fast_period, adjust=False).mean()
        slow_ema = ad_line.ewm(span=slow_period, adjust=False).mean()
        chaikin = fast_ema - slow_ema

        value = float(chaikin.iloc[-1])
        prev_value = float(chaikin.iloc[-2])

        return {
            'value': round(value, 4),
            'signal': 'BUY' if value > 0 and prev_value <= 0 else \
                     'SELL' if value < 0 and prev_value >= 0 else 'NEUTRAL'
        }

    def vwma(self, period: int = 20) -> dict:
        """Volume Weighted Moving Average."""
        vwma = (self.df['close'] * self.df['volume']).rolling(window=period).sum() / \
               self.df['volume'].rolling(window=period).sum()

        current_price = self.df['close'].iloc[-1]
        vwma_val = float(vwma.iloc[-1])

        return {
            'value': round(vwma_val, 4),
            'position': 'ABOVE' if current_price > vwma_val else 'BELOW'
        }

    def klinger_oscillator(self, short_period: int = 34, long_period: int = 55) -> dict:
        """Klinger Volume Oscillator."""
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        dm = self.df['high'] - self.df['low']

        cm = pd.Series(index=self.df.index, dtype='float64')
        cm.iloc[0] = dm.iloc[0]

        for i in range(1, len(self.df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                cm.iloc[i] = cm.iloc[i-1] + dm.iloc[i]
            else:
                cm.iloc[i] = cm.iloc[i-1] - dm.iloc[i]

        vf = self.df['volume'] * abs(2 * (dm / cm) - 1) * (typical_price.diff() / abs(typical_price.diff()))
        vf = vf.fillna(0)

        short_ema = vf.ewm(span=short_period, adjust=False).mean()
        long_ema = vf.ewm(span=long_period, adjust=False).mean()
        klinger = short_ema - long_ema

        signal = klinger.ewm(span=13, adjust=False).mean()

        return {
            'klinger': round(float(klinger.iloc[-1]), 4),
            'signal': round(float(signal.iloc[-1]), 4),
            'direction': 'BULLISH' if klinger.iloc[-1] > signal.iloc[-1] else 'BEARISH'
        }

    # ==========================================================================
    # Volume-Price Indicators
    # ==========================================================================

    def force_index(self, period: int = 13) -> dict:
        """Force Index."""
        force = (self.df['close'].diff() * self.df['volume']).ewm(span=period, adjust=False).mean()

        value = float(force.iloc[-1])
        return {
            'value': round(value, 2),
            'signal': 'BUY' if value > 0 else 'SELL' if value < 0 else 'NEUTRAL'
        }

    def ease_of_movement(self, period: int = 14) -> dict:
        """Ease of Movement."""
        distance = ((self.df['high'] + self.df['low']) / 2) - ((self.df['high'].shift(1) + self.df['low'].shift(1)) / 2)
        box_ratio = (self.df['volume'] / 100000000) / (self.df['high'] - self.df['low'])
        eom = distance / box_ratio
        eom_smooth = eom.rolling(window=period).mean()

        value = float(eom_smooth.iloc[-1])
        return {
            'value': round(value, 6),
            'signal': 'BULLISH' if value > 0 else 'BEARISH'
        }

    def nvi(self) -> dict:
        """Negative Volume Index."""
        nvi = [1000]

        for i in range(1, len(self.df)):
            if self.df['volume'].iloc[i] < self.df['volume'].iloc[i-1]:
                nvi.append(nvi[-1] + (self.df['close'].iloc[i] - self.df['close'].iloc[i-1]) / self.df['close'].iloc[i-1] * nvi[-1])
            else:
                nvi.append(nvi[-1])

        return {
            'value': round(float(nvi[-1]), 2),
            'trend': 'UP' if nvi[-1] > nvi[-5] else 'DOWN'
        }

    def pvi(self) -> dict:
        """Positive Volume Index."""
        pvi = [1000]

        for i in range(1, len(self.df)):
            if self.df['volume'].iloc[i] > self.df['volume'].iloc[i-1]:
                pvi.append(pvi[-1] + (self.df['close'].iloc[i] - self.df['close'].iloc[i-1]) / self.df['close'].iloc[i-1] * pvi[-1])
            else:
                pvi.append(pvi[-1])

        return {
            'value': round(float(pvi[-1]), 2),
            'trend': 'UP' if pvi[-1] > pvi[-5] else 'DOWN'
        }

    # ==========================================================================
    # Calculate All
    # ==========================================================================

    def calculate_all(self) -> dict:
        """Calculate all 26 technical indicators."""
        return {
            # Trend (6)
            'SMA_20': self.sma(20),
            'EMA_20': self.ema(20),
            'MACD': self.macd(),
            'Parabolic_SAR': self.parabolic_sar(),
            'TRIX': self.trix(),
            'Ichimoku_Cloud': self.ichimoku_cloud(),

            # Momentum (4)
            'RSI_14': self.rsi(14),
            'Stochastic_14': self.stochastic(14, 3),
            'Williams_R_14': self.williams_r(14),
            'CCI_20': self.cci(20),

            # Volatility (4)
            'Bollinger_Bands_20': self.bollinger_bands(20),
            'ATR_14': self.atr(14),
            'ADX_14': self.adx(14),
            'Keltner_Channels_20': self.keltner_channels(20),

            # Volume (8)
            'VWAP': self.vwap(),
            'OBV': self.obv(),
            'MFI_14': self.mfi(14),
            'Volume_Oscillator': self.volume_oscillator(),
            'AD_Line': self.ad_line(),
            'Chaikin_Oscillator': self.chaikin_oscillator(),
            'VWMA_20': self.vwma(20),
            'Klinger_Oscillator': self.klinger_oscillator(),

            # Volume-Price (4)
            'Force_Index': self.force_index(),
            'Ease_of_Movement': self.ease_of_movement(),
            'NVI': self.nvi(),
            'PVI': self.pvi()
        }


# =============================================================================
# DATA FETCHING
# =============================================================================

async def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
    exchange_id: str = "binance"
) -> pd.DataFrame:
    """Fetch OHLCV data from exchange."""

    exchange_class = getattr(ccxt, exchange_id, None)
    if not exchange_class:
        raise ValueError(f"Unknown exchange: {exchange_id}")

    exchange = exchange_class({"enableRateLimit": True})

    try:
        await exchange.load_markets()

        # Normalize symbol
        symbol = symbol.upper()
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"

        if symbol not in exchange.markets:
            raise ValueError(f"Symbol {symbol} not found on {exchange_id}")

        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        if not ohlcv:
            raise ValueError("No data returned")

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)

        return df

    finally:
        await exchange.close()


# =============================================================================
# MAIN
# =============================================================================

INDICATOR_CATEGORIES = {
    'trend': ['SMA_20', 'EMA_20', 'MACD', 'Parabolic_SAR', 'TRIX', 'Ichimoku_Cloud'],
    'momentum': ['RSI_14', 'Stochastic_14', 'Williams_R_14', 'CCI_20'],
    'volatility': ['Bollinger_Bands_20', 'ATR_14', 'ADX_14', 'Keltner_Channels_20'],
    'volume': ['VWAP', 'OBV', 'MFI_14', 'Volume_Oscillator', 'AD_Line', 'Chaikin_Oscillator', 'VWMA_20', 'Klinger_Oscillator'],
    'price_volume': ['Force_Index', 'Ease_of_Movement', 'NVI', 'PVI']
}

ALL_INDICATORS = [ind for cat in INDICATOR_CATEGORIES.values() for ind in cat]


def print_indicators(result: dict, category: str = None):
    """Pretty print indicators."""
    indicators = result.get('indicators', {})
    symbol = result.get('symbol', 'UNKNOWN')
    timeframe = result.get('timeframe', '1h')
    price = result.get('current_price', 0)

    print(f"\n{'═' * 72}")
    print(f"  Technical Analysis │ {symbol} │ {timeframe} │ ${price:.4f}")
    print(f"{'═' * 72}")

    categories = INDICATOR_CATEGORIES if category is None else {category: INDICATOR_CATEGORIES.get(category, [])}

    for cat_name, cat_indicators in categories.items():
        print(f"\n  📊 {cat_name.upper()}")
        print(f"  {'─' * 68}")

        for ind_name in cat_indicators:
            if ind_name in indicators:
                data = indicators[ind_name]
                if isinstance(data, dict):
                    values = ' | '.join([f"{k}: {v}" for k, v in data.items() if k not in ['signal', 'trend', 'direction', 'position', 'strength']][:3])
                    signal = data.get('signal') or data.get('direction') or data.get('trend') or data.get('position') or data.get('strength')
                    if signal:
                        icon = "🟢" if signal in ['BUY', 'BULLISH', 'UP', 'ABOVE', 'ABOVE_UPPER', 'STRONG', 'INCREASING'] else \
                               "🔴" if signal in ['SELL', 'BEARISH', 'DOWN', 'BELOW', 'BELOW_LOWER', 'WEAK', 'DECREASING'] else "⚪"
                        print(f"  {icon} {ind_name:<20} {values:<35} [{signal}]")
                    else:
                        print(f"  ⚪ {ind_name:<20} {values}")

    print(f"\n{'─' * 72}")
    print(f"  Total: {len(indicators)} indicators calculated")
    print(f"{'═' * 72}")


async def main():
    parser = argparse.ArgumentParser(description="CCXT Crypto Technical Indicators")
    parser.add_argument("symbol", nargs="?", help="Trading pair (e.g., BTC, ETH)")
    parser.add_argument("--timeframe", default="1h", help="Timeframe (default: 1h)")
    parser.add_argument("--limit", type=int, default=100, help="Candle count (default: 100)")
    parser.add_argument("--exchange", default="binance", help="Exchange (default: binance)")
    parser.add_argument("--indicator", help="Specific indicator to calculate")
    parser.add_argument("--category", choices=['trend', 'momentum', 'volatility', 'volume', 'price_volume'],
                       help="Indicator category")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", action="store_true", help="List all available indicators")
    args = parser.parse_args()

    if args.list:
        print("\n📋 Available Technical Indicators (26 total)\n")
        for cat, indicators in INDICATOR_CATEGORIES.items():
            print(f"  {cat.upper()} ({len(indicators)}):")
            for ind in indicators:
                print(f"    • {ind}")
        print()
        return

    try:
        # Fetch data
        print(f"Fetching {args.timeframe} data for {args.symbol} from {args.exchange}...", file=sys.stderr)
        df = await fetch_ohlcv(args.symbol, args.timeframe, args.limit, args.exchange)

        if len(df) < 55:
            print(f"ERROR: Need at least 55 candles, got {len(df)}")
            sys.exit(1)

        # Calculate indicators
        ti = TechnicalIndicators(df)

        if args.indicator:
            method = getattr(ti, args.indicator.lower(), None)
            if method:
                result = {
                    'symbol': args.symbol.upper(),
                    'timeframe': args.timeframe,
                    'current_price': float(df['close'].iloc[-1]),
                    'indicators': {args.indicator: method()}
                }
            else:
                print(f"ERROR: Unknown indicator '{args.indicator}'")
                sys.exit(1)
        else:
            result = {
                'symbol': args.symbol.upper(),
                'timeframe': args.timeframe,
                'current_price': float(df['close'].iloc[-1]),
                'candle_count': len(df),
                'datetime': df.index[-1].isoformat(),
                'indicators': ti.calculate_all()
            }

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print_indicators(result, args.category)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
