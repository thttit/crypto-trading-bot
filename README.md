# Crypto Futures Trading Bot (Binance)

Bot AI giao dịch **futures** trên Binance: phân tích chart, tin tức crypto/chính trị/kinh tế, ra lệnh **LONG/SHORT** kèm **đòn bẩy**, **TP**, **SL**. Chỉ đặt lệnh khi độ tin cậy đạt ngưỡng (mặc định 65%, có thể chỉnh 65%–90%).

---

## Tính năng

| Tính năng | Mô tả |
|-----------|--------|
| **Lệnh futures** | LONG / SHORT, lệnh thị trường (MARKET), tự đặt Stop Loss & Take Profit |
| **Đòn bẩy** | Cấu hình đòn bẩy mặc định (1–125), áp dụng trước mỗi lệnh |
| **Phân tích chart** | RSI, MACD, EMA 9/21/50, Bollinger Bands, ATR; tóm tắt xu hướng (uptrend/downtrend) |
| **Tin tức** | RSS: crypto (CoinTelegraph, CoinDesk, Decrypt, The Block...), kinh tế (Bloomberg, CNBC, Dow Jones); sentiment đơn giản (bull/bear, Fed, ETF, regulation) |
| **AI Engine** | Kết hợp kỹ thuật (70%) + sentiment tin tức (30%) → confidence 0–1; chỉ ra signal khi ≥ MIN_CONFIDENCE |
| **Chế độ** | **paper**: chỉ log, không gửi lệnh thật; **live**: đặt lệnh thật trên sàn |

### Khi nào lệnh kết thúc?

Bot **không** tự đóng lệnh theo thời gian hay điều kiện trong code. Khi vào lệnh, bot gửi lên sàn:

1. **1 lệnh MARKET** — mở vị thế (Long/Short).
2. **2 lệnh điều kiện** — **Stop Loss (STOP_MARKET)** và **Take Profit (TAKE_PROFIT_MARKET)** với giá trigger tính theo % bạn cấu hình (SL %, TP %).

**Lệnh tự kết thúc khi:**

- **Đạt Take Profit**: giá chạm mức TP → sàn tự khớp lệnh đóng vị thế.
- **Đạt Stop Loss**: giá chạm mức SL → sàn tự khớp lệnh đóng vị thế.

Bạn có thể đóng tay bất kỳ lúc nào trên Binance. Cấu hình **SL %** và **TP %** trên dashboard (và bấm **Lưu cấu hình**) sẽ được dùng cho **lần vào lệnh tiếp theo**; lần chạy chu kỳ sau khi lưu sẽ đọc lại `.env` và áp dụng đúng leverage, SL, TP, limit USDT bạn đã đặt.

---

## Cài đặt

### 1. Môi trường

```bash
cd crypto-trading-bot
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Cấu hình `.env`

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/Mac
```

Sửa file `.env`:

| Biến | Ý nghĩa |
|------|---------|
| `BINANCE_API_KEY` | API Key từ [Binance API Management](https://www.binance.com/en/my/settings/api-management) (bật **Futures**) |
| `BINANCE_API_SECRET` | API Secret |
| `BINANCE_BASE_URL` | Để trống = mainnet. **Testnet (demo)**: `https://testnet.binancefuture.com` (chỉ domain, không thêm /fapi) — API key từ [Futures Testnet](https://testnet.binancefuture.com/) |
| `TRADE_MODE` | `paper` (giả lập trong bot, không gửi lệnh) hoặc `live` (gửi lệnh lên sàn) |
| `MIN_CONFIDENCE` | Ngưỡng confidence để ra lệnh: `0.65` (65%) đến `0.90` (90%) |
| `DEFAULT_LEVERAGE` | Đòn bẩy mặc định (1–125), ví dụ `5` |
| `STOP_LOSS_PERCENT` | % stop loss (ví dụ `0.02` = 2%) |
| `TAKE_PROFIT_PERCENT` | % take profit (ví dụ `0.04` = 4%) |
| `BOT_INTERVAL_MINUTES` | Số phút giữa mỗi chu kỳ khi chạy lặp (dùng với `run_loop.py`) |

### Tài khoản demo (Testnet) — an toàn với TRADE_MODE=live

Nếu bạn dùng **Binance Futures Testnet** (tiền ảo, không tốn tiền thật):

1. Lấy API key tại [testnet.binancefuture.com](https://testnet.binancefuture.com/).
2. Trong `.env`: đặt `BINANCE_BASE_URL=https://testnet.binancefuture.com` và `TRADE_MODE=live`.
3. Bot sẽ **lấy số dư từ ví Testnet** (khi chọn "Thật" trên dashboard) và **gửi lệnh lên Testnet** — không có conflict, an toàn.

Dropdown "Demo 500/1000/5000 USDT" trên dashboard chỉ **override số dư** để tính size lệnh (dùng khi bạn muốn giả lập "nếu có X USDT"), không chuyển kết nối sang testnet. Để thật sự dùng tài khoản demo của Binance, dùng `BINANCE_BASE_URL` testnet như trên.

---

## Dashboard (Khuyến nghị — quản lý bot qua giao diện)

Cách **an toàn và phổ biến** để dùng bot: chạy **Dashboard** trên trình duyệt, xem cấu hình, chạy **Phân tích only** (không đặt lệnh) trước, sau đó mới dùng **Chạy 1 chu kỳ** nếu muốn.

### Chạy Dashboard

```bash
# Cài thêm Flask nếu chưa có
pip install flask

# Chạy dashboard
python dashboard.py
```

Mở trình duyệt: **http://127.0.0.1:5000**

### Trên Dashboard bạn có thể

| Chức năng | Mô tả |
|-----------|--------|
| **Xem trạng thái** | Chế độ Paper/Live, số dư USDT (nếu có API), trạng thái Idle/Đang chạy |
| **Xem cấu hình** | Min confidence, leverage, SL/TP, số symbol (đọc từ `.env`) |
| **Phân tích only** | Chạy AI và hiển thị signal **không đặt lệnh** — dùng để xem bot sẽ làm gì |
| **Chạy 1 chu kỳ** | Chạy đầy đủ: phân tích + đặt lệnh (nếu đạt ngưỡng, theo chế độ Paper/Live) |
| **Kết quả** | Bảng signal (LONG/SHORT, confidence, lý do) và lệnh đã thực thi |
| **Log** | Xem log mới nhất, bấm "Làm mới log" để cập nhật |

### Cách dùng an toàn (khuyến nghị)

1. **Luôn để `TRADE_MODE=paper`** trong `.env` khi mới bắt đầu.
2. Mở Dashboard → bấm **"Phân tích only"** nhiều lần, xem signal và log.
3. Khi đã quen, có thể chuyển sang **"Chạy 1 chu kỳ"** — ở chế độ Paper bot vẫn chỉ log, không gửi lệnh thật.
4. Chỉ chuyển `TRADE_MODE=live` khi đã test kỹ và chấp nhận rủi ro; dùng vốn nhỏ.

---

## Hướng dẫn sử dụng (dòng lệnh)

### Chạy một lần (phân tích + ra lệnh nếu đủ điều kiện)

```bash
python main.py
```

- Bot sẽ:
  1. Lấy tin tức và tính sentiment (crypto + kinh tế).
  2. Quét các symbol (BTC, ETH, SOL, …), lấy nến và chỉ báo (RSI, MACD, EMA).
  3. AI kết hợp kỹ thuật + tin tức → chỉ ra signal **LONG** hoặc **SHORT** khi **confidence ≥ MIN_CONFIDENCE**.
  4. Với mỗi signal đạt ngưỡng: set đòn bẩy → đặt lệnh MARKET → đặt SL và TP.
- Ở chế độ **paper**: chỉ in log, không gửi lệnh lên sàn.
- Ở chế độ **live**: gửi lệnh thật (cẩn trọng với vốn).

### Chạy lặp (mỗi N phút)

```bash
python run_loop.py
```

- Mặc định mỗi **60 phút** chạy một chu kỳ (giống `main.py`).
- Đổi khoảng cách: trong `.env` đặt `BOT_INTERVAL_MINUTES=30` (hoặc số phút bạn muốn).

### Cách đọc log

- **Tin tức/xu hướng**: sentiment (bullish/bearish/neutral) và headline mới nhất.
- **Signal**: symbol, hướng (LONG/SHORT), confidence (%), lý do (technical + news).
- **Lệnh**: symbol, side, quantity, SL, TP; ở **paper** sẽ có prefix `[PAPER]`.

### Chỉnh danh sách coin và khung thời gian

- File `config.py`:
  - `SYMBOLS`: thêm/bớt symbol futures (phải đúng tên Binance, ví dụ `BTCUSDT`).
  - `TIMEFRAMES`: khung nến dùng để phân tích (`1h`, `4h`, `1d`).
- AI đang dùng khung **4h** mặc định; có thể sửa trong `ai_engine.py` (thay `interval="4h"` nếu cần).

### Tăng độ “chặt” (ít lệnh hơn, tin cậy cao hơn)

- Chỉnh `MIN_CONFIDENCE` trong `.env` (65%–90%), ví dụ:
  - `MIN_CONFIDENCE=0.65` → chỉ ra lệnh khi confidence ≥ 65%.
  - `MIN_CONFIDENCE=0.90` → chỉ khi ≥ 90%.

### Giảm rủi ro mỗi lệnh

- Giảm `MAX_POSITION_PERCENT` (ví dụ `0.02` = 2% tài khoản mỗi lệnh).
- Giảm `DEFAULT_LEVERAGE` (ví dụ 3 hoặc 5).
- Chỉnh `STOP_LOSS_PERCENT` / `TAKE_PROFIT_PERCENT` cho phù hợp phong cách của bạn.

---

## Cấu trúc project

```
crypto-trading-bot/
├── config.py          # Cấu hình: symbols, timeframes, MIN_CONFIDENCE, leverage, risk
├── binance_client.py  # Kết nối Binance Futures: klines, set leverage, đặt lệnh + SL/TP
├── data_collector.py  # Lấy OHLCV, tính RSI/MACD/EMA/ATR, tóm tắt chart
├── news_analyzer.py   # RSS crypto + kinh tế, sentiment, xu hướng tin tức
├── ai_engine.py       # Gộp kỹ thuật + tin tức → signal (chỉ khi ≥ MIN_CONFIDENCE)
├── order_executor.py  # Tính size, set leverage, gọi client đặt lệnh kèm SL/TP
├── main.py            # Chạy 1 chu kỳ
├── run_loop.py        # Chạy lặp mỗi N phút
├── requirements.txt
├── .env.example
├── README.md
└── logs/              # Log theo ngày (tự tạo khi chạy)
```

---

## Xử lý lỗi: Invalid API-key, IP, or permissions (401 / -2015)

Khi Dashboard hoặc bot báo lỗi **401** hoặc **-2015** từ Binance:

1. **API Key**: Vào [Binance API Management](https://www.binance.com/en/my/settings/api-management), kiểm tra key trong `.env` còn hiệu lực.
2. **Quyền Futures**: Bật **Enable Reading** và **Enable Futures** (không cần Enable Withdraw).
3. **Whitelist IP**: Nếu bật "Restrict access to trusted IPs only", thêm IP máy bạn (ví dụ `116.100.44.125`) vào danh sách. Hoặc tắt giới hạn IP.

Sau khi sửa, tải lại Dashboard. **Phân tích only** và dữ liệu giá vẫn dùng được; chỉ số dư và đặt lệnh cần API đúng.

---

## Lưu ý quan trọng

### Về “độ chính xác” 90%–99%

- **MIN_CONFIDENCE** là **ngưỡng để bot quyết định có đặt lệnh hay không**, không phải tỷ lệ thắng thực tế.
- Thị trường luôn có rủi ro. Nên test kỹ ở **paper** và dùng vốn nhỏ khi chuyển **live**.

### Rủi ro

- Giao dịch futures có rủi ro cao (đòn bẩy, có thể mất vốn nhanh).
- API key nên **chỉ bật Futures**, **không** cấp quyền rút tiền.
- Tin tức/sentiment hiện tại là bản đơn giản; có thể tích hợp thêm API/news hoặc model NLP để cải thiện.

---

## Mở rộng (gợi ý)

- Thêm model ML (sklearn, xgboost) trong `ai_engine.py` để dự đoán từ chuỗi chỉ báo.
- Tích hợp API tin tức có sentiment (NewsAPI, CryptoNews API...) trong `news_analyzer.py`.
- Lấy thêm funding rate, open interest từ Binance/Glassnode.
- Thêm dashboard hoặc Telegram/Discord để nhận thông báo signal và lệnh.

---

## Đẩy code lên GitHub

**Lưu ý:** File `.env` (chứa API key) đã được liệt kê trong `.gitignore` — **sẽ không bị push** lên GitHub. Chỉ dùng `.env.example` làm mẫu cấu hình.

Nếu chưa tạo repo trên GitHub:

1. Vào [GitHub](https://github.com/new), tạo repository mới tên `crypto-trading-bot` (có thể private hoặc public).
2. Trong thư mục project (đã có `git init` và `remote origin` trỏ tới `https://github.com/thttit/crypto-trading-bot.git`), chạy:

```bash
git push -u origin master
```

Nếu GitHub dùng nhánh mặc định là `main`:

```bash
git branch -M main
git push -u origin main
```
