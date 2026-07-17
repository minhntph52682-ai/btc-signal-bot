"""
Lay du lieu gia (nen + gia hien tai).
UU TIEN OKX (de khop dung gia tren web OKX), neu loi thi dung Binance du phong.
"""
import json
import urllib.request
import urllib.error

import okx

BINANCE_HOSTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",  # host du lieu, thuong khong bi chan
]


def _get(path):
    last_err = None
    for host in BINANCE_HOSTS:
        try:
            req = urllib.request.Request(
                host + path, headers={"User-Agent": "btc-signal-bot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            continue
    raise RuntimeError(f"Khong ket noi duoc Binance: {last_err}")


def _get_klines_binance(symbol, interval, limit):
    path = f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    raw = _get(path)
    candles = []
    for k in raw:
        candles.append(
            {
                "time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
        )
    return candles


def get_klines(symbol, interval="1h", limit=200):
    """Nen: uu tien OKX, loi thi dung Binance. Tra ve list dict cu -> moi."""
    try:
        candles = okx.get_klines(symbol, interval, limit)
        if candles:
            return candles
    except Exception:
        pass
    return _get_klines_binance(symbol, interval, limit)


def get_price(symbol):
    """Gia hien tai: uu tien OKX (khop web OKX), loi thi dung Binance."""
    try:
        return okx.get_price(symbol)
    except Exception:
        pass
    d = _get(f"/api/v3/ticker/price?symbol={symbol}")
    return float(d["price"])
