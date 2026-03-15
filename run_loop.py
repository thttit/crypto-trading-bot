"""
Chạy bot lặp mỗi N phút (mặc định 60 phút).
"""
import time
import sys
import os
os.makedirs("logs", exist_ok=True)

from loguru import logger
from config import MIN_CONFIDENCE, SYMBOLS, TRADE_MODE
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
    logger.add("logs/bot_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days", level="DEBUG")


def run_cycle(engine: AIEngine, executor: OrderExecutor):
    signals = engine.get_signals()
    for sig in signals:
        if sig.confidence >= MIN_CONFIDENCE:
            executor.execute(sig)


if __name__ == "__main__":
    setup_logging()
    interval_minutes = int(os.getenv("BOT_INTERVAL_MINUTES", "60"))
    engine = AIEngine()
    executor = OrderExecutor()
    logger.info(f"Bot loop: mỗi {interval_minutes} phút | Mode={TRADE_MODE} | Min confidence={MIN_CONFIDENCE:.0%}")
    while True:
        try:
            run_cycle(engine, executor)
        except Exception as e:
            logger.exception(f"Chu kỳ lỗi: {e}")
        logger.info(f"Chờ {interval_minutes} phút...")
        time.sleep(interval_minutes * 60)
