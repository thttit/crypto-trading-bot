"""
AI Engine: tổng hợp dữ liệu kỹ thuật + tin tức, đưa ra signal LONG/SHORT
chỉ khi confidence >= MIN_CONFIDENCE (mặc định 90%).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np
from loguru import logger

from config import MIN_CONFIDENCE, SYMBOLS
from data_collector import DataCollector
from news_analyzer import NewsAnalyzer


@dataclass
class TradeSignal:
    symbol: str
    direction: str  # "LONG" | "SHORT"
    confidence: float  # 0..1
    reason: str
    indicators: Dict[str, Any]
    news_sentiment: float
    leverage: Optional[int] = None  # Đòn bẩy (dùng config nếu None)
    stop_loss_percent: Optional[float] = None  # % SL (dùng config nếu None)
    take_profit_percent: Optional[float] = None  # % TP (dùng config nếu None)


def _normalize_confidence(score: float) -> float:
    return max(0.0, min(1.0, (score + 1) / 2))


class AIEngine:
    """
    Kết hợp:
    - Phân tích kỹ thuật (RSI, MACD, EMA, trend)
    - Sentiment tin tức
    Chỉ trả về signal khi confidence >= MIN_CONFIDENCE.
    """

    def __init__(self, min_confidence: Optional[float] = None):
        self.min_confidence = min_confidence if min_confidence is not None else MIN_CONFIDENCE
        self.data_collector = DataCollector()
        self.news_analyzer = NewsAnalyzer()

    def _technical_score(self, ind: Dict[str, Any]) -> float:
        """
        Điểm kỹ thuật -1..1.
        Dương = thiên hướng long, âm = thiên hướng short.
        """
        score = 0.0
        weight_sum = 0.0

        # RSI: <30 oversold -> long, >70 overbought -> short
        rsi = ind.get("rsi")
        if rsi is not None:
            if rsi < 30:
                score += 1.0
            elif rsi > 70:
                score -= 1.0
            else:
                score += (50 - rsi) / 50  # 0-50 -> dương, 50-70 -> âm
            weight_sum += 1.0

        # MACD histogram: dương -> uptrend, âm -> downtrend
        macd_hist = ind.get("macd_hist")
        if macd_hist is not None and ind.get("close"):
            # Chuẩn hóa theo giá
            norm = macd_hist / (ind["close"] * 0.01) if ind["close"] else 0
            score += np.clip(norm * 10, -1, 1)
            weight_sum += 1.0

        # EMA: giá > EMA9 > EMA21 > EMA50 -> uptrend
        close = ind.get("close")
        ema9 = ind.get("ema_9")
        ema21 = ind.get("ema_21")
        ema50 = ind.get("ema_50")
        if all(x is not None for x in [close, ema9, ema21, ema50]):
            if close > ema9 > ema21:
                score += 0.5
            elif close < ema9 < ema21:
                score -= 0.5
            weight_sum += 0.5

        if weight_sum == 0:
            return 0.0
        return np.clip(score / weight_sum, -1, 1)

    def _analyze_symbol(self, symbol: str, interval: str = "4h") -> Optional[TradeSignal]:
        """Phân tích 1 symbol, trả về signal nếu đủ mạnh."""
        ind = self.data_collector.get_latest_indicators(symbol, interval)
        if not ind:
            return None

        tech_score = self._technical_score(ind)
        sentiment = self.news_analyzer.get_market_sentiment()
        news_score = sentiment["score"]  # -1..1

        # Kết hợp: 70% kỹ thuật, 30% tin tức
        combined = 0.7 * tech_score + 0.3 * news_score
        confidence = _normalize_confidence(combined)

        # Chỉ trả về khi confidence >= ngưỡng
        if confidence < self.min_confidence and (1 - confidence) < self.min_confidence:
            return None

        if combined > 0:
            direction = "LONG"
            conf = confidence
            reason = f"Technical+news bullish (tech={tech_score:.2f}, news={news_score:.2f})"
        else:
            direction = "SHORT"
            conf = 1 - confidence
            reason = f"Technical+news bearish (tech={tech_score:.2f}, news={news_score:.2f})"

        if conf < self.min_confidence:
            return None

        return TradeSignal(
            symbol=symbol,
            direction=direction,
            confidence=conf,
            reason=reason,
            indicators=ind,
            news_sentiment=news_score,
        )

    def _analyze_symbol_always(self, symbol: str, interval: str = "4h") -> Optional[TradeSignal]:
        """Phân tích 1 symbol, luôn trả về signal (kể cả confidence dưới ngưỡng) để hiển thị kết quả."""
        ind = self.data_collector.get_latest_indicators(symbol, interval)
        if not ind:
            return None
        tech_score = self._technical_score(ind)
        sentiment = self.news_analyzer.get_market_sentiment()
        news_score = sentiment["score"]
        combined = 0.7 * tech_score + 0.3 * news_score
        confidence = _normalize_confidence(combined)
        if combined > 0:
            direction = "LONG"
            conf = confidence
            reason = f"Technical+news bullish (tech={tech_score:.2f}, news={news_score:.2f})"
        else:
            direction = "SHORT"
            conf = 1 - confidence
            reason = f"Technical+news bearish (tech={tech_score:.2f}, news={news_score:.2f})"
        return TradeSignal(
            symbol=symbol,
            direction=direction,
            confidence=conf,
            reason=reason,
            indicators=ind,
            news_sentiment=news_score,
        )

    def get_signals(
        self,
        symbols: Optional[List[str]] = None,
        include_below_threshold: bool = False,
    ) -> List[TradeSignal]:
        """
        Quét các symbol.
        include_below_threshold=False: chỉ trả về signal có confidence >= MIN_CONFIDENCE.
        include_below_threshold=True: trả về mọi symbol (để hiển thị kết quả phân tích).
        """
        symbols = symbols or SYMBOLS
        signals = []
        for symbol in symbols:
            try:
                sig = (
                    self._analyze_symbol_always(symbol)
                    if include_below_threshold
                    else self._analyze_symbol(symbol)
                )
                if sig:
                    signals.append(sig)
                    logger.info(
                        f"Signal: {sig.symbol} {sig.direction} confidence={sig.confidence:.2%} - {sig.reason}"
                    )
            except Exception as e:
                logger.warning(f"analyze {symbol}: {e}")
        return signals
