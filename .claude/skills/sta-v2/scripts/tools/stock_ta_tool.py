import os
import requests
import time
import random
from typing import Dict, Union, List, Any, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import re

# Import TA-Lib
import talib as ta

# Tiingo API 配置
TIINGO_API_KEY = os.getenv('TIINGO_API_KEY', "2146105fde5488455a958c98755941aafb9d9c66") # 請替換為您的 Tiingo API 金鑰

# 常見外匯對名稱映射
FOREX_NAMES = {
    "EURUSD": "Euro / US Dollar",
    "GBPUSD": "British Pound / US Dollar",
    "USDJPY": "US Dollar / Japanese Yen",
    "USDCHF": "US Dollar / Swiss Franc",
    "AUDUSD": "Australian Dollar / US Dollar",
    "USDCAD": "US Dollar / Canadian Dollar",
    "NZDUSD": "New Zealand Dollar / US Dollar",
    "EURJPY": "Euro / Japanese Yen",
    "GBPJPY": "British Pound / Japanese Yen",
    "EURGBP": "Euro / British Pound",
    "EURAUD": "Euro / Australian Dollar",
    "USDSGD": "US Dollar / Singapore Dollar",
    "USDHKD": "US Dollar / Hong Kong Dollar",
    "USDCNY": "US Dollar / Chinese Yuan",
    "XAUUSD": "Gold / US Dollar",
    "XAGUSD": "Silver / US Dollar",
}

def is_forex_ticker(ticker: str) -> bool:
    """
    判斷是否為外匯代碼（6字元貨幣對，如 EURUSD、GBPUSD）
    
    Args:
        ticker: 代碼字串
        
    Returns:
        True 如果是外匯對格式
    """
    t = ticker.strip().upper()
    # 標準 6 字元外匯對，或已知外匯對
    if t in FOREX_NAMES:
        return True
    # 通用規則：6 字元全英文字母（含貴金屬如 XAUUSD）
    if len(t) == 6 and t.isalpha():
        # 排除已知股票（例如 GOOGL 不是 6 字元，但做個保護）
        return True
    return False

def get_forex_data(pair: str, time_period: str = "365d") -> pd.DataFrame:
    """
    使用 Tiingo FX API 獲取外匯歷史數據。
    
    Args:
        pair: 貨幣對代碼（如 eurusd、EURUSD）
        time_period: 時間週期（支援 30d, 90d, 180d, 365d, 2y 等）
    
    Returns:
        包含 open/high/low/close 欄位的 DataFrame（無成交量）
    """
    try:
        if not TIINGO_API_KEY or TIINGO_API_KEY == "YOUR_TIINGO_API_KEY_HERE":
            raise ValueError("有效的 Tiingo API 金鑰未配置。")

        pair_lower = pair.strip().lower()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {TIINGO_API_KEY}'
        }

        # 計算起始日期
        days = 365
        if "d" in time_period:
            days = int(time_period.replace("d", ""))
        elif "y" in time_period:
            days = int(time_period.replace("y", "")) * 365

        now_utc = datetime.now(timezone.utc)
        # 多抓 250 天以供指標計算用
        start_date = (now_utc - timedelta(days=days + 250)).strftime('%Y-%m-%d')
        
        url = f"https://api.tiingo.com/tiingo/fx/{pair_lower}/prices"
        params = {
            'startDate': start_date,
            'resampleFreq': '1Day',  # Tiingo FX 使用 resampleFreq
        }
        
        print(f"使用 Tiingo FX API 獲取 {pair_lower} 數據: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:
            raise ValueError("Tiingo API 金鑰無效或未授權。")
        if response.status_code == 404:
            raise ValueError(f"Tiingo FX API 找不到貨幣對 {pair_lower}，請確認代碼是否正確（例如 eurusd）。")
        if response.status_code == 429:
            raise ValueError("Tiingo API 速率限制，請稍後再試。")
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list) or not data:
            raise ValueError(f"無法獲取 {pair_lower} 的外匯數據，API 未返回有效數據。")

        df = pd.DataFrame(data)
        
        # Tiingo FX 欄位：date, open, high, low, close（無 volume）
        col_map = {'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'}
        available = {k: v for k, v in col_map.items() if k in df.columns}
        df = df[list(available.keys())].rename(columns=available)
        
        # 增加假 volume 欄位（外匯無成交量，設為 NaN）
        df['volume'] = float('nan')
        
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)
        df.set_index('date', inplace=True)
        
        # 過濾到所需時間段
        filter_start = now_utc - timedelta(days=days)
        filtered = df[df.index >= filter_start].copy()
        
        if len(filtered) < 20:
            num_rows = min(len(df), max(days, 250))
            filtered = df.iloc[-num_rows:].copy()
            if len(filtered) < 20:
                raise ValueError(f"獲取 {pair_lower} 的外匯數據不足20行 ({len(filtered)}行)，無法進行分析。")

        print(f"成功獲取 {pair_lower} 外匯數據，共 {len(filtered)} 行")
        return filtered

    except requests.exceptions.RequestException as e:
        raise ValueError(f"獲取 {pair} 外匯數據時發生網路錯誤: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"獲取 {pair} 外匯數據時發生未預期錯誤: {str(e)}")

def is_intraday_frequency(time_period: str) -> bool:
    """
    檢查是否為日內時間頻率
    
    Args:
        time_period: 時間週期字符串
        
    Returns:
        True 如果是日內頻率，False 如果是日級或更長頻率
    """
    # 日內頻率格式：1min, 5min, 15min, 30min, 1hour, 2hour 等
    intraday_pattern = r'^\d+(?:min|hour)$'
    return bool(re.match(intraday_pattern, time_period.lower()))

def get_stock_data_yfinance(ticker: str, time_period: str = "365d") -> pd.DataFrame:
    """
    使用 yfinance 獲取股票日線數據（無 rate limit，免費）。

    Args:
        ticker: 股票代碼
        time_period: 日級頻率（如 "365d", "1y", "2y"）

    Returns:
        包含 open/high/low/close/volume 的 DataFrame（UTC-aware index）
    """
    import yfinance as yf

    period_map = {
        "1d": "1d", "5d": "5d", "30d": "1mo", "90d": "3mo",
        "180d": "6mo", "365d": "1y", "1y": "1y", "2y": "2y", "5y": "5y",
    }
    yf_period = period_map.get(time_period, "1y")

    ticker_map = {"GOOG": "GOOGL", "GOOGLE": "GOOGL", "AMAZON": "AMZN"}
    actual_ticker = ticker_map.get(ticker.strip().upper(), ticker.strip().upper())

    print(f"使用 yfinance 獲取 {actual_ticker} 數據 (period={yf_period})")
    df = yf.Ticker(actual_ticker).history(period=yf_period)

    if df.empty:
        raise ValueError(f"yfinance 無法獲取 {actual_ticker} 的數據")

    df.columns = [c.lower() for c in df.columns]
    df = df[['open', 'high', 'low', 'close', 'volume']].copy()

    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    else:
        df.index = df.index.tz_convert('UTC')

    if df.empty:
        raise ValueError(f"yfinance 獲取的 {actual_ticker} 數據為空")

    print(f"yfinance 成功獲取 {actual_ticker} 數據，共 {len(df)} 行")
    return df


def get_stock_data_tiingo(ticker: str, time_period: str = "365d") -> pd.DataFrame:
    """
    使用 Tiingo API 獲取股票數據（日線 + 日內頻率）。

    Args:
        ticker: 股票代碼
        time_period: 時間週期（日線或日內頻率）

    Returns:
        包含市場數據的 DataFrame
    """
    try:
        if not TIINGO_API_KEY or TIINGO_API_KEY == "YOUR_TIINGO_API_KEY_HERE":
            raise ValueError("有效的 Tiingo API 金鑰未配置。")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {TIINGO_API_KEY}'
        }

        # 標準化股票代碼並處理常見的映射
        ticker_processed = ticker.strip().upper()
        ticker_map = {
            "GOOG": "GOOGL",
            "GOOGLE": "GOOGL",
            "AMAZON": "AMZN"
        }
        actual_ticker = ticker_map.get(ticker_processed, ticker_processed)
        
        print(f"嘗試使用 Tiingo API 獲取 {actual_ticker} 的股票數據 (頻率: {time_period})")

        # 檢查是否為日內頻率
        if is_intraday_frequency(time_period):
            # 使用 IEX API 獲取日內數據
            url = f"https://api.tiingo.com/iex/{actual_ticker}/prices"
            params = {
                'resampleFreq': time_period,
                'format': 'json'
            }
            
            # IEX API 限制：最多返回 2000 個數據點
            print(f"使用 IEX API 獲取日內數據: {url} (頻率: {time_period})")
            
        else:
            # 使用傳統的日級 API
            days = 365  # 預設為一年
            if "d" in time_period:
                days = int(time_period.replace("d", ""))
            elif "m" in time_period:
                days = int(time_period.replace("m", "")) * 30
            elif "y" in time_period:
                days = int(time_period.replace("y", "")) * 365
            
            now_utc = datetime.now(timezone.utc)
            api_start_date_utc = now_utc - timedelta(days=days + 250)
            
            five_years_ago_utc = now_utc - timedelta(days=5*365)
            if api_start_date_utc < five_years_ago_utc:
                api_start_date_utc = five_years_ago_utc
                
            start_date_str = api_start_date_utc.strftime('%Y-%m-%d')
            
            url = f"https://api.tiingo.com/tiingo/daily/{actual_ticker}/prices"
            params = {
                'startDate': start_date_str,
                'format': 'json'
            }
            print(f"使用 Daily API 獲取日級數據: {url}")

        # 發送請求
        response = requests.get(url, headers=headers, params=params)
        # 請求已在上面發送
        
        if response.status_code == 401:
            raise ValueError(f"Tiingo API 金鑰無效或未授權。")
        if response.status_code == 429:
            raise ValueError(f"Tiingo API 速率限制。請稍後再試。")
        if response.status_code == 404:
            raise ValueError(f"Tiingo API 找不到股票代碼 {actual_ticker}。")

        response.raise_for_status() 
        
        data = response.json()

        if not isinstance(data, list) or not data:
            if isinstance(data, dict) and "detail" in data:
                raise ValueError(f"無法獲取 {actual_ticker} 的股票數據: Tiingo API 錯誤 - {data['detail']}")
            raise ValueError(f"無法獲取 {actual_ticker} (原始: {ticker}) 的股票數據。API 未返回有效數據。")

        df = pd.DataFrame(data)
        
        if df.empty:
            raise ValueError(f"從 Tiingo API 獲取的 {actual_ticker} 數據為空。")

        column_mapping = {
            'date': 'date', 'adjOpen': 'open', 'adjHigh': 'high',
            'adjLow': 'low', 'adjClose': 'close', 'adjVolume': 'volume'
        }
        required_tiingo_cols = list(column_mapping.keys())
        missing_cols = [col for col in required_tiingo_cols if col not in df.columns]
        if missing_cols:
            # 如果 adjVolume 不存在，嘗試使用 volume
            if 'adjVolume' in missing_cols and 'volume' in df.columns:
                print("警告: Tiingo API 返回數據中缺少 'adjVolume'，將嘗試使用 'volume'。")
                column_mapping['volume'] = 'volume' # 更新映射以使用 'volume'
                required_tiingo_cols.remove('adjVolume') # 從必要列中移除 adjVolume
                if 'volume' not in required_tiingo_cols: required_tiingo_cols.append('volume')
                missing_cols = [col for col in required_tiingo_cols if col not in df.columns] # 重新檢查
            
            if missing_cols: # 如果仍然有缺失列
                 raise ValueError(f"Tiingo API 返回的數據缺少必要欄位: {', '.join(missing_cols)}")


        df = df[list(column_mapping.keys())].rename(columns=column_mapping)
        
        df['date'] = pd.to_datetime(df['date']) # Tiingo 日期帶 'Z' 會解析為 UTC
        df.sort_values('date', inplace=True)
        df.set_index('date', inplace=True) # df.index 現在是 datetime64[ns, UTC]

        print(f"從 Tiingo 成功獲取 {actual_ticker} 的數據，共 {len(df)} 行，索引時區: {df.index.tz}")
        
        # --- 修改開始: 使用 UTC 感知的 filter_start_date ---
        filter_start_date_utc = now_utc - timedelta(days=days)
        # 現在 df.index (UTC) 和 filter_start_date_utc (UTC) 可以正確比較
        filtered_df = df[df.index >= filter_start_date_utc].copy()
        # --- 修改結束 ---
        
        if len(filtered_df) < 20:
            print(f"警告: 按 '{time_period}' 過濾後數據少於20行 ({len(filtered_df)}行)。嘗試使用更多可用數據。")
            num_rows_to_take = min(len(df), max(days, 250)) 
            filtered_df = df.iloc[-num_rows_to_take:].copy()
            if len(filtered_df) < 20:
                 raise ValueError(f"獲取 {actual_ticker} 的股票數據不足20行 ({len(filtered_df)}行)，無法進行分析。")

        print(f"最終用於分析的數據集: {len(filtered_df)} 行，日期範圍: {filtered_df.index.min()} 至 {filtered_df.index.max()}")
        return filtered_df
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"獲取股票數據時發生網路請求錯誤: {error_msg}")
        raise ValueError(f"獲取 {ticker} 的股票數據時 (Tiingo API) 發生網路錯誤: {error_msg}")
    except ValueError as e:
        error_msg = str(e)
        print(f"獲取股票數據時發生錯誤: {error_msg}")
        raise ValueError(f"獲取 {ticker} 的股票數據時 (Tiingo API) 出錯: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        print(f"獲取股票數據時發生未預期錯誤: {error_msg}")
        raise ValueError(f"獲取 {ticker} 的股票數據時 (Tiingo API) 發生未預期錯誤: {error_msg}")


def get_stock_data(ticker: str, time_period: str = "365d") -> pd.DataFrame:
    """
    獲取股票或外匯數據，路由策略：
    - 外匯 → Tiingo FX API
    - 日內頻率 → Tiingo IEX API
    - 股票日線 → yfinance（優先）→ Tiingo（fallback）

    Args:
        ticker: 股票代碼或外匯對（如 EURUSD）
        time_period: 時間週期

    Returns:
        包含市場數據的 DataFrame
    """
    if is_forex_ticker(ticker):
        return get_forex_data(ticker, time_period)

    if is_intraday_frequency(time_period):
        return get_stock_data_tiingo(ticker, time_period)

    # 股票日線：yfinance 優先，Tiingo 備份
    try:
        return get_stock_data_yfinance(ticker, time_period)
    except Exception as e:
        print(f"yfinance 失敗 ({e})，回退到 Tiingo...")
        return get_stock_data_tiingo(ticker, time_period)


# === TA-Lib 技術指標計算函數 ===

def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """計算簡單移動平均線 (SMA)"""
    return ta.SMA(data, timeperiod=period)

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """計算指數移動平均線 (EMA)"""
    return ta.EMA(data, timeperiod=period)

def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """計算相對強弱指標 (RSI)"""
    return ta.RSI(data, timeperiod=period)

def calculate_macd_detailed(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    """計算 MACD 指標 (詳細版本)"""
    macd, macdsignal, macdhist = ta.MACD(data, fastperiod=fast, slowperiod=slow, signalperiod=signal)
    return {
        'MACD': macd,
        'Signal': macdsignal,
        'Histogram': macdhist
    }

def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
    """計算布林通道"""
    upper, middle, lower = ta.BBANDS(data, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev, matype=ta.MA_Type.SMA)
    
    # Calculate %B
    percent_b = (data - lower) / (upper - lower)
    
    return {
        'Middle': middle,
        'Upper': upper,
        'Lower': lower,
        'Width': upper - lower,
        'PercentB': percent_b
    }

def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
    """計算隨機指標 (Stochastic Oscillator)"""
    slowk, slowd = ta.STOCH(high, low, close, 
                            fastk_period=k_period, 
                            slowk_period=d_period, 
                            slowk_matype=ta.MA_Type.SMA, 
                            slowd_period=d_period, 
                            slowd_matype=ta.MA_Type.SMA)
    return {
        'K': slowk,
        'D': slowd
    }

def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """計算威廉指標 (Williams %R)"""
    return ta.WILLR(high, low, close, timeperiod=period)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """計算平均真實範圍 (ATR)"""
    return ta.ATR(df['high'], df['low'], df['close'], timeperiod=period)

def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """計算商品通道指標 (CCI)"""
    return ta.CCI(df['high'], df['low'], df['close'], timeperiod=period)

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """計算平均趨向指標 (ADX)"""
    return ta.ADX(df['high'], df['low'], df['close'], timeperiod=period)

# === 原有的函數 ===

def get_technical_indicators(ticker: str, indicators: List[str], periods: Optional[Dict[str, int]] = None, time_period: str = "365d") -> Dict[str, Any]:
    """
    獲取指定股票的技術指標
    
    Args:
        ticker: 股票代碼
        indicators: 要計算的技術指標列表 (例如: ['SMA', 'EMA', 'RSI', 'MACD'])
        periods: 各指標的週期參數 (可選)
        time_period: 數據時間範圍
    
    Returns:
        包含技術指標結果的字典
    """
    try:
        # print(f"DEBUG (stock_ta_tool.py): get_technical_indicators 函數入口 - ticker: {ticker}, indicators: {indicators}, periods: {periods}, time_period: {time_period}")  # 修復: 移除以避免污染 JSON 輸出
        # 獲取股票數據
        df = get_stock_data(ticker, time_period)
        
        if df.empty:
            # print(f"DEBUG (stock_ta_tool.py): get_stock_data 返回空 DataFrame for {ticker}")  # 修復: 移除以避免污染 JSON 輸出
            raise ValueError(f"無法獲取 {ticker} 的股票數據")
        
        # print(f"DEBUG (stock_ta_tool.py): 成功獲取 {ticker} 數據，共 {len(df)} 行。")  # 修復: 移除以避免污染 JSON 輸出
        # print(f"DEBUG (stock_ta_tool.py): DataFrame 列: {df.columns.tolist()}")  # 修復: 移除以避免污染 JSON 輸出
        # print(f"DEBUG (stock_ta_tool.py): DataFrame 索引時區: {df.index.tz}")  # 修復: 移除以避免污染 JSON 輸出

        # 設定預設週期
        default_periods = {
            'SMA': 20, 'EMA': 20, 'RSI': 14, 'MACD': 12,
            'BOLLINGER': 20, 'STOCHASTIC': 14, 'WILLIAMS_R': 14,
            'ADX': 14, 'ATR': 14, 'CCI': 20
        }
        
        if periods is None:
            periods = {}
        
        # 合併預設週期和自定義週期
        for indicator in indicators:
            if indicator.upper() not in periods:
                periods[indicator.upper()] = default_periods.get(indicator.upper(), 20)
        
        # print(f"DEBUG (stock_ta_tool.py): 最終使用的週期設置: {periods}")  # 修復: 移除以避免污染 JSON 輸出

        results = {
            'ticker': ticker.upper(),
            'company_name': get_stock_name(ticker),
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'current_price': round(float(df['close'].iloc[-1]), 2),
            'data_points': len(df),
            'indicators': {}
        }
        
        # 計算各種技術指標
        for indicator in indicators:
            indicator_upper = indicator.upper()
            period = periods.get(indicator_upper, default_periods.get(indicator_upper, 20)) # 使用 .get 避免 KeyError
            
            # print(f"DEBUG (stock_ta_tool.py): 計算指標 {indicator_upper}，週期: {period}")  # 修復: 移除以避免污染 JSON 輸出

            try:
                if indicator_upper == 'SMA':
                    sma_values = calculate_sma(df['close'], period)
                    # print(f"DEBUG (stock_ta_tool.py): SMA 計算完成，最後值: {sma_values.iloc[-1] if len(sma_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    results['indicators'][f'SMA_{period}'] = {
                        'current_value': round(float(sma_values.iloc[-1]), 2) if len(sma_values) > 0 and pd.notna(sma_values.iloc[-1]) else None,
                        'previous_value': round(float(sma_values.iloc[-2]), 2) if len(sma_values) > 1 and pd.notna(sma_values.iloc[-2]) else None,
                        'trend': 'UP' if len(sma_values) > 1 and pd.notna(sma_values.iloc[-1]) and pd.notna(sma_values.iloc[-2]) and sma_values.iloc[-1] > sma_values.iloc[-2] else 'DOWN' if len(sma_values) > 1 and pd.notna(sma_values.iloc[-1]) and pd.notna(sma_values.iloc[-2]) and sma_values.iloc[-1] < sma_values.iloc[-2] else 'NEUTRAL'
                    }
                    
                elif indicator_upper == 'EMA':
                    ema_values = calculate_ema(df['close'], period)
                    # print(f"DEBUG (stock_ta_tool.py): EMA 計算完成，最後值: {ema_values.iloc[-1] if len(ema_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    results['indicators'][f'EMA_{period}'] = {
                        'current_value': round(float(ema_values.iloc[-1]), 2) if len(ema_values) > 0 and pd.notna(ema_values.iloc[-1]) else None,
                        'previous_value': round(float(ema_values.iloc[-2]), 2) if len(ema_values) > 1 and pd.notna(ema_values.iloc[-2]) else None,
                        'trend': 'UP' if len(ema_values) > 1 and pd.notna(ema_values.iloc[-1]) and pd.notna(ema_values.iloc[-2]) and ema_values.iloc[-1] > ema_values.iloc[-2] else 'DOWN' if len(ema_values) > 1 and pd.notna(ema_values.iloc[-1]) and pd.notna(ema_values.iloc[-2]) and ema_values.iloc[-1] < ema_values.iloc[-2] else 'NEUTRAL'
                    }
                    
                elif indicator_upper == 'RSI':
                    rsi_values = calculate_rsi(df['close'], period)
                    # print(f"DEBUG (stock_ta_tool.py): RSI 計算完成，最後值: {rsi_values.iloc[-1] if len(rsi_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_rsi = float(rsi_values.iloc[-1]) if len(rsi_values) > 0 and pd.notna(rsi_values.iloc[-1]) else None
                    results['indicators'][f'RSI_{period}'] = {
                        'current_value': round(current_rsi, 2) if current_rsi is not None else None,
                        'signal': 'OVERBOUGHT' if current_rsi is not None and current_rsi > 70 else 'OVERSOLD' if current_rsi is not None and current_rsi < 30 else 'NEUTRAL',
                        'trend': 'UP' if len(rsi_values) > 1 and pd.notna(rsi_values.iloc[-1]) and pd.notna(rsi_values.iloc[-2]) and rsi_values.iloc[-1] > rsi_values.iloc[-2] else 'DOWN' if len(rsi_values) > 1 and pd.notna(rsi_values.iloc[-1]) and pd.notna(rsi_values.iloc[-2]) and rsi_values.iloc[-1] < rsi_values.iloc[-2] else 'NEUTRAL'
                    }
                    
                elif indicator_upper == 'MACD':
                    macd_data = calculate_macd_detailed(df['close'])
                    # print(f"DEBUG (stock_ta_tool.py): MACD 計算完成，最後值: MACD={macd_data['MACD'].iloc[-1] if len(macd_data['MACD']) > 0 else 'N/A'}, Signal={macd_data['Signal'].iloc[-1] if len(macd_data['Signal']) > 0 else 'N/A'}, Histogram={macd_data['Histogram'].iloc[-1] if len(macd_data['Histogram']) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_macd = float(macd_data['MACD'].iloc[-1]) if len(macd_data['MACD']) > 0 and pd.notna(macd_data['MACD'].iloc[-1]) else None
                    current_signal = float(macd_data['Signal'].iloc[-1]) if len(macd_data['Signal']) > 0 and pd.notna(macd_data['Signal'].iloc[-1]) else None
                    current_histogram = float(macd_data['Histogram'].iloc[-1]) if len(macd_data['Histogram']) > 0 and pd.notna(macd_data['Histogram'].iloc[-1]) else None
                    
                    results['indicators']['MACD'] = {
                        'MACD_line': round(current_macd, 4) if current_macd is not None else None,
                        'Signal_line': round(current_signal, 4) if current_signal is not None else None,
                        'Histogram': round(current_histogram, 4) if current_histogram is not None else None,
                        'signal': 'BUY' if current_macd is not None and current_signal is not None and current_macd > current_signal else 'SELL' if current_macd is not None and current_signal is not None and current_macd < current_signal else 'NEUTRAL',
                        'trend': 'BULLISH' if current_histogram is not None and current_histogram > 0 else 'BEARISH' if current_histogram is not None and current_histogram < 0 else 'NEUTRAL'
                    }
                    
                elif indicator_upper == 'BOLLINGER':
                    bb_data = calculate_bollinger_bands(df['close'], period)
                    # print(f"DEBUG (stock_ta_tool.py): BOLLINGER 計算完成，最後值: Upper={bb_data['Upper'].iloc[-1] if len(bb_data['Upper']) > 0 else 'N/A'}, Middle={bb_data['Middle'].iloc[-1] if len(bb_data['Middle']) > 0 else 'N/A'}, Lower={bb_data['Lower'].iloc[-1] if len(bb_data['Lower']) > 0 else 'N/A'}, PercentB={bb_data['PercentB'].iloc[-1] if len(bb_data['PercentB']) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_price = float(df['close'].iloc[-1]) if len(df['close']) > 0 and pd.notna(df['close'].iloc[-1]) else None
                    upper_band = float(bb_data['Upper'].iloc[-1]) if len(bb_data['Upper']) > 0 and pd.notna(bb_data['Upper'].iloc[-1]) else None
                    lower_band = float(bb_data['Lower'].iloc[-1]) if len(bb_data['Lower']) > 0 and pd.notna(bb_data['Lower'].iloc[-1]) else None
                    middle_band = float(bb_data['Middle'].iloc[-1]) if len(bb_data['Middle']) > 0 and pd.notna(bb_data['Middle'].iloc[-1]) else None
                    percent_b = float(bb_data['PercentB'].iloc[-1]) if len(bb_data['PercentB']) > 0 and pd.notna(bb_data['PercentB'].iloc[-1]) else None
                    
                    results['indicators'][f'BOLLINGER_{period}'] = {
                        'Upper_Band': round(upper_band, 2) if upper_band is not None else None,
                        'Middle_Band': round(middle_band, 2) if middle_band is not None else None,
                        'Lower_Band': round(lower_band, 2) if lower_band is not None else None,
                        'Percent_B': round(percent_b, 2) if percent_b is not None else None,
                        'position': 'ABOVE_UPPER' if current_price is not None and upper_band is not None and current_price > upper_band else 'BELOW_LOWER' if current_price is not None and lower_band is not None and current_price < lower_band else 'WITHIN_BANDS' if current_price is not None and upper_band is not None and lower_band is not None and current_price <= upper_band and current_price >= lower_band else 'N/A'
                    }
                    
                elif indicator_upper == 'ADX':
                    adx_values = calculate_adx(df, period)
                    # print(f"DEBUG (stock_ta_tool.py): ADX 計算完成，最後值: {adx_values.iloc[-1] if len(adx_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_adx = float(adx_values.iloc[-1]) if len(adx_values) > 0 and pd.notna(adx_values.iloc[-1]) else None
                    
                    results['indicators'][f'ADX_{period}'] = {
                        'current_value': round(current_adx, 2) if current_adx is not None else None,
                        'trend_strength': 'STRONG' if current_adx is not None and current_adx > 25 else 'MODERATE' if current_adx is not None and current_adx > 20 else 'WEAK' if current_adx is not None else 'N/A'
                    }
                    
                elif indicator_upper == 'ATR':
                    atr_values = calculate_atr(df, period)
                    # print(f"DEBUG (stock_ta_tool.py): ATR 計算完成，最後值: {atr_values.iloc[-1] if len(atr_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_atr = float(atr_values.iloc[-1]) if len(atr_values) > 0 and pd.notna(atr_values.iloc[-1]) else None
                    current_close = float(df['close'].iloc[-1]) if len(df['close']) > 0 and pd.notna(df['close'].iloc[-1]) else None
                    
                    results['indicators'][f'ATR_{period}'] = {
                        'current_value': round(current_atr, 2) if current_atr is not None else None,
                        'volatility': 'HIGH' if current_atr is not None and current_close is not None and current_atr > current_close * 0.02 else 'LOW' if current_atr is not None and current_close is not None else 'N/A'
                    }
                
                elif indicator_upper == 'STOCHASTIC':
                    stoch_data = calculate_stochastic(df['high'], df['low'], df['close'], period, 3) # Using 3 as default D period
                    # print(f"DEBUG (stock_ta_tool.py): STOCHASTIC 計算完成，最後值: K={stoch_data['K'].iloc[-1] if len(stoch_data['K']) > 0 else 'N/A'}, D={stoch_data['D'].iloc[-1] if len(stoch_data['D']) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_k = float(stoch_data['K'].iloc[-1]) if len(stoch_data['K']) > 0 and pd.notna(stoch_data['K'].iloc[-1]) else None
                    current_d = float(stoch_data['D'].iloc[-1]) if len(stoch_data['D']) > 0 and pd.notna(stoch_data['D'].iloc[-1]) else None
                    
                    results['indicators'][f'STOCHASTIC_{period}'] = {
                        'K_line': round(current_k, 2) if current_k is not None else None,
                        'D_line': round(current_d, 2) if current_d is not None else None,
                        'signal': 'BUY' if current_k is not None and current_d is not None and current_k > current_d and current_k < 80 else 'SELL' if current_k is not None and current_d is not None and current_k < current_d and current_k > 20 else 'NEUTRAL'
                    }
                
                elif indicator_upper == 'WILLIAMS_R':
                    willr_values = calculate_williams_r(df['high'], df['low'], df['close'], period)
                    # print(f"DEBUG (stock_ta_tool.py): WILLIAMS_R 計算完成，最後值: {willr_values.iloc[-1] if len(willr_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_willr = float(willr_values.iloc[-1]) if len(willr_values) > 0 and pd.notna(willr_values.iloc[-1]) else None
                    
                    results['indicators'][f'WILLIAMS_R_{period}'] = {
                        'current_value': round(current_willr, 2) if current_willr is not None else None,
                        'signal': 'OVERSOLD' if current_willr is not None and current_willr < -80 else 'OVERBOUGHT' if current_willr is not None and current_willr > -20 else 'NEUTRAL'
                    }
                
                elif indicator_upper == 'CCI':
                    cci_values = calculate_cci(df, period)
                    # print(f"DEBUG (stock_ta_tool.py): CCI 計算完成，最後值: {cci_values.iloc[-1] if len(cci_values) > 0 else 'N/A'}")  # 修復: 移除以避免污染 JSON 輸出
                    current_cci = float(cci_values.iloc[-1]) if len(cci_values) > 0 and pd.notna(cci_values.iloc[-1]) else None
                    
                    results['indicators'][f'CCI_{period}'] = {
                        'current_value': round(current_cci, 2) if current_cci is not None else None,
                        'signal': 'BUY' if current_cci is not None and current_cci < -100 else 'SELL' if current_cci is not None and current_cci > 100 else 'NEUTRAL'
                    }
                    
                else:
                    # print(f"DEBUG (stock_ta_tool.py): 不支援的指標: {indicator_upper}")  # 修復: 移除以避免污染 JSON 輸出
                    results['indicators'][indicator_upper] = {
                        'error': f"不支援的技術指標: {indicator_upper}"
                    }

            except Exception as e:
                # print(f"DEBUG (stock_ta_tool.py): 計算 {indicator_upper} 時發生錯誤: {e}", exc_info=True)  # 修復: 移除以避免污染 JSON 輸出
                results['indicators'][indicator_upper] = {
                    'error': f"計算 {indicator_upper} 時發生錯誤: {str(e)}"
                }
        
        # print(f"DEBUG (stock_ta_tool.py): get_technical_indicators 函數即將返回結果: {results}")  # 修復: 移除以避免污染 JSON 輸出
        return results
        
    except Exception as e:
        # print(f"DEBUG (stock_ta_tool.py): 獲取技術指標時發生頂層錯誤: {e}", exc_info=True)  # 修復: 移除以避免污染 JSON 輸出
        return {
            'ticker': ticker.upper(),
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'error': f"獲取技術指標時發生錯誤: {str(e)}"
        }


# The following functions are no longer needed as TA-Lib is used
# def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
#     ... (removed)

# def calculate_adx(df: pd.DataFrame, period: int =14) -> pd.Series:
#     ... (removed)

def calculate_score(df: pd.DataFrame) -> Dict[str, Any]:
    # This function still uses the calculated indicators from the DataFrame
    # It needs to be updated to reflect the new TA-Lib based indicator names
    # For now, I will leave it as is, as the primary task is to integrate TA-Lib
    # into the indicator calculations. This function will likely need further
    # adjustments if the indicator names or structure change significantly.
    try:
        if len(df) == 0 or df.isnull().all().all():
            raise ValueError("輸入的 DataFrame 為空或全為 NaN，無法計算評分。")
        latest = df.iloc[-1].copy() 
        default_numeric_value = 0.0 
        default_level_value = latest.get('close', 0.0) 
        for col in ['MA5', 'MA10', 'MA20', 'MA50', 'MA200', 'EMA12', 'EMA26', 'EMA50', 
                    'MACD', 'Signal', 'Histogram', 'RSI', 'Volatility', 
                    'Volume_Ratio', 'Volume_MA20', '20D_High', '50D_High', 
                    'Price_to_MA20_Ratio', 'Price_to_MA50_Ratio', 
                    'Support_Level', 'Resistance_Level', 'ADX',
                    'UpperBand', 'LowerBand', 'PercentB']:
            if pd.isna(latest.get(col)):
                if 'MA' in col or 'EMA' in col or 'High' in col or 'Level' in col or 'Band' in col or 'Signal' in col:
                    latest[col] = default_level_value
                elif col == 'RSI': latest[col] = 50.0
                elif col == 'ADX': latest[col] = 20.0
                else: latest[col] = default_numeric_value
        if pd.isna(latest.get('close')):
             raise ValueError("最新數據中缺少收盤價，無法計算評分。")
        score = 50
        # These calculations will need to be updated to use the new TA-Lib indicator outputs
        # For now, I'm keeping the structure, but the actual values might be off
        # until the `calculate_indicators` function is properly replaced or removed.
        
        # Placeholder for actual indicator values from TA-Lib
        # This part needs careful mapping from TA-Lib outputs to the expected 'latest' DataFrame structure
        
        # For now, I'll use dummy values or try to map existing ones if possible
        # This section needs a more thorough review and update after TA-Lib integration.
        
        # Example: If MA20 is needed, it should come from the TA-Lib calculation, not a pre-calculated column
        # For now, I'll assume the 'latest' DataFrame still has these columns, which might not be true after TA-Lib integration.
        
        # This function needs a complete rewrite to properly integrate with TA-Lib outputs.
        # For the purpose of this task (integrating TA-Lib into indicator calculations),
        # I will leave this function as is, but note that it requires further work.
        
        # Dummy values for now to avoid errors
        trend_score = 0
        momentum_score = 0
        macd_score = 0
        volume_score = 0
        breakout_score = 0
        overbought_penalty = 0
        adx_score = 0
        ma_alignment_score = 0

        # Attempt to use existing values if they exist, otherwise default
        if 'MA20' in latest and latest['MA20'] != 0:
            if latest['MA5'] > latest['MA20']: trend_score = 25 * min(1, (latest['MA5'] / latest['MA20'] - 1) * 10)
            else: trend_score = -25 * min(1, (1 - latest['MA5'] / latest['MA20']) * 10)
        
        if 'close' in latest and 'close' in df.columns and len(df) >= 4:
            price_3_days_ago = df['close'].iloc[-4]
            if pd.isna(price_3_days_ago) or price_3_days_ago == 0: momentum_score = 0
            elif latest['close'] > price_3_days_ago: momentum_score = 15 * min(1, (latest['close'] / price_3_days_ago - 1) * 10)
            else: momentum_score = -15 * min(1, (1 - latest['close'] / price_3_days_ago) * 10)
        
        if 'MACD' in latest and 'Signal' in latest and 'Histogram' in latest:
            hist_std = df['Histogram'].std() if 'Histogram' in df.columns else 1.0
            if pd.isna(hist_std) or hist_std == 0: hist_std = 1.0
            if latest['MACD'] > latest['Signal'] and latest['Histogram'] > 0: macd_score = 15 * min(1, latest['Histogram'] / hist_std)
            elif latest['MACD'] < latest['Signal'] and latest['Histogram'] < 0: macd_score = -15 * min(1, abs(latest['Histogram']) / hist_std)
            else: macd_score = 0
        
        if 'Volume_Ratio' in latest:
            volume_ratio = latest['Volume_Ratio']
            if volume_ratio > 1.2: volume_score = 10 * min(1, (volume_ratio - 1.2) * 5)
            elif volume_ratio < 0.8: volume_score = -5 * min(1, (0.8 - volume_ratio) * 5)
            else: volume_score = 0
        
        if '20D_High' in latest and 'close' in latest:
            if latest['close'] > latest['20D_High'] * 0.99 and latest['close'] < latest['20D_High'] * 1.03: breakout_score = 10
            elif '50D_High' in latest and latest['close'] > latest['50D_High'] * 0.99 and latest['close'] < latest['50D_High'] * 1.03: breakout_score = 5
        
        if 'Price_to_MA20_Ratio' in latest and 'RSI' in latest:
            if latest['Price_to_MA20_Ratio'] > 1.15: overbought_penalty -= 10
            elif latest['Price_to_MA20_Ratio'] > 1.08: overbought_penalty -= 5
            if latest['RSI'] > 80: overbought_penalty -= 10
            elif latest['RSI'] > 70: overbought_penalty -= 5
        
        if 'ADX' in latest:
            if latest['ADX'] > 30: adx_score = 10
            elif latest['ADX'] > 20: adx_score = 5
        
        if 'MA5' in latest and 'MA10' in latest and 'MA20' in latest and 'MA50' in latest:
            if latest['MA5'] > latest['MA10'] and latest['MA10'] > latest['MA20'] and latest['MA20'] > latest['MA50']: ma_alignment_score = 10
            elif latest['MA5'] > latest['MA10'] and latest['MA10'] > latest['MA20']: ma_alignment_score = 5
        
        raw_score_sum = (trend_score + momentum_score + macd_score + volume_score + breakout_score + overbought_penalty + adx_score + ma_alignment_score)
        final_score = 50 + (raw_score_sum * 0.5)
        final_score = max(0, min(100, final_score))
        score_breakdown = {"趨勢分數": round(trend_score, 1), "動量分數": round(momentum_score, 1), "MACD分數": round(macd_score, 1), "成交量分數": round(volume_score, 1), "突破分數": round(breakout_score, 1), "過度買入調整": round(overbought_penalty, 1), "趨勢強度分數": round(adx_score, 1), "均線排列分數": round(ma_alignment_score, 1)}
        technical_summary = {"收盤價": round(latest['close'], 2) if pd.notna(latest['close']) else "N/A", "MA5": round(latest['MA5'], 2) if pd.notna(latest['MA5']) else "N/A", "MA20": round(latest['MA20'], 2) if pd.notna(latest['MA20']) else "N/A", "MA50": round(latest['MA50'], 2) if pd.notna(latest['MA50']) else "N/A", "RSI(14)": round(latest['RSI'], 1) if pd.notna(latest['RSI']) else "N/A", "MACD": round(latest['MACD'], 3) if pd.notna(latest['MACD']) else "N/A", "Signal": round(latest['Signal'], 3) if pd.notna(latest['Signal']) else "N/A", "ADX(14)": round(latest['ADX'], 1) if pd.notna(latest['ADX']) else "N/A", "20日高點": round(latest['20D_High'], 2) if pd.notna(latest['20D_High']) else "N/A", "成交量比率": round(latest['Volume_Ratio'], 2) if pd.notna(latest['Volume_Ratio']) else "N/A"}
        recommendation = generate_recommendation(final_score, latest, score_breakdown)
        return {"momentum_score": round(final_score), "score_breakdown": score_breakdown, "technical_summary": technical_summary, "recommendation": recommendation}
    except Exception as e:
        print(f"計算評分時發生錯誤: {e}")
        raise ValueError(f"計算評分時出錯: {str(e)}")

def generate_recommendation(score: float, latest_data: pd.Series, score_breakdown: Dict[str, float]) -> str:
    if score >= 85: strength, action = "極強", "可考慮積極建立多頭倉位，設置合理止損"
    elif score >= 70: strength, action = "強勁", "多頭機會，可考慮建立中型倉位"
    elif score >= 60: strength, action = "中強", "偏多趨勢，可小量建倉或持有現有倉位"
    elif score >= 45: strength, action = "中性", "趨勢不明朗，建議觀望"
    elif score >= 30: strength, action = "中弱", "偏空趨勢，避免新建多頭倉位"
    elif score >= 15: strength, action = "弱勢", "明顯空頭趨勢，可考慮減倉或持有空單"
    else: strength, action = "極弱", "強烈看跌信號，避免做多"
    overbought_risk = ""
    if pd.notna(latest_data.get('RSI')) and latest_data['RSI'] > 75 : overbought_risk = "警告：RSI ({:.1f}) 處於超買區間，短期回調風險較高。".format(latest_data['RSI'])
    elif pd.notna(latest_data.get('Price_to_MA20_Ratio')) and latest_data['Price_to_MA20_Ratio'] > 1.12: overbought_risk = "注意：股價 ({:.2f}) 相對於MA20 ({:.2f}) 顯著偏高，可能面臨回調壓力。".format(latest_data['close'], latest_data['MA20'])
    breakout_status = ""
    if pd.notna(latest_data.get('close')) and pd.notna(latest_data.get('20D_High')) and latest_data['close'] > latest_data['20D_High'] * 0.99 and score_breakdown.get("突破分數", 0) > 0: breakout_status = "價格正處於或接近20日高點 ({:.2f})，可能出現突破行情。".format(latest_data['20D_High'])
    recommendation = f"動量評分 {int(score)}/100 ({strength})。{action}"
    if overbought_risk: recommendation += " " + overbought_risk
    if breakout_status: recommendation += " " + breakout_status
    return recommendation

def get_stock_name(ticker: str) -> str:
    try:
        ticker_upper = ticker.strip().upper()
        # 若為外匯代碼，直接返回外匯名稱
        if is_forex_ticker(ticker_upper):
            return FOREX_NAMES.get(ticker_upper, f"{ticker_upper} 外匯對")
        if not TIINGO_API_KEY or TIINGO_API_KEY == "YOUR_TIINGO_API_KEY_HERE":
            print("警告: Tiingo API 金鑰未有效配置，將返回通用股票名稱。")
            return f"{ticker.upper()} 股票/ETF"
        headers = {'Content-Type': 'application/json', 'Authorization': f'Token {TIINGO_API_KEY}'}
        common_names = {"AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc. Class A", "GOOG": "Alphabet Inc. Class C", "AMZN": "Amazon.com, Inc.", "TSLA": "Tesla, Inc.", "META": "Meta Platforms, Inc.", "NVDA": "NVIDIA Corporation", "JPM": "JPMorgan Chase & Co.", "V": "Visa Inc.", "VOO": "Vanguard S&P 500 ETF", "VTI": "Vanguard Total Stock Market ETF", "QQQ": "Invesco QQQ Trust", "SPY": "SPDR S&P 500 ETF", "IVV": "iShares Core S&P 500 ETF", "ARKK": "ARK Innovation ETF", "DIA": "SPDR Dow Jones Industrial Average ETF", "XLF": "Financial Select Sector SPDR Fund"}
        if ticker_upper in common_names: return common_names[ticker_upper]
        meta_url = f"https://api.tiingo.com/tiingo/daily/{ticker_upper}"
        response_meta = requests.get(meta_url, headers=headers)
        if response_meta.status_code == 200:
            data_meta = response_meta.json()
            if isinstance(data_meta, dict) and "name" in data_meta and data_meta["name"]: return data_meta["name"]
        search_url = f"https://api.tiingo.com/tiingo/utilities/search?query={ticker_upper}&limit=1"
        response_search = requests.get(search_url, headers=headers)
        if response_search.status_code == 200:
            data_search = response_search.json()
            if isinstance(data_search, list) and len(data_search) > 0:
                best_match = data_search[0]
                if "ticker" in best_match and best_match["ticker"].upper() == ticker_upper and "name" in best_match and best_match["name"]: return best_match["name"]
        print(f"無法通過 Tiingo API 找到 {ticker_upper} 的確切名稱，將返回通用名稱。")
        return f"{ticker_upper} 股票/ETF"
    except requests.exceptions.RequestException as e:
        print(f"獲取股票名稱時 (Tiingo API) 發生網路錯誤: {e}")
        return f"{ticker.upper()} 股票/ETF"
    except Exception as e:
        print(f"獲取股票名稱時 (Tiingo API) 發生錯誤: {e}")
        return f"{ticker.upper()} 股票/ETF"

def momentum_stock_score(ticker: str, time_period: str = "180d") -> Dict[str, Any]:
    ticker_cleaned = ticker.upper().strip()
    # --- 修改: 在回傳時間戳時也使用 UTC ---
    # timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + " UTC"


    company_name = get_stock_name(ticker_cleaned)
    try:
        df = get_stock_data(ticker_cleaned, time_period)
        if df.empty or len(df) < 20:
            return {"timestamp": timestamp_str, "ticker": ticker_cleaned, "name": company_name, "analysis_period": time_period, "error": f"無法進行分析：可用的歷史數據不足。需要至少20天的數據，實際獲取 {len(df)} 天。"}
        
        # Calculate indicators using TA-Lib functions
        # Map to column names that calculate_score expects
        
        df['MA5'] = calculate_sma(df['close'], 5)    # calculate_score expects MA5
        df['MA10'] = calculate_sma(df['close'], 10)   # calculate_score expects MA10
        df['MA20'] = calculate_sma(df['close'], 20)   # calculate_score expects MA20
        df['MA50'] = calculate_sma(df['close'], 50)   # calculate_score expects MA50
        df['MA200'] = calculate_sma(df['close'], 200) # calculate_score expects MA200
        
        df['EMA12'] = calculate_ema(df['close'], 12)
        df['EMA26'] = calculate_ema(df['close'], 26)
        df['EMA50'] = calculate_ema(df['close'], 50)
        
        macd_data = calculate_macd_detailed(df['close'])
        df['MACD'] = macd_data['MACD']
        df['Signal'] = macd_data['Signal']
        df['Histogram'] = macd_data['Histogram']
        
        df['RSI'] = calculate_rsi(df['close'], 14)
        
        bb_data = calculate_bollinger_bands(df['close'], 20)
        df['UpperBand'] = bb_data['Upper']
        df['LowerBand'] = bb_data['Lower']
        df['MiddleBand'] = bb_data['Middle']
        df['PercentB'] = bb_data['PercentB']
        
        df['ADX'] = calculate_adx(df, 14)
        df['ATR'] = calculate_atr(df, 14)
        df['CCI'] = calculate_cci(df, 20)
        
        stoch_data = calculate_stochastic(df['high'], df['low'], df['close'], 14, 3)
        df['StochK'] = stoch_data['K']
        df['StochD'] = stoch_data['D']
        
        df['WilliamsR'] = calculate_williams_r(df['high'], df['low'], df['close'], 14)
        
        # Add other necessary columns for calculate_score if they are not directly from TA-Lib
        # These might need to be re-evaluated based on how calculate_score uses them
        df["Volatility"] = df["close"].rolling(window=20).std() / df["close"].rolling(window=20).mean()
        df["Volume_Ratio"] = df["volume"] / df["volume"].rolling(window=20).mean()
        df["Volume_MA20"] = df["volume"].rolling(window=20).mean()
        df["Money_Flow"] = df["close"] * df["volume"]
        df['20D_High'] = df['high'].rolling(window=20).max()
        df['50D_High'] = df['high'].rolling(window=50).max()
        df['Price_to_MA20_Ratio'] = df['close'] / df['MA20'] # Use MA20 instead of SMA20
        df['Price_to_MA50_Ratio'] = df['close'] / df['MA50'] # Use MA50 instead of SMA50
        df['Support_Level'] = df['low'].rolling(window=20).min()
        df['Resistance_Level'] = df['high'].rolling(window=20).max()
        
        # Ensure all columns used by calculate_score are present and filled
        df_filled = df.ffill().bfill() # Fill NaNs for score calculation
        
        score_result = calculate_score(df_filled) # Pass the DataFrame with TA-Lib indicators
        
        return {"timestamp": timestamp_str, "ticker": ticker_cleaned, "name": company_name, "analysis_period": time_period, "momentum_score": score_result["momentum_score"], "score_breakdown": score_result["score_breakdown"], "technical_summary": score_result["technical_summary"], "recommendation": score_result["recommendation"], "data_rows_used_for_analysis": len(df_filled)}
    except ValueError as ve:
        error_message = str(ve)
        friendly_error = f"分析 {ticker_cleaned} 時發生錯誤: {error_message}"
        if "API 金鑰無效" in error_message or "API 金鑰未配置" in error_message: friendly_error = f"Tiingo API 金鑰配置錯誤或無效: {error_message}"
        elif "API 速率限制" in error_message: friendly_error = "Tiingo API 呼叫頻率超過限制，請稍後再試。"
        elif "找不到股票代碼" in error_message or "無法獲取" in error_message: friendly_error = f"無法獲取 {ticker_cleaned} 的歷史數據。請確認股票代碼是否正確或稍後再試 ({error_message})。"
        elif "數據不足" in error_message or "無法計算評分" in error_message: friendly_error = f"分析 {ticker_cleaned} 失敗，因為數據不足或數據質量問題: {error_message}"
        return {"timestamp": timestamp_str, "ticker": ticker_cleaned, "name": company_name, "analysis_period": time_period, "error": friendly_error}
    except Exception as e:
        error_message = str(e)
        friendly_error = f"分析 {ticker_cleaned} 時發生未預期系統錯誤: {error_message}"
        return {
            "timestamp": timestamp_str,
            "ticker": ticker_cleaned,
            "name": company_name,
            "analysis_period": time_period, # 確保這裡返回的是傳入的 time_period
            "error": friendly_error
        }

if __name__ == '__main__':
    print("--- 進階動量股票評分工具 (Tiingo API 版本) ---")
    if TIINGO_API_KEY == "YOUR_TIINGO_API_KEY_HERE":
        print("警告：請設定有效的 TIINGO_API_KEY 以進行完整測試。\n")
    
    test_tickers_and_periods = [
        ("AAPL", "180d"), ("MSFT", "1y"), ("GOOG", "90d"), ("TSLA", "250d"),
        ("VOO", "365d"), # 測試 ETF，之前出錯的地方
        ("NONEXISTENTTICKERXYZ", "60d"), ("AMD", "30d")
    ]
    for ticker, period in test_tickers_and_periods:
        print(f"\n--- 正在分析 {ticker} (週期: {period}) ---")
        analysis_result = momentum_stock_score(ticker, period)
        if "error" in analysis_result: print(f"錯誤: {analysis_result['error']}")
        else:
            print(f"時間戳: {analysis_result['timestamp']}")
            print(f"股票名稱: {analysis_result['name']}")
            print(f"動量評分: {analysis_result['momentum_score']}")
            # print(f"評分細節: {analysis_result['score_breakdown']}") # 可選擇性打印
            # print(f"技術指標摘要: {analysis_result['technical_summary']}") # 可選擇性打印
            print(f"建議: {analysis_result['recommendation']}")
            print(f"用於分析的數據行數: {analysis_result.get('data_rows_used_for_analysis', 'N/A')}")
        time.sleep(1.5) # 稍微增加延遲，尊重API限制
    
    print("\n--- 測試無效 API 金鑰 ---")
    original_key = TIINGO_API_KEY
    TIINGO_API_KEY = "INVALID_KEY_FOR_TESTING_PURPOSES"
    result_invalid_key = momentum_stock_score("AAPL", "30d")
    print(f"股票: {result_invalid_key['ticker']}, 名稱: {result_invalid_key['name']}")
    print(f"錯誤: {result_invalid_key['error']}")
    TIINGO_API_KEY = original_key 

    print("\n--- 測試 API 金鑰未配置 ---")
    TIINGO_API_KEY = "YOUR_TIINGO_API_KEY_HERE" 
    result_no_key = momentum_stock_score("MSFT", "30d")
    print(f"股票: {result_no_key['ticker']}, 名稱: {result_no_key['name']}")
    print(f"錯誤: {result_no_key['error']}")
    TIINGO_API_KEY = original_key

