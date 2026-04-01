# advanced_indicators.py
# 進階技術指標計算模組，專注於成交量分析和更多技術指標

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    計算成交量加權平均價格 (Volume Weighted Average Price)
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return vwap

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    計算平衡成交量 (On Balance Volume)
    """
    obv = pd.Series(index=df.index, dtype='float64')
    obv.iloc[0] = df['volume'].iloc[0]
    
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv

def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    計算資金流量指標 (Money Flow Index)
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    raw_money_flow = typical_price * df['volume']
    
    # 計算正負資金流量
    positive_flow = pd.Series(index=df.index, dtype='float64')
    negative_flow = pd.Series(index=df.index, dtype='float64')
    
    for i in range(1, len(df)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            positive_flow.iloc[i] = raw_money_flow.iloc[i]
            negative_flow.iloc[i] = 0
        elif typical_price.iloc[i] < typical_price.iloc[i-1]:
            positive_flow.iloc[i] = 0
            negative_flow.iloc[i] = raw_money_flow.iloc[i]
        else:
            positive_flow.iloc[i] = 0
            negative_flow.iloc[i] = 0
    
    positive_flow = positive_flow.rolling(window=period).sum()
    negative_flow = negative_flow.rolling(window=period).sum()
    
    money_flow_ratio = positive_flow / negative_flow
    mfi = 100 - (100 / (1 + money_flow_ratio))
    
    return mfi.fillna(50)

def calculate_volume_oscillator(df: pd.DataFrame, short_period: int = 5, long_period: int = 10) -> pd.Series:
    """
    計算成交量震盪指標 (Volume Oscillator)
    """
    short_vol_ma = df['volume'].rolling(window=short_period).mean()
    long_vol_ma = df['volume'].rolling(window=long_period).mean()
    
    volume_oscillator = ((short_vol_ma - long_vol_ma) / long_vol_ma) * 100
    return volume_oscillator

def calculate_accumulation_distribution(df: pd.DataFrame) -> pd.Series:
    """
    計算累積分佈線 (Accumulation/Distribution Line)
    """
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    clv = clv.fillna(0)  # 處理高低價相等的情況
    
    ad_line = (clv * df['volume']).cumsum()
    return ad_line

def calculate_chaikin_oscillator(df: pd.DataFrame, fast_period: int = 3, slow_period: int = 10) -> pd.Series:
    """
    計算蔡金震盪指標 (Chaikin Oscillator)
    """
    ad_line = calculate_accumulation_distribution(df)
    fast_ema = ad_line.ewm(span=fast_period).mean()
    slow_ema = ad_line.ewm(span=slow_period).mean()
    
    chaikin_osc = fast_ema - slow_ema
    return chaikin_osc

def calculate_volume_profile(df: pd.DataFrame, price_bins: int = 50) -> Dict[str, any]:
    """
    計算成交量分佈圖 (Volume Profile)
    """
    # 計算價格區間
    price_min = df['low'].min()
    price_max = df['high'].max()
    price_step = (price_max - price_min) / price_bins
    
    volume_profile = {}
    
    for i in range(price_bins):
        price_level = price_min + i * price_step
        price_upper = price_min + (i + 1) * price_step
        
        # 找出在此價格區間內的交易
        mask = (df['low'] <= price_upper) & (df['high'] >= price_level)
        volume_at_level = df[mask]['volume'].sum()
        
        volume_profile[round(price_level, 2)] = volume_at_level
    
    # 找出成交量最大的價格區間 (POC - Point of Control)
    poc_price = max(volume_profile, key=volume_profile.get)
    
    return {
        'volume_profile': volume_profile,
        'poc_price': poc_price,
        'total_volume': df['volume'].sum()
    }

def calculate_trix(data: pd.Series, period: int = 14) -> pd.Series:
    """
    計算TRIX指標 (Triple Exponential Moving Average)
    """
    ema1 = data.ewm(span=period).mean()
    ema2 = ema1.ewm(span=period).mean()
    ema3 = ema2.ewm(span=period).mean()
    
    trix = ((ema3 - ema3.shift(1)) / ema3.shift(1)) * 10000
    return trix

def calculate_parabolic_sar(df: pd.DataFrame, acceleration: float = 0.02, max_acceleration: float = 0.2) -> pd.Series:
    """
    計算拋物線轉向指標 (Parabolic SAR)
    """
    sar = pd.Series(index=df.index, dtype='float64')
    af = acceleration
    ep = df['high'].iloc[0]  # 極值點
    trend = 1  # 1為上升趨勢，-1為下降趨勢
    
    sar.iloc[0] = df['low'].iloc[0]
    
    for i in range(1, len(df)):
        if trend == 1:  # 上升趨勢
            sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
            
            if df['high'].iloc[i] > ep:
                ep = df['high'].iloc[i]
                af = min(af + acceleration, max_acceleration)
            
            if df['low'].iloc[i] < sar.iloc[i]:
                trend = -1
                sar.iloc[i] = ep
                ep = df['low'].iloc[i]
                af = acceleration
        else:  # 下降趨勢
            sar.iloc[i] = sar.iloc[i-1] - af * (sar.iloc[i-1] - ep)
            
            if df['low'].iloc[i] < ep:
                ep = df['low'].iloc[i]
                af = min(af + acceleration, max_acceleration)
            
            if df['high'].iloc[i] > sar.iloc[i]:
                trend = 1
                sar.iloc[i] = ep
                ep = df['high'].iloc[i]
                af = acceleration
    
    return sar

def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> Dict[str, pd.Series]:
    """
    計算凱爾特納通道 (Keltner Channels)
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    middle_line = typical_price.ewm(span=period).mean()
    
    # 計算ATR
    df_temp = df.copy()
    df_temp['H-L'] = df_temp['high'] - df_temp['low']
    df_temp['H-pC'] = np.abs(df_temp['high'] - df_temp['close'].shift(1))
    df_temp['L-pC'] = np.abs(df_temp['low'] - df_temp['close'].shift(1))
    df_temp['TR'] = df_temp[['H-L', 'H-pC', 'L-pC']].max(axis=1)
    atr = df_temp['TR'].ewm(span=period).mean()
    
    upper_channel = middle_line + (multiplier * atr)
    lower_channel = middle_line - (multiplier * atr)
    
    return {
        'upper': upper_channel,
        'middle': middle_line,
        'lower': lower_channel,
        'atr': atr
    }

def calculate_ichimoku_cloud(df: pd.DataFrame, 
                           tenkan_period: int = 9, 
                           kijun_period: int = 26, 
                           senkou_span_b_period: int = 52) -> Dict[str, pd.Series]:
    """
    計算一目均衡表 (Ichimoku Cloud)
    """
    # 轉換線 (Tenkan-sen)
    tenkan_sen = ((df['high'].rolling(window=tenkan_period).max() + 
                   df['low'].rolling(window=tenkan_period).min()) / 2)
    
    # 基準線 (Kijun-sen)
    kijun_sen = ((df['high'].rolling(window=kijun_period).max() + 
                  df['low'].rolling(window=kijun_period).min()) / 2)
    
    # 先行帶A (Senkou Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
    
    # 先行帶B (Senkou Span B)
    senkou_span_b = ((df['high'].rolling(window=senkou_span_b_period).max() + 
                      df['low'].rolling(window=senkou_span_b_period).min()) / 2).shift(kijun_period)
    
    # 遲行帶 (Chikou Span)
    chikou_span = df['close'].shift(-kijun_period)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }

def calculate_force_index(df: pd.DataFrame, period: int = 13) -> pd.Series:
    """
    計算力量指標 (Force Index)
    """
    force_index = (df['close'] - df['close'].shift(1)) * df['volume']
    force_index_ma = force_index.ewm(span=period).mean()
    return force_index_ma

def calculate_ease_of_movement(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    計算簡易波動指標 (Ease of Movement)
    """
    distance_moved = ((df['high'] + df['low']) / 2) - ((df['high'].shift(1) + df['low'].shift(1)) / 2)
    box_height = (df['volume'] / 100000000) / (df['high'] - df['low'])
    
    # 避免除零錯誤
    box_height = box_height.replace([np.inf, -np.inf], 0)
    
    em = distance_moved / box_height
    em = em.replace([np.inf, -np.inf], 0)
    
    ease_of_movement = em.rolling(window=period).mean()
    return ease_of_movement

def calculate_negative_volume_index(df: pd.DataFrame) -> pd.Series:
    """
    計算負成交量指標 (Negative Volume Index)
    """
    nvi = pd.Series(index=df.index, dtype='float64')
    nvi.iloc[0] = 1000  # 起始值設為1000
    
    for i in range(1, len(df)):
        if df['volume'].iloc[i] < df['volume'].iloc[i-1]:
            nvi.iloc[i] = nvi.iloc[i-1] * (df['close'].iloc[i] / df['close'].iloc[i-1])
        else:
            nvi.iloc[i] = nvi.iloc[i-1]
    
    return nvi

def calculate_positive_volume_index(df: pd.DataFrame) -> pd.Series:
    """
    計算正成交量指標 (Positive Volume Index)
    """
    pvi = pd.Series(index=df.index, dtype='float64')
    pvi.iloc[0] = 1000  # 起始值設為1000
    
    for i in range(1, len(df)):
        if df['volume'].iloc[i] > df['volume'].iloc[i-1]:
            pvi.iloc[i] = pvi.iloc[i-1] * (df['close'].iloc[i] / df['close'].iloc[i-1])
        else:
            pvi.iloc[i] = pvi.iloc[i-1]
    
    return pvi

def calculate_volume_weighted_moving_average(data: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
    """
    計算成交量加權移動平均線 (Volume Weighted Moving Average)
    """
    def vwma_func(price_vol_window):
        prices = price_vol_window['price']
        volumes = price_vol_window['volume']
        return (prices * volumes).sum() / volumes.sum()
    
    df_temp = pd.DataFrame({'price': data, 'volume': volume})
    vwma = df_temp.rolling(window=period).apply(vwma_func, raw=False)['price']
    
    return vwma

def calculate_klinger_oscillator(df: pd.DataFrame, fast_period: int = 34, slow_period: int = 55, signal_period: int = 13) -> Dict[str, pd.Series]:
    """
    計算克林格震盪指標 (Klinger Oscillator)
    """
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    hlc3_prev = hlc3.shift(1)
    
    # 計算趨勢
    trend = pd.Series(index=df.index, dtype='int')
    trend.iloc[0] = 1
    
    for i in range(1, len(df)):
        if hlc3.iloc[i] > hlc3_prev.iloc[i]:
            trend.iloc[i] = 1
        elif hlc3.iloc[i] < hlc3_prev.iloc[i]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i-1]
    
    # 計算成交量力度 (Volume Force)
    vf = df['volume'] * trend * ((hlc3 - hlc3_prev) / hlc3_prev * 100)
    vf = vf.fillna(0)
    
    # 計算快速和慢速EMA
    fast_ema = vf.ewm(span=fast_period).mean()
    slow_ema = vf.ewm(span=slow_period).mean()
    
    klinger = fast_ema - slow_ema
    signal = klinger.ewm(span=signal_period).mean()
    
    return {
        'klinger': klinger,
        'signal': signal,
        'histogram': klinger - signal
    }

def calculate_advanced_volume_indicators(df: pd.DataFrame) -> Dict[str, any]:
    """
    計算所有進階成交量指標的綜合函數
    """
    indicators = {}
    
    try:
        indicators['VWAP'] = calculate_vwap(df)
        indicators['OBV'] = calculate_obv(df)
        indicators['MFI'] = calculate_mfi(df)
        indicators['Volume_Oscillator'] = calculate_volume_oscillator(df)
        indicators['AD_Line'] = calculate_accumulation_distribution(df)
        indicators['Chaikin_Oscillator'] = calculate_chaikin_oscillator(df)
        indicators['Force_Index'] = calculate_force_index(df)
        indicators['Ease_of_Movement'] = calculate_ease_of_movement(df)
        indicators['NVI'] = calculate_negative_volume_index(df)
        indicators['PVI'] = calculate_positive_volume_index(df)
        indicators['VWMA'] = calculate_volume_weighted_moving_average(df['close'], df['volume'])
        
        # 克林格震盪指標
        klinger_data = calculate_klinger_oscillator(df)
        indicators['Klinger_Oscillator'] = klinger_data['klinger']
        indicators['Klinger_Signal'] = klinger_data['signal']
        indicators['Klinger_Histogram'] = klinger_data['histogram']
        
        # 成交量分佈圖
        volume_profile = calculate_volume_profile(df)
        indicators['Volume_Profile'] = volume_profile
        
    except Exception as e:
        print(f"計算進階成交量指標時發生錯誤: {e}")
    
    return indicators

def calculate_all_advanced_indicators(df: pd.DataFrame) -> Dict[str, any]:
    """
    計算所有進階技術指標的綜合函數
    """
    indicators = {}
    
    try:
        # 成交量指標
        volume_indicators = calculate_advanced_volume_indicators(df)
        indicators.update(volume_indicators)
        
        # 其他進階指標
        indicators['TRIX'] = calculate_trix(df['close'])
        indicators['Parabolic_SAR'] = calculate_parabolic_sar(df)
        
        # 凱爾特納通道
        keltner_data = calculate_keltner_channels(df)
        indicators['Keltner_Upper'] = keltner_data['upper']
        indicators['Keltner_Middle'] = keltner_data['middle']
        indicators['Keltner_Lower'] = keltner_data['lower']
        
        # 一目均衡表
        ichimoku_data = calculate_ichimoku_cloud(df)
        indicators['Ichimoku_Tenkan'] = ichimoku_data['tenkan_sen']
        indicators['Ichimoku_Kijun'] = ichimoku_data['kijun_sen']
        indicators['Ichimoku_Senkou_A'] = ichimoku_data['senkou_span_a']
        indicators['Ichimoku_Senkou_B'] = ichimoku_data['senkou_span_b']
        indicators['Ichimoku_Chikou'] = ichimoku_data['chikou_span']
        
    except Exception as e:
        print(f"計算進階技術指標時發生錯誤: {e}")
    
    return indicators

def get_indicator_interpretation(indicator_name: str, current_value: float, previous_value: float = None, 
                               price: float = None, **kwargs) -> Dict[str, str]:
    """
    提供技術指標的解釋和交易信號
    """
    interpretation = {
        'signal': 'NEUTRAL',
        'strength': 'MEDIUM',
        'description': ''
    }
    
    try:
        if indicator_name == 'MFI':
            if current_value > 80:
                interpretation.update({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'description': f'資金流量指標 ({current_value:.1f}) 處於超買區間，建議賣出'
                })
            elif current_value < 20:
                interpretation.update({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'description': f'資金流量指標 ({current_value:.1f}) 處於超賣區間，建議買入'
                })
            else:
                interpretation['description'] = f'資金流量指標 ({current_value:.1f}) 處於正常範圍'
        
        elif indicator_name == 'VWAP':
            if price and current_value:
                if price > current_value:
                    interpretation.update({
                        'signal': 'BUY',
                        'strength': 'MEDIUM',
                        'description': f'價格高於VWAP ({current_value:.2f})，顯示買盤強勁'
                    })
                else:
                    interpretation.update({
                        'signal': 'SELL',
                        'strength': 'MEDIUM',
                        'description': f'價格低於VWAP ({current_value:.2f})，顯示賣盤強勁'
                    })
        
        elif indicator_name == 'Chaikin_Oscillator':
            if current_value > 0 and previous_value and previous_value < 0:
                interpretation.update({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'description': '蔡金震盪指標由負轉正，顯示買盤增強'
                })
            elif current_value < 0 and previous_value and previous_value > 0:
                interpretation.update({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'description': '蔡金震盪指標由正轉負，顯示賣盤增強'
                })
        
        elif indicator_name == 'Klinger_Oscillator':
            klinger_signal = kwargs.get('signal_value', 0)
            if current_value > klinger_signal:
                interpretation.update({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'description': '克林格震盪指標高於信號線，顯示買盤強勁'
                })
            else:
                interpretation.update({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'description': '克林格震盪指標低於信號線，顯示賣盤強勁'
                })
        
        elif indicator_name == 'Force_Index':
            if current_value > 0 and previous_value and previous_value < 0:
                interpretation.update({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'description': '力量指標由負轉正，顯示買盤力量增強'
                })
            elif current_value < 0 and previous_value and previous_value > 0:
                interpretation.update({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'description': '力量指標由正轉負，顯示賣盤力量增強'
                })
        
    except Exception as e:
        interpretation['description'] = f'解釋指標時發生錯誤: {str(e)}'
    
    return interpretation
