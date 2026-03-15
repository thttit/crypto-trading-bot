"""
Bot giao dịch Crypto Futures - Binance.
Luồng: Thu thập dữ liệu -> Phân tích AI (chỉ ra lệnh khi confidence >= 90%) -> Thực thi lệnh.
Chạy: python main.py
"""
import time
import sys
from loguru import logger

from config import TRADE_MODE, MIN_CONFIDENCE, SYMBOLS
from data_collector import DataCollector
from ai_engine import AIEngine
from order_executor import OrderExecutor


def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
    )
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
    )


def run_cycle(engine: AIEngine, executor: OrderExecutor):
    """Một vòng: phân tích -> lấy signal -> execute nếu đủ confidence."""
    logger.info("--- Bắt đầu chu kỳ phân tích ---")
    # Log tóm tắt tin tức / xu hướng
    try:
        from news_analyzer import NewsAnalyzer
        summary = NewsAnalyzer().get_latest_trends_summary()
        if summary:
            logger.info(f"Tin tức/xu hướng: {summary}")
    except Exception as e:
        logger.debug(f"News summary: {e}")
    signals = engine.get_signals()
    if not signals:
        logger.info(f"Không có signal đạt ngưỡng confidence {int(MIN_CONFIDENCE*100)}% trong chu kỳ này.")
        return
    for sig in signals:
        if sig.confidence >= MIN_CONFIDENCE:
            executor.execute(sig)
        else:
            logger.debug(f"Bỏ qua {sig.symbol}: confidence {sig.confidence:.2%} < {MIN_CONFIDENCE:.0%}")


def main():
    import os
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    logger.info(
        f"Crypto Trading Bot | Mode={TRADE_MODE} | Min confidence={MIN_CONFIDENCE:.0%} | Symbols={len(SYMBOLS)}"
    )

    engine = AIEngine()
    executor = OrderExecutor()

    # Chạy 1 lần (có thể đổi thành loop + schedule)
    run_cycle(engine, executor)

    # Để chạy lặp mỗi 1 giờ, bỏ comment block dưới:
    # interval_seconds = 3600
    # while True:
    #     run_cycle(engine, executor)
    #     logger.info(f"Chờ {interval_seconds}s đến chu kỳ tiếp theo...")
    #     time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
