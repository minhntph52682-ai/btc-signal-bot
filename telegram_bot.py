"""Gui tin nhan qua Telegram Bot API (khong can thu vien ngoai)."""
import json
import urllib.request
import urllib.parse
import urllib.error

import config

API = "https://api.telegram.org/bot{token}/{method}"


def _call(method, params):
    url = API.format(token=config.TELEGRAM_TOKEN, method=method)
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Telegram HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Telegram loi ket noi: {e}")


def send_message(text, chat_id=None, parse_mode="HTML"):
    """Gui tin nhan toi chat_id (mac dinh lay tu config.CHAT_ID)."""
    chat_id = chat_id or config.CHAT_ID
    if not chat_id:
        raise RuntimeError(
            "Chua co CHAT_ID. Chay 'py get_chat_id.py' de lay ID roi dat vao config."
        )
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true",
    }
    try:
        return _call("sendMessage", params)
    except RuntimeError as e:
        # Neu loi do parse HTML -> gui lai dang van ban thuong (bo dinh dang)
        if "parse" in str(e).lower() or "entit" in str(e).lower():
            params.pop("parse_mode", None)
            return _call("sendMessage", params)
        raise


def edit_message(chat_id, message_id, text, parse_mode="HTML"):
    """Sua noi dung 1 tin nhan da gui (dung de cap nhat gia truc tiep)."""
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true",
    }
    try:
        return _call("editMessageText", params)
    except RuntimeError as e:
        s = str(e).lower()
        # "message is not modified" -> khong sao, bo qua
        if "not modified" in s:
            return None
        if "parse" in s or "entit" in s:
            params.pop("parse_mode", None)
            return _call("editMessageText", params)
        raise


def get_updates(offset=None):
    """Lay tin nhan gan day (dung de tim chat_id)."""
    params = {"timeout": 5}
    if offset is not None:
        params["offset"] = offset
    return _call("getUpdates", params)
