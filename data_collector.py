"""
Thu thập dữ liệu: nến OHLCV từ Binance, tính chỉ báo kỹ thuật (RSI, MACD, EMA, ...).
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger

try:
    import ta
except ImportError:
    ta = None

from binance_client import BinanceFuturesClient
from config import SYMBOLS, TIMEFRAMES


def klines_to_dataframe(klines: list) -> pd.DataFrame:
    """Chuyển klines Binance sang DataFrame."""
    if not klines:
        return pd.DataFrame()
    df = pd.DataFrame(
        klines,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ],
    )
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm RSI, MACD, EMA, Bollinger Bands, ATR."""
    if df.empty or len(df) < 30:
        return df
    out = df.copy()
    c = out["close"]
    h = out["high"]
    l = out["low"]
    v = out["volume"]

    if ta:
        out["rsi"] = ta.momentum.RSIIndicator(c, window=14).rsi()
        macd = ta.trend.MACD(c, window_slow=26, window_fast=12, window_sign=9)
        out["macd"] = macd.macd()
        out["macd_signal"] = macd.macd_signal()
        out["macd_hist"] = macd.macd_diff()
        out["ema_9"] = ta.trend.EMAIndicator(c, window=9).ema_indicator()
        out["ema_21"] = ta.trend.EMAIndicator(c, window=21).ema_indicator()
        out["ema_50"] = ta.trend.EMAIndicator(c, window=50).ema_indicator()
        bb = ta.volatility.BollingerBands(c, window=20, window_dev=2)
        out["bb_upper"] = bb.bollinger_hband()
        out["bb_lower"] = bb.bollinger_lband()
        out["bb_mid"] = bb.bollinger_mavg()
        out["atr"] = ta.volatility.AverageTrueRange(h, l, c, window=14).average_true_range()
    else:
        # Fallback đơn giản không cần ta
        out["rsi"] = _rsi(c, 14)
        out["ema_9"] = c.ewm(span=9, adjust=False).mean()
        out["ema_21"] = c.ewm(span=21, adjust=False).mean()
        out["ema_50"] = c.ewm(span=50, adjust=False).mean()
        out["atr"] = (h - l).rolling(14).mean()

    return out


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


class DataCollector:
    def __init__(self, client: Optional[BinanceFuturesClient] = None):
        self.client = client or BinanceFuturesClient()
        self.symbols = SYMBOLS
        self.timeframes = TIMEFRAMES

    def fetch_ohlcv(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """Lấy OHLCV và thêm chỉ báo."""
        klines = self.client.get_klines(symbol, interval, limit=limit)
        df = klines_to_dataframe(klines)
        return add_technical_indicators(df)

    def fetch_all(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Trả về: { symbol: { "1h": df, "4h": df, "1d": df } }
        """
        result = {}
        for symbol in self.symbols:
            result[symbol] = {}
            for tf in self.timeframes:
                try:
                    result[symbol][tf] = self.fetch_ohlcv(symbol, tf)
                except Exception as e:
                    logger.warning(f"fetch_all {symbol} {tf}: {e}")
                    result[symbol][tf] = pd.DataFrame()
        return result

    def get_latest_indicators(
        self, symbol: str, interval: str = "4h"
    ) -> Optional[Dict[str, float]]:
        """Lấy giá trị chỉ báo mới nhất cho 1 symbol."""
        df = self.fetch_ohlcv(symbol, interval, limit=100)
        if df.empty or len(df) < 2:
            return None
        row = df.iloc[-1]
        return {
            "close": float(row["close"]),
            "rsi": float(row["rsi"]) if "rsi" in row and pd.notna(row["rsi"]) else None,
            "macd_hist": float(row["macd_hist"]) if "macd_hist" in row and pd.notna(row["macd_hist"]) else None,
            "ema_9": float(row["ema_9"]) if "ema_9" in row else None,
            "ema_21": float(row["ema_21"]) if "ema_21" in row else None,
            "ema_50": float(row["ema_50"]) if "ema_50" in row else None,
            "atr": float(row["atr"]) if "atr" in row and pd.notna(row["atr"]) else None,
        }

    def get_chart_summary(self, symbol: str, interval: str = "4h") -> Optional[str]:
        """
        Tóm tắt biểu đồ/chỉ số cho symbol (dùng trong AI hoặc log).
        Trả về mô tả ngắn: xu hướng, RSI, MACD, hỗ trợ/kháng cự gần.
        """
        ind = self.get_latest_indicators(symbol, interval)
        if not ind:
            return None
        close = ind.get("close") or 0
        rsi = ind.get("rsi")
        ema9, ema21, ema50 = ind.get("ema_9"), ind.get("ema_21"), ind.get("ema_50")
        trend = "sideway"
        if all(x is not None for x in [close, ema9, ema21, ema50]):
            if close > ema9 > ema21:
                trend = "uptrend"
            elif close < ema9 < ema21:
                trend = "downtrend"
        rsi_desc = f"RSI={rsi:.0f}" if rsi is not None else "RSI=N/A"
        if rsi is not None:
            if rsi < 30:
                rsi_desc += " (oversold)"
            elif rsi > 70:
                rsi_desc += " (overbought)"
        return f"{symbol} {interval}: {trend}, {rsi_desc}, price={close}"
