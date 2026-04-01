# 進階成交量指標模組
# Volume-based Technical Indicators using Tiingo API data

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    計算成交量加權平均價格 (Volume Weighted Average Price)
    
    VWAP 是一個重要的交易基準，顯示股票在特定時期的平均成交價格，
    並按成交量加權。當價格高於 VWAP 時，通常被視為看漲信號。
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return vwap.ffill()

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    計算平衡成交量 (On Balance Volume)
    
    OBV 是一個動量指標，結合價格和成交量的變化。
    當收盤價上漲時，該日成交量被視為正值；
    當收盤價下跌時，該日成交量被視為負值。
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
    
    MFI 是一個基於價格和成交量的動量振蕩指標，類似於 RSI。
    數值範圍從 0 到 100，通常 80 以上為超買，20 以下為超賣。
    """
    try:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']
        
        # 計算正負資金流量
        positive_flow = pd.Series(0.0, index=df.index)
        negative_flow = pd.Series(0.0, index=df.index)
        
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = raw_money_flow.iloc[i]
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                negative_flow.iloc[i] = raw_money_flow.iloc[i]
        
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        # 避免除零錯誤
        money_flow_ratio = positive_mf / negative_mf.replace(0, np.nan)
        mfi = 100 - (100 / (1 + money_flow_ratio))
        
        return mfi.fillna(50)
    except Exception as e:
        print(f"計算 MFI 時發生錯誤: {e}")
        return pd.Series(50.0, index=df.index)

def calculate_volume_oscillator(df: pd.DataFrame, short_period: int = 5, long_period: int = 10) -> pd.Series:
    """
    計算成交量震盪指標 (Volume Oscillator)
    
    成交量震盪指標衡量短期成交量移動平均線與長期成交量移動平均線之間的關係。
    正值表示成交量增加，負值表示成交量減少。
    """
    short_vol_ma = df['volume'].rolling(window=short_period).mean()
    long_vol_ma = df['volume'].rolling(window=long_period).mean()
    
    volume_oscillator = ((short_vol_ma - long_vol_ma) / long_vol_ma) * 100
    return volume_oscillator.fillna(0)

def calculate_accumulation_distribution(df: pd.DataFrame) -> pd.Series:
    """
    計算累積分佈線 (Accumulation/Distribution Line)
    
    A/D 線是一個基於成交量的指標，用於確定資金是否流入（累積）或流出（分佈）股票。
    該指標結合了價格和成交量，以顯示資金流動的方向。
    """
    # 避免除零錯誤
    high_low_diff = df['high'] - df['low']
    high_low_diff = high_low_diff.replace(0, np.nan)
    
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / high_low_diff
    clv = clv.fillna(0)  # 處理高低價相等的情況
    
    ad_line = (clv * df['volume']).cumsum()
    return ad_line

def calculate_chaikin_oscillator(df: pd.DataFrame, fast_period: int = 3, slow_period: int = 10) -> pd.Series:
    """
    計算蔡金震盪指標 (Chaikin Oscillator)
    
    蔡金震盪指標是 A/D 線的動量指標，通過計算 A/D 線的快速 EMA 和慢速 EMA 之差得出。
    正值表示買盤壓力，負值表示賣盤壓力。
    """
    ad_line = calculate_accumulation_distribution(df)
    fast_ema = ad_line.ewm(span=fast_period).mean()
    slow_ema = ad_line.ewm(span=slow_period).mean()
    
    chaikin_osc = fast_ema - slow_ema
    return chaikin_osc.fillna(0)

def calculate_force_index(df: pd.DataFrame, period: int = 13) -> pd.Series:
    """
    計算力量指標 (Force Index)
    
    力量指標結合價格變化和成交量，衡量每次價格變動背後的力量。
    正值表示買盤力量強勁，負值表示賣盤力量強勁。
    """
    price_change = df['close'].diff()
    force_index = price_change * df['volume']
    
    # 使用 EMA 平滑化
    force_index_smoothed = force_index.ewm(span=period).mean()
    return force_index_smoothed.fillna(0)

def calculate_volume_weighted_moving_average(data: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
    """
    計算成交量加權移動平均線 (Volume Weighted Moving Average)
    
    VWMA 給予成交量較大的價格更多權重，比簡單移動平均線更能反映市場活動。
    """
    def vwma_calc(window_data):
        prices = window_data['price']
        volumes = window_data['volume']
        if volumes.sum() == 0:
            return prices.mean()
        return (prices * volumes).sum() / volumes.sum()
    
    df_temp = pd.DataFrame({'price': data, 'volume': volume})
    vwma = df_temp.rolling(window=period).apply(vwma_calc, raw=False)['price']
    
    return vwma.ffill()

def get_volume_indicators_analysis(df: pd.DataFrame, periods: Optional[Dict[str, int]] = None) -> Dict[str, any]:
    """
    計算所有成交量技術指標的綜合分析
    
    Args:
        df: 包含 OHLCV 數據的 DataFrame
        periods: 各指標的自定義週期參數
    
    Returns:
        包含所有成交量指標結果的字典
    """
    if periods is None:
        periods = {
            'MFI': 14,
            'VOLUME_OSC_SHORT': 5,
            'VOLUME_OSC_LONG': 10,
            'CHAIKIN_FAST': 3,
            'CHAIKIN_SLOW': 10,
            'FORCE_INDEX': 13,
            'VWMA': 20
        }
    
    results = {}
    
    try:
        # 基本成交量指標
        results['VWAP'] = calculate_vwap(df)
        results['OBV'] = calculate_obv(df)
        results['MFI'] = calculate_mfi(df, periods.get('MFI', 14))
        results['Volume_Oscillator'] = calculate_volume_oscillator(
            df, 
            periods.get('VOLUME_OSC_SHORT', 5), 
            periods.get('VOLUME_OSC_LONG', 10)
        )
        results['AD_Line'] = calculate_accumulation_distribution(df)
        results['Chaikin_Oscillator'] = calculate_chaikin_oscillator(
            df,
            periods.get('CHAIKIN_FAST', 3),
            periods.get('CHAIKIN_SLOW', 10)
        )
        results['Force_Index'] = calculate_force_index(df, periods.get('FORCE_INDEX', 13))
        results['VWMA'] = calculate_volume_weighted_moving_average(
            df['close'], 
            df['volume'], 
            periods.get('VWMA', 20)
        )
        
        # 當前值和信號解釋
        current_analysis = generate_volume_signals(results, df)
        results['analysis'] = current_analysis
        
    except Exception as e:
        results['error'] = f"計算成交量指標時發生錯誤: {str(e)}"
    
    return results

def generate_volume_signals(indicators: Dict[str, pd.Series], df: pd.DataFrame) -> Dict[str, any]:
    """
    基於成交量指標生成交易信號和市場分析
    """
    analysis = {
        'overall_volume_trend': 'NEUTRAL',
        'money_flow_signal': 'NEUTRAL',
        'accumulation_distribution': 'NEUTRAL',
        'volume_strength': 'MEDIUM',
        'key_observations': [],
        'trading_signals': []
    }
    
    try:
        current_price = df['close'].iloc[-1]
        
        # VWAP 分析
        if 'VWAP' in indicators:
            vwap_current = indicators['VWAP'].iloc[-1]
            vwap_deviation = ((current_price - vwap_current) / vwap_current) * 100
            
            if abs(vwap_deviation) > 2:
                analysis['key_observations'].append(
                    f"價格相對於 VWAP {'高出' if vwap_deviation > 0 else '低於'} {abs(vwap_deviation):.1f}%"
                )
                if vwap_deviation > 2:
                    analysis['trading_signals'].append("價格大幅高於 VWAP，注意回調風險")
                elif vwap_deviation < -2:
                    analysis['trading_signals'].append("價格大幅低於 VWAP，可能存在買入機會")
        
        # MFI 分析
        if 'MFI' in indicators:
            mfi_current = indicators['MFI'].iloc[-1]
            if mfi_current > 80:
                analysis['money_flow_signal'] = 'OVERBOUGHT'
                analysis['key_observations'].append(f"資金流量指標 ({mfi_current:.1f}) 顯示超買")
                analysis['trading_signals'].append("MFI 超買，建議謹慎或考慮減倉")
            elif mfi_current < 20:
                analysis['money_flow_signal'] = 'OVERSOLD'
                analysis['key_observations'].append(f"資金流量指標 ({mfi_current:.1f}) 顯示超賣")
                analysis['trading_signals'].append("MFI 超賣，可能存在買入機會")
        
        # OBV 趨勢分析
        if 'OBV' in indicators and len(indicators['OBV']) > 5:
            obv_recent = indicators['OBV'].iloc[-5:]
            obv_trend = 'UP' if obv_recent.iloc[-1] > obv_recent.iloc[0] else 'DOWN'
            
            price_recent = df['close'].iloc[-5:]
            price_trend = 'UP' if price_recent.iloc[-1] > price_recent.iloc[0] else 'DOWN'
            
            if obv_trend == 'UP' and price_trend == 'UP':
                analysis['overall_volume_trend'] = 'BULLISH'
                analysis['key_observations'].append("OBV 和價格同步上升，顯示健康的上升趨勢")
            elif obv_trend == 'DOWN' and price_trend == 'DOWN':
                analysis['overall_volume_trend'] = 'BEARISH'
                analysis['key_observations'].append("OBV 和價格同步下降，顯示明確的下降趨勢")
            elif obv_trend != price_trend:
                analysis['key_observations'].append("OBV 和價格出現背離，需要關注趨勢轉變")
                analysis['trading_signals'].append("成交量與價格背離，謹慎操作")
        
        # 蔡金震盪指標分析
        if 'Chaikin_Oscillator' in indicators:
            chaikin_current = indicators['Chaikin_Oscillator'].iloc[-1]
            chaikin_prev = indicators['Chaikin_Oscillator'].iloc[-2] if len(indicators['Chaikin_Oscillator']) > 1 else 0
            
            if chaikin_current > 0 and chaikin_prev <= 0:
                analysis['accumulation_distribution'] = 'ACCUMULATION'
                analysis['trading_signals'].append("蔡金震盪指標轉正，顯示累積階段")
            elif chaikin_current < 0 and chaikin_prev >= 0:
                analysis['accumulation_distribution'] = 'DISTRIBUTION'
                analysis['trading_signals'].append("蔡金震盪指標轉負，顯示分佈階段")
        
        # 成交量強度評估
        if 'Volume_Oscillator' in indicators:
            vol_osc_current = indicators['Volume_Oscillator'].iloc[-1]
            if vol_osc_current > 20:
                analysis['volume_strength'] = 'HIGH'
                analysis['key_observations'].append("成交量明顯高於平均水平")
            elif vol_osc_current < -20:
                analysis['volume_strength'] = 'LOW'
                analysis['key_observations'].append("成交量明顯低於平均水平")
        
    except Exception as e:
        analysis['error'] = f"生成成交量信號時發生錯誤: {str(e)}"
    
    return analysis

def get_volume_indicator_description(indicator_name: str) -> str:
    """
    返回成交量指標的詳細說明
    """
    descriptions = {
        'VWAP': '成交量加權平均價格，是重要的交易基準。價格高於 VWAP 通常被視為看漲信號。',
        'OBV': '平衡成交量，結合價格和成交量變化的動量指標。上升趨勢伴隨 OBV 上升表示健康趨勢。',
        'MFI': '資金流量指標，類似於基於成交量的 RSI。80 以上超買，20 以下超賣。',
        'Volume_Oscillator': '成交量震盪指標，衡量短期與長期成交量的關係。正值表示成交量增加。',
        'AD_Line': '累積分佈線，用於判斷資金流入或流出。持續上升表示累積，下降表示分佈。',
        'Chaikin_Oscillator': '蔡金震盪指標，A/D 線的動量版本。正值表示買盤壓力，負值表示賣盤壓力。',
        'Force_Index': '力量指標，衡量價格變動背後的力量。結合價格變化和成交量。',
        'VWMA': '成交量加權移動平均線，給予高成交量的價格更多權重，比簡單移動平均線更敏感。'
    }
    
    return descriptions.get(indicator_name, f'{indicator_name} 的詳細說明暫未提供。')
