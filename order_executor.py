"""
Thực thi lệnh: chỉ khi signal từ AI Engine đạt confidence >= MIN_CONFIDENCE.
Tính size lệnh, stop loss, take profit và gọi Binance client.
Hỗ trợ: balance_override (demo), limit_usdt_total (chia đều cho các lệnh).
Đọc SL/TP/leverage từ config tại thời điểm execute() để dùng đúng giá trị .env sau khi user "Lưu cấu hình".
"""
from typing import Optional, List
from loguru import logger

from config import (
    MIN_CONFIDENCE,
    MAX_POSITION_PERCENT,
    LIMIT_USDT_PER_RUN,
)
from binance_client import BinanceFuturesClient
from ai_engine import TradeSignal


class OrderExecutor:
    """
    Chỉ đặt lệnh khi signal.confidence >= MIN_CONFIDENCE.
    """

    def __init__(self, client: Optional[BinanceFuturesClient] = None):
        self.client = client or BinanceFuturesClient()
        self.min_confidence = MIN_CONFIDENCE

    def _get_usdt_balance(self, balance_override: Optional[float] = None) -> float:
        """Lấy số dư USDT (thật hoặc override cho demo)."""
        if balance_override is not None and balance_override > 0:
            return float(balance_override)
        balance = self.client.get_balance()
        if not balance:
            return 0.0
        assets = balance if isinstance(balance, list) else (balance.get("assets") or [])
        for b in assets:
            if isinstance(b, dict) and b.get("asset") == "USDT":
                return float(b.get("availableBalance", 0) or b.get("balance", 0))
        return 0.0

    def _get_quantity(
        self,
        symbol: str,
        price: float,
        balance_override: Optional[float] = None,
        usdt_per_order: Optional[float] = None,
    ) -> float:
        """
        Tính size lệnh.
        Nếu usdt_per_order được truyền (từ limit chia đều), dùng luôn.
        Ngược lại: dùng balance (thật hoặc demo) * MAX_POSITION_PERCENT.
        """
        if price <= 0:
            return 0.0
        if usdt_per_order is not None and usdt_per_order > 0:
            return usdt_per_order / price
        usdt = self._get_usdt_balance(balance_override)
        if usdt <= 0:
            return 0.0
        import config as _cfg
        amount_usdt = usdt * _cfg.MAX_POSITION_PERCENT
        return amount_usdt / price

    def _round_quantity(self, symbol: str, qty: float) -> float:
        """Làm tròn theo quy tắc lot size của sàn (đơn giản)."""
        # Có thể lấy từ exchange_info; tạm làm tròn 3 chữ số
        if "BTC" in symbol:
            return round(qty, 4)
        return round(qty, 2)

    def execute(
        self,
        signal: TradeSignal,
        balance_override: Optional[float] = None,
        usdt_per_order: Optional[float] = None,
    ) -> bool:
        """
        Chỉ execute khi signal.confidence >= self.min_confidence.
        balance_override: dùng số dư demo (USDT). usdt_per_order: số USDT cố định cho lệnh này (từ limit chia đều).
        """
        import config as _cfg
        min_conf = _cfg.MIN_CONFIDENCE
        if signal.confidence < min_conf:
            logger.warning(
                f"Bỏ qua {signal.symbol} {signal.direction}: confidence {signal.confidence:.2%} < {min_conf:.0%}"
            )
            return False

        price = self.client.get_ticker_price(signal.symbol)
        if not price or price <= 0:
            logger.error(f"Không lấy được giá {signal.symbol}")
            return False

        quantity = self._get_quantity(
            signal.symbol, price,
            balance_override=balance_override,
            usdt_per_order=usdt_per_order,
        )
        quantity = self._round_quantity(signal.symbol, quantity)
        if quantity <= 0:
            logger.warning("Quantity = 0, bỏ qua lệnh")
            return False

        # Position side: One-way mode dùng "BOTH"
        position_side = "BOTH"
        side = "BUY" if signal.direction == "LONG" else "SELL"

        leverage = getattr(signal, "leverage", None) or _cfg.DEFAULT_LEVERAGE
        self.client.change_leverage(signal.symbol, leverage)

        sl = None
        tp = None
        sl_pct = getattr(signal, "stop_loss_percent", None) or _cfg.STOP_LOSS_PERCENT
        tp_pct = getattr(signal, "take_profit_percent", None) or _cfg.TAKE_PROFIT_PERCENT
        if signal.direction == "LONG":
            sl = price * (1 - sl_pct)
            tp = price * (1 + tp_pct)
        else:
            sl = price * (1 + sl_pct)
            tp = price * (1 - tp_pct)

        result = self.client.place_order(
            symbol=signal.symbol,
            side=side,
            position_side=position_side,
            quantity=quantity,
            order_type="MARKET",
            reduce_only=False,
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
        )
        if result:
            logger.info(
                f"Lệnh đã gửi: {signal.symbol} {signal.direction} qty={quantity} "
                f"confidence={signal.confidence:.2%}"
            )
            return True
        return False

    def execute_batch(
        self,
        signals: List[TradeSignal],
        balance_override: Optional[float] = None,
        limit_usdt_total: Optional[float] = None,
    ) -> List[dict]:
        """
        Thực thi nhiều signal. Nếu limit_usdt_total > 0 thì chia đều USDT cho từng lệnh.
        Trả về list { symbol, direction, confidence_pct, ok }.
        """
        import config as _cfg
        min_conf = _cfg.MIN_CONFIDENCE
        to_execute = [s for s in signals if s.confidence >= min_conf]
        if not to_execute:
            return []
        n = len(to_execute)
        usdt_per_order = None
        if limit_usdt_total and limit_usdt_total > 0:
            usdt_per_order = limit_usdt_total / n
        results = []
        for sig in to_execute:
            ok = self.execute(
                sig,
                balance_override=balance_override,
                usdt_per_order=usdt_per_order,
            )
            results.append({
                "symbol": sig.symbol,
                "direction": sig.direction,
                "confidence_pct": f"{sig.confidence * 100:.1f}%",
                "ok": ok,
            })
        return results
