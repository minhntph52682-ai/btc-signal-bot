"""
Danh sach coin theo doi (co the them/xoa luc chay, luu ra file watchlist.json).
Mac dinh lay tu config.SYMBOLS neu chua co file.
"""
import os
import json

import config

_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
_cache = None


def _norm(text):
    """'btc' -> 'BTCUSDT'."""
    s = text.strip().upper().replace(" ", "")
    if not s.endswith("USDT"):
        s += "USDT"
    return s


def _load():
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            _cache = [str(x).upper() for x in data]
            return _cache
    except (FileNotFoundError, ValueError):
        pass
    _cache = list(config.SYMBOLS)
    return _cache


def _save():
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f)
    except OSError:
        pass


def get():
    """Tra ve danh sach coin hien tai."""
    return list(_load())


def add(symbol):
    """Them coin. Tra ve (ten_da_chuan, da_ton_tai_chua)."""
    sym = _norm(symbol)
    lst = _load()
    if sym in lst:
        return sym, True
    lst.append(sym)
    _save()
    return sym, False


def remove(symbol):
    """Xoa coin. Tra ve (ten, da_xoa_khong)."""
    sym = _norm(symbol)
    lst = _load()
    if sym in lst:
        lst.remove(sym)
        _save()
        return sym, True
    return sym, False
