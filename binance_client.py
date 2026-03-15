"""
Client Binance Futures - kết nối API, lấy dữ liệu, đặt lệnh.
Chế độ paper: ghi log lệnh, không gửi thật.
"""
import time
from typing import Optional
from loguru import logger

try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_BASE_URL,
    TRADE_MODE,
)


def _norm_base_url(url: Optional[str]) -> str:
    """Chuẩn hóa base_url: bỏ /fapi để tránh lỗi /fapi/fapi/."""
    if not url or not url.strip():
        return ""
    u = url.strip()
    if u.endswith("/fapi"):
        u = u[:-5].rstrip("/")
    elif u.endswith("/fapi/"):
        u = u[:-6].rstrip("/")
    return u


class BinanceFuturesClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Nếu không truyền api_key/api_secret/base_url thì dùng từ config (.env).
        Cho phép override để dashboard dùng key nhập từ form "ví".
        """
        self.mode = TRADE_MODE
        self._client: Optional[UMFutures] = None
        self._last_balance_error: Optional[str] = None
        key = (api_key or "").strip() or BINANCE_API_KEY
        secret = (api_secret or "").strip() or BINANCE_API_SECRET
        base = _norm_base_url((base_url or "").strip() or BINANCE_BASE_URL)
        if UMFutures:
            kwargs = {}
            if key and secret:
                kwargs = {"key": key, "secret": secret}
            if base:
                kwargs["base_url"] = base
            self._client = UMFutures(**kwargs) if kwargs else UMFutures()
            logger.info(f"Binance client init: mode={self.mode}, authenticated={bool(kwargs)}")
        else:
            logger.warning("Chưa cài binance-futures-connector -> chỉ chạy phân tích offline")

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> list:
        """Lấy nến OHLCV. interval: 1h, 4h, 1d."""
        if not self._client:
            return []
        try:
            return self._client.klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            logger.error(f"get_klines {symbol} {interval}: {e}")
            return []

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        if not self._client:
            return None
        try:
            r = self._client.ticker_price(symbol=symbol)
            return float(r.get("price", 0))
        except Exception as e:
            logger.error(f"get_ticker_price {symbol}: {e}")
            return None

    def get_exchange_info(self):
        if not self._client:
            return None
        try:
            return self._client.exchange_info()
        except Exception as e:
            logger.error(f"get_exchange_info: {e}")
            return None

    def get_balance(self) -> Optional[dict]:
        if not self._client:
            self._last_balance_error = "Chưa kết nối client (thiếu API key/secret?)."
            return None
        self._last_balance_error = None
        try:
            return self._client.balance()
        except Exception as e:
            err_str = str(e)
            self._last_balance_error = err_str
            if "-2015" in err_str or "Invalid API-key" in err_str or "permissions" in err_str.lower():
                logger.warning(
                    "get_balance: Binance từ chối (API key / IP / quyền). "
                    "Kiểm tra: Binance API Management → bật Futures, thêm IP vào whitelist (hoặc tắt giới hạn IP)."
                )
            else:
                logger.error(f"get_balance: {e}")
            return None

    def get_last_balance_error(self) -> Optional[str]:
        """Lỗi lần gọi get_balance gần nhất (để dashboard hiển thị)."""
        return self._last_balance_error

    def get_position_risk(self):
        """
        Trả về list vị thế, hoặc dict lỗi từ Binance (để dashboard hiển thị thông báo).
        Nếu exception: raise để caller (dashboard) bắt và trả error cho user.
        """
        if not self._client:
            return []
        try:
            raw = self._client.get_position_risk()
            if isinstance(raw, list):
                return raw
            # Binance trả lỗi dạng dict {"code": ..., "msg": ...}
            return raw
        except Exception as e:
            logger.warning(f"get_position_risk: {e}")
            raise

    def change_leverage(self, symbol: str, leverage: int) -> bool:
        """Đặt đòn bẩy cho symbol (1-125). Chỉ có hiệu lực khi đã đăng nhập API."""
        if not self._client or self.mode == "paper":
            if self.mode == "paper":
                logger.info(f"[PAPER] Set leverage {symbol} = {leverage}x")
            return True
        try:
            leverage = max(1, min(125, int(leverage)))
            self._client.change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Leverage {symbol} = {leverage}x")
            return True
        except Exception as e:
            logger.error(f"change_leverage {symbol}: {e}")
            return False

    def place_order(
        self,
        symbol: str,
        side: str,  # BUY | SELL
        position_side: str,  # LONG | SHORT (hedge mode) hoặc BOTH
        quantity: float,
        order_type: str = "MARKET",
        reduce_only: bool = False,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[dict]:
        """
        Đặt lệnh futures.
        side: BUY = mở long / đóng short, SELL = mở short / đóng long.
        """
        if not self._client:
            logger.warning("Không có client -> bỏ qua đặt lệnh")
            return None

        if self.mode == "paper":
            logger.info(
                f"[PAPER] ORDER: {symbol} {side} qty={quantity} type={order_type} "
                f"SL={stop_loss} TP={take_profit}"
            )
            return {"paper": True, "symbol": symbol, "side": side, "quantity": quantity}

        try:
            params = {
                "symbol": symbol,
                "side": side,
                "positionSide": position_side,
                "type": order_type,
                "quantity": quantity,
            }
            if reduce_only:
                params["reduceOnly"] = "true"
            if order_type == "LIMIT":
                params["timeInForce"] = "GTC"
                # price cần truyền thêm

            result = self._client.new_order(**params)
            logger.info(f"Order placed: {result}")

            if stop_loss and result.get("orderId"):
                self._client.new_order(
                    symbol=symbol,
                    side="SELL" if side == "BUY" else "BUY",
                    positionSide=position_side,
                    type="STOP_MARKET",
                    stopPrice=str(round(stop_loss, 2)),
                    quantity=quantity,
                    reduceOnly="true",
                )
            if take_profit and result.get("orderId"):
                self._client.new_order(
                    symbol=symbol,
                    side="SELL" if side == "BUY" else "BUY",
                    positionSide=position_side,
                    type="TAKE_PROFIT_MARKET",
                    stopPrice=str(round(take_profit, 2)),
                    quantity=quantity,
                    reduceOnly="true",
                )
            return result
        except Exception as e:
            logger.error(f"place_order failed: {e}")
            return None

    def close_position(self, symbol: str, position_side: str, quantity: float) -> Optional[dict]:
        """Đóng vị thế: long thì SELL, short thì BUY."""
        side = "SELL" if position_side.upper() == "LONG" else "BUY"
        return self.place_order(
            symbol=symbol,
            side=side,
            position_side=position_side,
            quantity=quantity,
            reduce_only=True,
        )

    def get_income_history(
        self,
        income_type: str = "REALIZED_PNL",
        symbol: Optional[str] = None,
        limit: int = 1000,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ):
        """
        Lịch sử lãi/lỗ đã thực hiện (REALIZED_PNL).
        Binance: không gửi startTime/endTime thì chỉ trả về 7 ngày gần nhất; tối đa 3 tháng.
        """
        if not self._client:
            return []
        try:
            import time
            params = {"incomeType": income_type, "limit": min(1000, limit)}
            if symbol:
                params["symbol"] = symbol
            # Lấy 3 tháng gần nhất (Binance chỉ lưu tối đa 3 tháng)
            if end_time is None:
                end_time = int(time.time() * 1000)
            if start_time is None:
                start_time = end_time - (90 * 24 * 60 * 60 * 1000)
            params["startTime"] = start_time
            params["endTime"] = end_time
            return self._client.get_income_history(**params) or []
        except Exception as e:
            logger.error(f"get_income_history: {e}")
            return []

    def get_user_trades(self, symbol: str, limit: int = 100, start_time: Optional[int] = None, end_time: Optional[int] = None):
        """Lịch sử giao dịch theo symbol."""
        if not self._client:
            return []
        try:
            params = {"symbol": symbol, "limit": min(1000, limit)}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            return self._client.get_account_trades(**params) or []
        except Exception as e:
            logger.error(f"get_user_trades: {e}")
            return []
