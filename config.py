"""
Cấu hình chung cho Crypto Trading Bot.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Đường dẫn
BASE_DIR = Path(__file__).resolve().parent

# Binance
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
# Để trống = mainnet. Testnet (demo): chỉ dùng domain, không thêm /fapi (thư viện tự thêm).
# Ví dụ: https://testnet.binancefuture.com — API key lấy tại https://testnet.binancefuture.com/
_raw_base = os.getenv("BINANCE_BASE_URL", "").strip()
# Tránh lỗi /fapi/fapi/...: nếu user cấu hình .../fapi thì bỏ /fapi đi
if _raw_base.endswith("/fapi"):
    _raw_base = _raw_base[:-5].rstrip("/")
elif _raw_base.endswith("/fapi/"):
    _raw_base = _raw_base[:-6].rstrip("/")
BINANCE_BASE_URL = _raw_base

# Chế độ: paper (giả lập) | live (thật)
TRADE_MODE = os.getenv("TRADE_MODE", "paper").lower()

# Ngưỡng confidence: chỉ ra lệnh khi >= MIN_CONFIDENCE (65% = 0.65 đến 90% = 0.90)
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.65"))

# Danh sách symbol futures theo dõi
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "ARBUSDT",
    "OPUSDT",
    "SUIUSDT",
    "NEARUSDT",
    "APTUSDT",
    "INJUSDT",
    "FETUSDT",   # AI coin
    "RENDERUSDT", # AI
    "TAOUSDT",   # Bittensor
    "WLDUSDT",   # Worldcoin
]

# Khung thời gian nến
TIMEFRAMES = ["1h", "4h", "1d"]

# News API (optional)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY", "")

# Risk & Leverage
DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", "5"))  # Đòn bẩy mặc định (1-125)
MAX_POSITION_PERCENT = float(os.getenv("MAX_POSITION_PERCENT", "0.05"))  # Tối đa 5% tài khoản mỗi lệnh
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "0.02"))   # 2% stop loss mặc định
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "0.04"))  # 4% take profit mặc định
# Giới hạn USDT cho mỗi lần vào lệnh (0 = không giới hạn, dùng toàn bộ theo MAX_POSITION_PERCENT)
LIMIT_USDT_PER_RUN = float(os.getenv("LIMIT_USDT_PER_RUN", "0"))
