"""
Lay muc don bay TOI DA cua tung coin theo san OKX (API cong khai, khong can key).
Vi du: BTC-USDT-SWAP -> x100, BNB -> x50...

Ket qua duoc cache trong bo nho de khong goi API lien tuc.
"""
import json
import urllib.request
import urllib.error

import config

_OKX_HOST = "https://www.okx.com"
_OKX_URL = _OKX_HOST + "/api/v5/public/instruments?instType=SWAP"
_cache = None  # dict: instId -> max leverage (int)

# Loai gia lay theo web OKX: "SWAP" (perp/futures - co don bay) hoac "SPOT".
PRICE_TYPE = "SWAP"

# Chuyen khung Binance -> khung OKX (bar).
_BAR_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
    "1d": "1D", "1w": "1W",
}


def _get(path):
    req = urllib.request.Request(_OKX_HOST + path, headers={"User-Agent": "btc-signal-bot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def _inst(symbol, kind=None):
    """'BTCUSDT' -> 'BTC-USDT-SWAP' (hoac -SPOT)."""
    kind = kind or getattr(config, "OKX_PRICE_TYPE", PRICE_TYPE)
    s = symbol.upper()
    for quote in ("USDT", "USDC", "USD"):
        if s.endswith(quote):
            base = s[: -len(quote)]
            pair = f"{base}-{quote}"
            break
    else:
        pair = s
    return f"{pair}-SWAP" if kind == "SWAP" else pair


def get_price(symbol):
    """Gia moi nhat tren OKX (theo PRICE_TYPE). Nem loi neu that bai."""
    d = _get(f"/api/v5/market/ticker?instId={_inst(symbol)}")
    return float(d["data"][0]["last"])


def _rows_to_candles(rows):
    """rows moi->cu (OKX) -> list dict cu->moi."""
    out = []
    for k in reversed(rows):
        out.append({
            "time": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return out


def get_klines(symbol, interval="1h", limit=200):
    """Nen tu OKX. Tra ve list dict {time,open,high,low,close,volume} cu -> moi."""
    bar = _BAR_MAP.get(interval.lower(), "1H")
    limit = min(int(limit), 300)  # OKX gioi han 300 nen moi lan
    d = _get(f"/api/v5/market/candles?instId={_inst(symbol)}&bar={bar}&limit={limit}")
    return _rows_to_candles(d.get("data", []))


def get_klines_history(symbol, interval="1h", total=1000):
    """
    Lay nhieu nen lich su hon bang cach phan trang (dung cho backtest).
    Gop nhieu lan goi API (moi lan toi da 100 nen).
    """
    bar = _BAR_MAP.get(interval.lower(), "1H")
    inst = _inst(symbol)
    collected = []  # moi -> cu
    after = None
    while len(collected) < total:
        path = f"/api/v5/market/history-candles?instId={inst}&bar={bar}&limit=100"
        if after:
            path += f"&after={after}"
        d = _get(path)
        rows = d.get("data", [])
        if not rows:
            break
        collected.extend(rows)
        after = rows[-1][0]  # ts cu nhat -> trang sau lay cu hon
    return _rows_to_candles(collected[:total])


def _load():
    global _cache
    if _cache is not None:
        return _cache
    _cache = {}
    try:
        req = urllib.request.Request(_OKX_URL, headers={"User-Agent": "btc-signal-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r).get("data", [])
        for x in data:
            try:
                _cache[x["instId"]] = int(float(x.get("lever", 0)))
            except (ValueError, TypeError):
                continue
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        pass  # loi mang -> tra ve cache rong, ben goi tu xu ly
    return _cache


def _inst_id(symbol):
    """'BTCUSDT' -> 'BTC-USDT-SWAP'."""
    s = symbol.upper()
    for quote in ("USDT", "USDC", "USD"):
        if s.endswith(quote):
            base = s[: -len(quote)]
            return f"{base}-{quote}-SWAP"
    return f"{s}-SWAP"


def get_max_leverage(symbol, default=None):
    """
    Tra ve don bay toi da OKX cho phep cho coin nay (int).
    Neu khong lay duoc (mang loi / coin khong co tren OKX) -> tra ve 'default'.
    """
    data = _load()
    return data.get(_inst_id(symbol), default)


def refresh():
    """Xoa cache de lan sau lay lai tu OKX."""
    global _cache
    _cache = None
