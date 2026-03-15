"""
Dashboard web quản lý Crypto Trading Bot.
Chạy: python dashboard.py
Mở trình duyệt: http://127.0.0.1:5000
"""
import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, render_template_string, jsonify, request

# Tạo thư mục logs trước khi import main (loguru ghi file)
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

WALLET_KEYS_PATH = Path(__file__).resolve().parent / "data" / "wallet_keys.json"
TESTNET_BASE_URL = "https://testnet.binancefuture.com"


def _load_wallet_keys() -> dict:
    """Đọc API keys nhập từ form ví. Trả về { mainnet: {api_key, api_secret}, testnet: {...} }."""
    if not WALLET_KEYS_PATH.exists():
        return {"mainnet": {}, "testnet": {}}
    try:
        with open(WALLET_KEYS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "mainnet": data.get("mainnet") or {},
            "testnet": data.get("testnet") or {},
        }
    except Exception:
        return {"mainnet": {}, "testnet": {}}


def _save_wallet_keys(account_type: str, api_key: str, api_secret: str):
    """Lưu key/secret cho mainnet hoặc testnet."""
    data = _load_wallet_keys()
    data[account_type] = {"api_key": (api_key or "").strip(), "api_secret": (api_secret or "").strip()}
    WALLET_KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WALLET_KEYS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_client_for_account(account_type: str):
    """Tạo Binance client dùng key từ ví (wallet_keys) hoặc .env. account_type: mainnet | testnet."""
    from binance_client import BinanceFuturesClient
    from config import BINANCE_API_KEY, BINANCE_API_SECRET
    keys = _load_wallet_keys()
    k = keys.get(account_type) or {}
    api_key = (k.get("api_key") or "").strip() or BINANCE_API_KEY
    api_secret = (k.get("api_secret") or "").strip() or BINANCE_API_SECRET
    base_url = TESTNET_BASE_URL if account_type == "testnet" else ""
    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# Trạng thái chạy chu kỳ (chạy trong thread)
_run_status = {
    "status": "idle",  # idle | running
    "started_at": None,
    "finished_at": None,
    "signals": [],
    "executed": [],
    "error": None,
    "log_tail": [],
}


def _signal_to_dict(sig, chart_summary=None):
    """Chuyển TradeSignal thành dict để JSON, kèm bằng chứng (indicators, chart_summary)."""
    d = {
        "symbol": sig.symbol,
        "direction": sig.direction,
        "confidence": round(sig.confidence, 4),
        "confidence_pct": f"{sig.confidence * 100:.1f}%",
        "reason": sig.reason,
        "news_sentiment": round(sig.news_sentiment, 3),
        "evidence": {
            "indicators": {k: v for k, v in (sig.indicators or {}).items() if v is not None},
            "chart_summary": chart_summary,
        },
    }
    return d


def _run_cycle_background(
    execute_orders: bool,
    selected_symbols: Optional[list] = None,
    limit_usdt: Optional[float] = None,
    demo_balance: Optional[float] = None,
    account_type: str = "mainnet",
):
    """
    Chạy 1 chu kỳ trong thread.
    execute_orders=False: chỉ phân tích.
    execute_orders=True, selected_symbols: chỉ vào lệnh các symbol đó (và đạt ngưỡng).
    limit_usdt: tổng USDT tối đa cho lần vào lệnh, bot chia đều cho từng coin.
    demo_balance: dùng số dư demo (USDT) thay vì balance thật để tính size.
    account_type: mainnet | testnet — dùng key từ form ví tương ứng khi vào lệnh.
    """
    global _run_status
    _run_status["status"] = "running"
    _run_status["started_at"] = datetime.now().isoformat()
    _run_status["signals"] = []
    _run_status["executed"] = []
    _run_status["error"] = None
    try:
        from dotenv import load_dotenv
        import importlib
        load_dotenv(override=True)
        import config as config_module
        importlib.reload(config_module)  # Đọc lại .env (SL, TP, leverage sau khi user "Lưu cấu hình")
        from main import setup_logging
        setup_logging()
        TRADE_MODE = config_module.TRADE_MODE
        MIN_CONFIDENCE = config_module.MIN_CONFIDENCE
        LIMIT_USDT_PER_RUN = config_module.LIMIT_USDT_PER_RUN
        from ai_engine import AIEngine
        from order_executor import OrderExecutor

        engine = AIEngine()
        # Phân tích only: lấy tất cả symbol, include_below_threshold=True để hiển thị hết.
        # Vào lệnh có selected_symbols: vẫn dùng include_below_threshold=True cho các symbol đã chọn
        # để luôn có signal (tránh lần chạy 2 trả về rỗng do dữ liệu thay đổi). execute_batch sẽ chỉ thực thi signal >= ngưỡng.
        symbols_to_analyze = selected_symbols if (execute_orders and selected_symbols) else None
        include_all = not execute_orders or (execute_orders and selected_symbols)
        signals = engine.get_signals(
            symbols=symbols_to_analyze,
            include_below_threshold=include_all,
        )
        from data_collector import DataCollector
        dc = DataCollector()
        _run_status["signals"] = []
        for s in signals:
            chart_summary = dc.get_chart_summary(s.symbol, "4h") if dc else None
            _run_status["signals"].append(_signal_to_dict(s, chart_summary))

        if execute_orders and signals:
            client = _get_client_for_account(account_type)
            executor = OrderExecutor(client=client)
            limit_total = limit_usdt if limit_usdt and limit_usdt > 0 else (LIMIT_USDT_PER_RUN or None)
            if limit_total and limit_total <= 0:
                limit_total = None
            executed_list = executor.execute_batch(
                signals,
                balance_override=demo_balance,
                limit_usdt_total=limit_total,
            )
            _run_status["executed"] = executed_list
    except Exception as e:
        _run_status["error"] = str(e)
    finally:
        _run_status["status"] = "idle"
        _run_status["finished_at"] = datetime.now().isoformat()
        # Lưu kết quả chu kỳ để sau khi reload/restart vẫn còn
        try:
            last_run_path = Path(__file__).resolve().parent / "data" / "last_run.json"
            last_run_path.parent.mkdir(parents=True, exist_ok=True)
            with open(last_run_path, "w", encoding="utf-8") as f:
                json.dump({
                    "status": _run_status["status"],
                    "signals": _run_status.get("signals", []),
                    "executed": _run_status.get("executed", []),
                    "error": _run_status.get("error"),
                    "started_at": _run_status.get("started_at"),
                    "finished_at": _run_status.get("finished_at"),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        # Đọc vài dòng log mới nhất
        log_path = Path("logs")
        if log_path.exists():
            log_files = sorted(log_path.glob("bot_*.log"), key=os.path.getmtime, reverse=True)
            if log_files:
                try:
                    with open(log_files[0], "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        _run_status["log_tail"] = lines[-50:] if len(lines) > 50 else lines
                except Exception:
                    _run_status["log_tail"] = []


def _get_log_tail(lines=80):
    """Lấy N dòng cuối file log mới nhất."""
    log_path = Path("logs")
    if not log_path.exists():
        return []
    log_files = sorted(log_path.glob("bot_*.log"), key=os.path.getmtime, reverse=True)
    if not log_files:
        return []
    try:
        with open(log_files[0], "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception:
        return []


def _get_config_safe():
    """Lấy config hiện tại (sau load_dotenv). Trả về cả giá trị thô để chỉnh trong form."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    from config import (
        TRADE_MODE,
        MIN_CONFIDENCE,
        BINANCE_BASE_URL,
        DEFAULT_LEVERAGE,
        STOP_LOSS_PERCENT,
        TAKE_PROFIT_PERCENT,
        MAX_POSITION_PERCENT,
        LIMIT_USDT_PER_RUN,
        SYMBOLS,
    )
    base_url = (BINANCE_BASE_URL or "").strip().lower()
    is_testnet = "testnet" in base_url or "demo-fapi" in base_url
    return {
        "trade_mode": TRADE_MODE,
        "binance_base_url": BINANCE_BASE_URL or "",
        "is_testnet": is_testnet,
        "min_confidence": MIN_CONFIDENCE,
        "min_confidence_pct": f"{MIN_CONFIDENCE * 100:.0f}%",
        "default_leverage": DEFAULT_LEVERAGE,
        "stop_loss_percent": STOP_LOSS_PERCENT,
        "take_profit_percent": TAKE_PROFIT_PERCENT,
        "max_position_percent": MAX_POSITION_PERCENT,
        "limit_usdt_per_run": LIMIT_USDT_PER_RUN,
        "symbols_count": len(SYMBOLS),
        "symbols": list(SYMBOLS),
    }


def _get_balance_safe(account_type: str = "mainnet"):
    """
    Lấy số dư Futures. account_type: 'mainnet' | 'testnet'.
    Ưu tiên key từ form ví (wallet_keys.json), không có thì dùng .env.
    Trả về (balance_float, error_message).
    """
    try:
        from binance_client import BinanceFuturesClient
        keys = _load_wallet_keys()
        k = keys.get(account_type) or {}
        api_key = (k.get("api_key") or "").strip()
        api_secret = (k.get("api_secret") or "").strip()
        from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_BASE_URL
        if not api_key or not api_secret:
            api_key = BINANCE_API_KEY
            api_secret = BINANCE_API_SECRET
        base_url = TESTNET_BASE_URL if account_type == "testnet" else ""
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)
        balance = client.get_balance()
        if not balance:
            detail = client.get_last_balance_error() or "Không lấy được balance."
            msg = detail[:200] if len(detail) > 200 else detail
            if account_type == "testnet":
                msg += " — Dùng API key từ https://testnet.binancefuture.com (không dùng key mainnet)."
            else:
                msg += " Kiểm tra API key / IP / quyền Futures trên Binance."
            return None, msg
        assets = balance if isinstance(balance, list) else (balance.get("assets") or [])
        for b in assets:
            if isinstance(b, dict) and b.get("asset") == "USDT":
                return float(b.get("availableBalance", 0) or b.get("balance", 0)), None
        return None, None
    except Exception as e:
        err = str(e)
        if "-2015" in err or "Invalid API-key" in err or "401" in err:
            return None, "Lỗi 401/-2015: Kiểm tra API key, whitelist IP và bật quyền Futures. Testnet: dùng key từ testnet.binancefuture.com."
        return None, str(e)[:200]


def _load_template():
    path = Path(__file__).parent / "templates" / "dashboard.html"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_portfolio_template():
    path = Path(__file__).parent / "templates" / "portfolio.html"
    with open(path, encoding="utf-8") as f:
        return f.read()


@app.route("/")
def index():
    return render_template_string(_load_template())


@app.route("/portfolio")
def portfolio():
    """Portfolio / Projects page — AI projects & experiments."""
    return render_template_string(_load_portfolio_template())


@app.route("/api/status")
def api_status():
    cfg = _get_config_safe()
    balance_mode = request.args.get("balance_mode", "mainnet")
    if balance_mode in ("demo_500", "demo_1000", "demo_5000"):
        balance = float(balance_mode.replace("demo_", ""))
        return jsonify({
            "trade_mode": cfg["trade_mode"],
            "balance_usdt": balance,
            "balance_error": None,
            "min_confidence_pct": cfg["min_confidence_pct"],
            "default_leverage": cfg["default_leverage"],
            "is_testnet": False,
        })
    account_type = "testnet" if balance_mode == "testnet" else "mainnet"
    balance, balance_error = _get_balance_safe(account_type=account_type)
    return jsonify({
        "trade_mode": cfg["trade_mode"],
        "balance_usdt": round(balance, 2) if balance is not None else None,
        "balance_error": balance_error,
        "min_confidence_pct": cfg["min_confidence_pct"],
        "default_leverage": cfg["default_leverage"],
        "is_testnet": (account_type == "testnet"),
    })


@app.route("/api/wallet-keys", methods=["GET", "POST"])
def api_wallet_keys():
    """GET: trả về trạng thái đã lưu key (masked). POST: lưu key cho mainnet hoặc testnet."""
    if request.method == "GET":
        keys = _load_wallet_keys()
        out = {}
        for t in ("mainnet", "testnet"):
            k = keys.get(t) or {}
            api_key = (k.get("api_key") or "").strip()
            out[t] = {"saved": bool(api_key), "key_masked": ("...%s" % api_key[-4:]) if len(api_key) >= 4 else ""}
        return jsonify(out)
    data = request.get_json() or {}
    account_type = (data.get("account_type") or "").strip().lower()
    if account_type not in ("mainnet", "testnet"):
        return jsonify({"ok": False, "message": "account_type phải là mainnet hoặc testnet."}), 400
    api_key = (data.get("api_key") or "").strip()
    api_secret = (data.get("api_secret") or "").strip()
    if not api_key or not api_secret:
        return jsonify({"ok": False, "message": "Cần nhập cả API Key và API Secret."}), 400
    try:
        _save_wallet_keys(account_type, api_key, api_secret)
        return jsonify({"ok": True, "message": "Đã lưu key %s. Tài khoản sẽ dùng key này khi chọn tương ứng." % account_type})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:120]}), 500


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        data = request.get_json() or {}
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            return jsonify({"ok": False, "message": "File .env không tồn tại."}), 400
        # Đọc .env hiện tại
        lines = []
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)}), 500
        # Map key .env
        key_map = {
            "min_confidence": "MIN_CONFIDENCE",
            "default_leverage": "DEFAULT_LEVERAGE",
            "stop_loss_percent": "STOP_LOSS_PERCENT",
            "take_profit_percent": "TAKE_PROFIT_PERCENT",
            "max_position_percent": "MAX_POSITION_PERCENT",
            "limit_usdt_per_run": "LIMIT_USDT_PER_RUN",
        }
        updated = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue
            if "=" in stripped:
                key = stripped.split("=")[0].strip()
                for py_key, env_key in key_map.items():
                    if key == env_key and py_key in data:
                        val = data[py_key]
                        if isinstance(val, float):
                            val = str(val) if env_key != "MIN_CONFIDENCE" else str(round(val, 2))
                        else:
                            val = str(val)
                        new_lines.append(f"{env_key}={val}\n")
                        updated.add(py_key)
                        break
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        # Append keys chưa có trong file
        for py_key, env_key in key_map.items():
            if py_key in data and py_key not in updated:
                val = data[py_key]
                new_lines.append(f"{env_key}={val}\n")
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)}), 500
        return jsonify({"ok": True, "message": "Đã lưu cấu hình."})
    return jsonify(_get_config_safe())


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


@app.route("/api/open-positions")
def api_open_positions():
    """Lệnh đang chạy: vị thế mở từ Binance, PNL/ROI realtime. Dùng key theo balance_mode (mainnet/testnet)."""
    balance_mode = request.args.get("balance_mode", "mainnet")
    account_type = "testnet" if balance_mode == "testnet" else "mainnet"
    try:
        client = _get_client_for_account(account_type)
        raw = client.get_position_risk()
        # Binance lỗi có thể trả dict {"code": -2015, "msg": "..."} thay vì list
        if not isinstance(raw, list):
            err = ""
            if isinstance(raw, dict):
                err = raw.get("msg", raw.get("error", str(raw)))
            return jsonify({"positions": [], "error": err or "API trả về định dạng không đúng."})
        risks = raw
        out = []
        for r in risks:
            if not isinstance(r, dict):
                continue
            amt = _safe_float(r.get("positionAmt"))
            if amt == 0:
                continue
            entry = _safe_float(r.get("entryPrice"))
            mark = _safe_float(r.get("markPrice")) or entry
            pnl = _safe_float(r.get("unRealizedProfit") or r.get("unrealizedProfit"))
            margin = _safe_float(r.get("initialMargin"))
            lev = int(_safe_float(r.get("leverage"), 1)) or 1
            roi_pct = (pnl / margin * 100) if margin and margin > 0 else 0.0
            side = "LONG" if amt > 0 else "SHORT"
            out.append({
                "symbol": r.get("symbol", ""),
                "side": side,
                "position_amt": amt,
                "entry_price": round(entry, 4),
                "mark_price": round(mark, 4),
                "unrealized_pnl": round(pnl, 2),
                "roi_pct": round(roi_pct, 2),
                "leverage": lev,
            })
        return jsonify({"positions": out})
    except Exception as e:
        err = str(e)
        if "-2015" in err or "Invalid API-key" in err or "401" in err:
            return jsonify({"positions": [], "error": "API key không hợp lệ hoặc chưa bật Futures. Với Testnet hãy dùng key từ testnet.binancefuture.com."})
        return jsonify({"positions": [], "error": str(e)})


@app.route("/api/position-history")
def api_position_history():
    """Lịch sử vị thế / lãi lỗ đã thực hiện từ Binance."""
    try:
        from binance_client import BinanceFuturesClient
        client = BinanceFuturesClient()
        # Binance: gửi startTime/endTime để lấy tối đa 3 tháng (mặc định chỉ 7 ngày)
        income = client.get_income_history(
            income_type="REALIZED_PNL",
            limit=1000,
        )
        out = []
        for row in income:
            symbol = row.get("symbol") or ""
            income_val = float(row.get("income", 0))
            ts = int(row.get("time", 0))
            out.append({
                "symbol": symbol or "—",
                "realized_pnl_usdt": round(income_val, 2),
                "time": ts,
                "time_str": datetime.fromtimestamp(ts / 1000).strftime("%d/%m/%Y %H:%M:%S") if ts else "--",
                "income_type": row.get("incomeType", "REALIZED_PNL"),
            })
        out.sort(key=lambda x: x["time"], reverse=True)
        return jsonify({"items": out[:100]})
    except Exception as e:
        return jsonify({"items": [], "error": str(e)})


@app.route("/api/symbols")
def api_symbols():
    cfg = _get_config_safe()
    return jsonify({"symbols": cfg.get("symbols", [])})


@app.route("/api/indicators")
def api_indicators():
    symbol = request.args.get("symbol", "BTCUSDT").upper()
    try:
        from data_collector import DataCollector
        dc = DataCollector()
        ind = dc.get_latest_indicators(symbol, "4h")
        summary = dc.get_chart_summary(symbol, "4h") if ind else None
        if not ind:
            return jsonify({"error": "Không lấy được chỉ báo."}), 404
        return jsonify({"symbol": symbol, "indicators": ind, "chart_summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Chat với AI (stub: có thể tích hợp OpenAI sau)."""
    data = request.get_json() or {}
    question = (data.get("message") or data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "reply": "Vui lòng nhập câu hỏi."}), 400
    # Stub: trả lời dựa trên context đơn giản (có thể thay bằng OpenAI API)
    try:
        from news_analyzer import NewsAnalyzer
        news = NewsAnalyzer()
        trend = news.get_latest_trends_summary()
    except Exception:
        trend = "Không lấy được tin tức."
    reply = (
        f"Bạn hỏi: {question}\n\n"
        f"Tin tức/xu hướng hiện tại: {trend}\n\n"
        "Để có phân tích sâu hơn (biểu đồ, xu hướng, coin cụ thể), hãy thêm OPENAI_API_KEY vào .env và tích hợp model trong dashboard."
    )
    return jsonify({"ok": True, "reply": reply})


LAST_RUN_PATH = Path(__file__).resolve().parent / "data" / "last_run.json"


def _load_last_run_if_needed():
    """Khi idle và chưa có dữ liệu (vd: sau restart), nạp kết quả chu kỳ lần trước từ file."""
    global _run_status
    if _run_status.get("status") != "idle":
        return
    if _run_status.get("signals") or _run_status.get("executed"):
        return
    if not LAST_RUN_PATH.exists():
        return
    try:
        with open(LAST_RUN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _run_status["signals"] = data.get("signals") or []
        _run_status["executed"] = data.get("executed") or []
        _run_status["error"] = data.get("error")
        _run_status["started_at"] = data.get("started_at")
        _run_status["finished_at"] = data.get("finished_at")
    except Exception:
        pass


@app.route("/api/run-status")
def api_run_status():
    _load_last_run_if_needed()
    return jsonify(_run_status)


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json() or {}
    execute = data.get("execute", False)
    selected_symbols = data.get("symbols")  # list symbol được chọn để vào lệnh (optional)
    limit_usdt = data.get("limit_usdt")
    if limit_usdt is not None:
        try:
            limit_usdt = float(limit_usdt)
        except (TypeError, ValueError):
            limit_usdt = None
    demo_balance = data.get("demo_balance")
    if demo_balance is not None:
        try:
            demo_balance = float(demo_balance)
        except (TypeError, ValueError):
            demo_balance = None
    balance_mode = (data.get("balance_mode") or "").strip().lower()
    account_type = "testnet" if balance_mode == "testnet" else "mainnet"
    if _run_status["status"] == "running":
        return jsonify({"ok": False, "message": "Chu kỳ đang chạy."}), 409
    threading.Thread(
        target=_run_cycle_background,
        args=(execute,),
        kwargs={
            "selected_symbols": selected_symbols if isinstance(selected_symbols, list) else None,
            "limit_usdt": limit_usdt,
            "demo_balance": demo_balance,
            "account_type": account_type,
        },
        daemon=True,
    ).start()
    return jsonify({"ok": True, "message": "Đã bắt đầu."})


@app.route("/api/logs")
def api_logs():
    lines = request.args.get("lines", 100, type=int)
    lines = min(200, max(10, lines))
    tail = _get_log_tail(lines)
    return jsonify({"lines": tail})


if __name__ == "__main__":
    print("Dashboard: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
