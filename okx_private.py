"""
Goi API RIENG TU cua OKX (can API key) de xem vi the / lenh dang mo.
Yeu cau 3 thong tin trong local_config.py: OKX_API_KEY, OKX_API_SECRET, OKX_API_PASSPHRASE.
NEN tao API key READ-ONLY (chi doc) - khong bat Trade/Withdraw cho an toan.
"""
import json
import hmac
import base64
import hashlib
import datetime
import urllib.request
import urllib.error

import config

_HOST = "https://www.okx.com"


def _timestamp():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def has_keys():
    return bool(config.OKX_API_KEY and config.OKX_API_SECRET and config.OKX_API_PASSPHRASE)


def _request(method, path, body=""):
    if not has_keys():
        raise RuntimeError("Chua cau hinh OKX API key (xem huong dan lenh /lenh).")
    ts = _timestamp()
    prehash = ts + method + path + body
    sign = base64.b64encode(
        hmac.new(config.OKX_API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "OK-ACCESS-KEY": config.OKX_API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": config.OKX_API_PASSPHRASE,
        "Content-Type": "application/json",
        "User-Agent": "btc-signal-bot/1.0",
    }
    data = body.encode() if body else None
    req = urllib.request.Request(_HOST + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OKX HTTP {e.code}: {e.read().decode('utf-8','ignore')}")
    if d.get("code") not in ("0", 0):
        raise RuntimeError(f"OKX loi: {d.get('msg')} (code {d.get('code')})")
    return d.get("data", [])


def get_positions():
    """Danh sach vi the dang mo (chi lay cai co khoi luong != 0)."""
    data = _request("GET", "/api/v5/account/positions")
    out = []
    for p in data:
        try:
            pos = float(p.get("pos") or 0)
        except ValueError:
            pos = 0
        if pos == 0:
            continue
        out.append(p)
    return out


def get_balance():
    """Tong tai san (USDT) trong tai khoan giao dich."""
    data = _request("GET", "/api/v5/account/balance")
    if not data:
        return None
    return data[0]


def get_tpsl_map():
    """
    Lay TP/SL dang cho (lenh dieu kien/OCO) theo tung instId.
    Tra ve dict: instId -> {"tp": <gia>, "sl": <gia>}.
    """
    result = {}
    for ot in ("oco", "conditional"):
        try:
            data = _request("GET", f"/api/v5/trade/orders-algo-pending?ordType={ot}")
        except Exception:
            continue
        for o in data:
            inst = o.get("instId")
            if not inst:
                continue
            tp = o.get("tpTriggerPx") or ""
            sl = o.get("slTriggerPx") or ""
            cur = result.setdefault(inst, {"tp": "", "sl": ""})
            if tp and not cur["tp"]:
                cur["tp"] = tp
            if sl and not cur["sl"]:
                cur["sl"] = sl
    return result
