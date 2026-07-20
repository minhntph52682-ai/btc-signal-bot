"""
Khoa Entry / SL / TP CO DINH cho tung coin khi tin hieu xuat hien.
Muc dich: SL khong bi "troi" theo gia moi lan tinh lai -> can volume moi chinh xac.

Ca tin hieu tu dong, /tinhieu va /von deu dung chung khoa nay.
Luu ra locks.json de giu nguyen ke ca khi khoi dong lai bot.
"""
import os
import json

_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locks.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            with open(_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except (FileNotFoundError, ValueError):
            _cache = {}
    return _cache


def _save():
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f)
    except OSError:
        pass


def clear(symbol):
    data = _load()
    if symbol in data:
        del data[symbol]
        _save()


def apply(res, renew=False):
    """
    Khoa entry/sl/tp/leverage cho res theo huong nghieng (lean).
    - Neu da co khoa cung huong -> DUNG LAI gia tri cu (SL co dinh).
    - Neu doi huong / chua co / renew=True -> tao khoa moi tu gia tri hien tai.
    - Neu di ngang (NEUTRAL) -> xoa khoa.
    Tra ve res (da cap nhat sl/tp/leverage + them 'entry' la gia khoa).
    """
    direction = res.get("lean") or res.get("side")
    symbol = res.get("symbol")
    if direction in (None, "NEUTRAL"):
        clear(symbol)
        return res

    data = _load()
    lk = data.get(symbol)
    if (not lk) or lk.get("side") != direction or renew:
        lk = {
            "side": direction,
            "entry": res["price"],
            "sl": res["sl"],
            "tp": res["tp"],
            "leverage": res.get("leverage"),
            "leverage_max": res.get("leverage_max"),
        }
        data[symbol] = lk
        _save()

    res = dict(res)
    res["entry"] = lk["entry"]
    res["sl"] = lk["sl"]
    res["tp"] = lk["tp"]
    res["leverage"] = lk["leverage"]
    res["leverage_max"] = lk["leverage_max"]
    return res
