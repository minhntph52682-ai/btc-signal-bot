"""
Bot tin hieu BTC / crypto.

Bot lam 2 viec cung luc:
  1) LANG NGHE lenh nguoi dung (/start, /gia, /tinhieu...) va TU DONG lay chat ID
     de tra loi dung nguoi da nhan (khong can dat CHAT_ID thu cong).
  2) TU DONG QUET thi truong moi LOOP_SECONDS giay, gui tin hieu LONG/SHORT
     manh (>= MIN_SCORE) cho TAT CA nguoi da tung nhan tin voi bot.

Cach chay:
  py bot.py           -> chay bot (lang nghe lenh + tu dong quet)
  py bot.py --once    -> quet 1 lan roi thoat (dung de test, khong lang nghe)
"""
import os
import sys
import json
import time
import html
import datetime
import threading

import config
import market
import strategy
import telegram_bot
import commands
import watchlist
import locks

# Luu tin hieu lan truoc cua tung coin de tranh spam (ONLY_ON_CHANGE)
_last_side = {}
# Luu thoi diem gui gan nhat cua tung coin (de gian cach khi nhac lai tin hieu)
_last_sent_time = {}
# Coin vua kiem tra gan nhat cua tung chat (de /von tu dung lai)
_last_coin = {}

# File luu danh sach chat ID da nhan tin voi bot (de gui tin hieu tu dong)
_SUBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscribers.json")


# ---------- Quan ly danh sach nguoi dung (subscribers) ----------
def load_subscribers():
    subs = set()
    if config.CHAT_ID:
        subs.add(str(config.CHAT_ID))
    try:
        with open(_SUBS_FILE, "r", encoding="utf-8") as f:
            for cid in json.load(f):
                subs.add(str(cid))
    except (FileNotFoundError, ValueError):
        pass
    return subs


def save_subscribers(subs):
    try:
        with open(_SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(subs), f)
    except OSError as e:
        print(f"[LOI luu subscribers] {e}")


# ---------- Dinh dang ----------
def _fmt_price(p):
    if p is None:
        return "-"
    if p >= 100:
        return f"{p:,.2f}"
    if p >= 1:
        return f"{p:,.4f}"
    return f"{p:.6f}"


def format_signal(res, repeat=False, on_demand=False):
    """
    Tao noi dung tin nhan HTML cho 1 tin hieu.
    repeat=True    -> danh dau nhac lai.
    on_demand=True -> khi nguoi dung HOI THANG 1 coin: luon hien huong (lean),
                      du tin hieu manh hay yeu.
    """
    # Huong hien thi: khi hoi thang -> dung 'lean' (luon co huong neu diem != 0)
    disp = res["side"]
    if on_demand and disp == "NEUTRAL":
        disp = res.get("lean", "NEUTRAL")

    actionable = bool(res.get("actionable"))
    lean_word = {"LONG": "LONG (mua)", "SHORT": "SHORT (ban)"}.get(disp, "")

    if disp == "NEUTRAL":
        head = "⚪ <b>DI NGANG</b> (chua ro huong)"
    elif not actionable:
        # Co huong nghieng nhung CHUA du dieu kien vao lenh -> chi quan sat,
        # KHONG hien tieu de xanh/do de tranh nham la khuyen nghi vao lenh.
        head = f"⚪ <b>QUAN SAT</b> — nghieng {lean_word}, chua du dieu kien vao lenh"
    elif disp == "LONG":
        head = "\U0001F7E2 <b>LONG</b> (Mua)"
    else:  # SHORT du manh
        head = "\U0001F534 <b>SHORT</b> (Ban)"

    stars = "⭐" * res["strength"] if res["strength"] else "-"
    tag = " \U0001F501 <i>nhac lai</i>" if repeat else ""
    lines = [
        f"{head}  |  <b>{html.escape(res['symbol'])}</b>  ({config.INTERVAL}){tag}",
        f"Gia hien tai: <b>{_fmt_price(res['price'])}</b> USDT",
        f"Do manh: {stars} ({res['strength']}/4)",
    ]

    # Khi hoi thang nhung tin hieu chua du manh -> nhac nho ro rang
    if on_demand and disp != "NEUTRAL" and not actionable:
        lines.append(
            "⚠️ <i>Chua du dieu kien vao lenh (tin hieu yeu / thi truong di ngang). "
            "Chi nen QUAN SAT, chua nen vao.</i>"
        )

    if disp != "NEUTRAL" and res["sl"] is not None:
        entry = res.get("entry", res["price"])
        if actionable:
            lines.append(f"\U0001F4CD Entry (diem vao): <b>{_fmt_price(entry)}</b>")
            lev = res.get("leverage")
            if lev:
                cap = res.get("leverage_max")
                extra = f" — OKX toi da x{cap}" if cap else ""
                lines.append(
                    f"\U0001F4A5 Don bay goi y: <b>x{lev}</b>{extra}\n"
                    f"   <i>(nen dung che do co lap / isolated)</i>"
                )
            lines.append(f"\U0001F3AF TP (chot loi): <b>{_fmt_price(res['tp'])}</b>")
            lines.append(f"\U0001F6D1 SL (cat lo, CO DINH): <b>{_fmt_price(res['sl'])}</b>")
        else:
            # Tin hieu yeu -> chi hien MUC THAM KHAO, KHONG goi y don bay
            # (tranh nham thanh lenh vao).
            lines.append("\U0001F4CA <i>Muc tham khao (chi khi thi truong xac nhan ro):</i>")
            lines.append(
                f"   Entry ~{_fmt_price(entry)} | "
                f"TP ~{_fmt_price(res['tp'])} | SL ~{_fmt_price(res['sl'])}"
            )

    lines.append("")
    lines.append("<i>Ly do:</i>")
    for rz in res["reasons"]:
        lines.append(f"  • {html.escape(rz)}")

    lines.append("")
    lines.append("<i>Chi mang tinh tham khao, khong phai loi khuyen dau tu.</i>")
    return "\n".join(lines)


# ---------- Lang nghe lenh nguoi dung ----------
def poll_commands(subs):
    """Doc tin nhan moi, tu them chat ID, tra loi lenh. Tra ve offset moi."""
    offset = poll_commands._offset
    try:
        res = telegram_bot.get_updates(offset=offset)
    except Exception as e:
        print(f"[LOI doc tin nhan] {e}")
        return

    for u in res.get("result", []):
        poll_commands._offset = u["update_id"] + 1
        msg = u.get("message") or u.get("channel_post")
        if not msg:
            continue
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip()
        if chat_id is None:
            continue

        cid = str(chat_id)
        chat_type = chat.get("type", "")   # private / group / supergroup / channel
        name = chat.get("title") or chat.get("first_name") or chat.get("username") or cid

        # Lay ten lenh (bo dau / va @tenbot)
        cmd = ""
        if text.startswith("/"):
            cmd = text.split()[0][1:].split("@")[0].lower()

        # Lenh TAT tin hieu tu dong cho chat/nhom nay
        if cmd in ("dung", "stop", "tattinhieu", "off"):
            if cid in subs:
                subs.discard(cid)
                save_subscribers(subs)
            _reply(chat_id, "\U0001F515 Da TAT tin hieu tu dong cho noi nay.\nGo /batdau de bat lai.")
            continue

        # Lenh BAT tin hieu tu dong cho chat/nhom nay
        if cmd in ("batdau", "start", "batinhieu", "battinhieu", "on"):
            if cid not in subs:
                subs.add(cid)
                save_subscribers(subs)
                print(f"  + Dang ky nhan tin hieu: {name} ({chat_type}, chat_id={chat_id})")

        # Tu dong nho chat ID nay (ke ca nhom) de gui tin hieu
        if cid not in subs:
            subs.add(cid)
            save_subscribers(subs)
            print(f"  + Noi moi nhan tin hieu: {name} ({chat_type}, chat_id={chat_id})")

        arg = text.split()[1] if len(text.split()) > 1 else None

        # /dunggia [coin] -> dung gia chay truc tiep
        if cmd in ("dunggia", "stopgia", "stopprice"):
            sym = _norm_symbol(arg) if arg else None
            n = stop_live_price(chat_id, sym)
            _reply(chat_id, f"⏹ Da dung {n} bang gia truc tiep." if n else "Khong co gia truc tiep nao dang chay.")
            continue

        # Ghi nho coin vua kiem tra (/p, /gia, /tinhieu <coin>) de /von dung lai
        if cmd in ("gia", "price", "p", "tinhieu", "signal", "s") and arg:
            _last_coin[cid] = _norm_symbol(arg)

        # /gia <coin> -> gia chay truc tiep (tu cap nhat lien tuc)
        if cmd in ("gia", "price", "p") and arg:
            start_live_price(chat_id, _norm_symbol(arg))
            print(f"  -> Gia truc tiep {arg} cho {name}")
            continue

        # Tra loi neu la lenh (kem coin vua kiem tra gan nhat)
        reply = commands.handle(text, format_signal, last_coin=_last_coin.get(cid))
        if reply:
            _reply(chat_id, reply)
            print(f"  -> Tra loi '{text}' cho {name} ({chat_type})")


def _reply(chat_id, text):
    try:
        telegram_bot.send_message(text, chat_id=chat_id)
    except Exception as e:
        print(f"  -> [LOI tra loi chat {chat_id}] {e}")


def _norm_symbol(text):
    s = text.strip().upper()
    return s if s.endswith("USDT") else s + "USDT"


# Quan ly cac phien gia chay truc tiep: key = (chat_id, symbol) -> Event dung
_live_stop = {}


def _live_price_line(symbol, price, prev, stopped=False):
    """Mot dong gia truc tiep, co mui ten len/xuong so voi lan truoc."""
    name = symbol.replace("USDT", "")
    arrow = ""
    if prev is not None:
        if price > prev:
            arrow = " \U0001F53A"   # tam giac do huong len
        elif price < prev:
            arrow = " \U0001F53B"   # tam giac xanh huong xuong
    now = config.now_vn().strftime("%H:%M:%S")
    if stopped:
        status = "⏹ da dung (go /p de chay lai)"
    else:
        status = "\U0001F7E2 dang cap nhat lien tuc — go /dunggia de dung"
    return (
        f"\U0001F4C8 <b>Gia {name} truc tiep (OKX)</b>\n"
        f"<b>{_fmt_price(price)}</b> USDT{arrow}\n\n"
        f"<i>{now} — {status}</i>"
    )


def start_live_price(chat_id, symbol):
    """Gui 1 tin roi tu dong sua gia LIEN TUC (khong dung) trong 1 luong rieng."""
    key = (str(chat_id), symbol)
    # Neu dang chay cho coin nay o chat nay -> dung cai cu, mo cai moi
    old = _live_stop.get(key)
    if old:
        old.set()
    stop = threading.Event()
    _live_stop[key] = stop

    def run():
        try:
            price = market.get_price(symbol)
        except Exception as e:
            _reply(chat_id, f"Khong lay duoc gia {symbol}: {e}")
            return
        try:
            res = telegram_bot.send_message(
                _live_price_line(symbol, price, None), chat_id=chat_id
            )
            mid = res.get("result", {}).get("message_id")
        except Exception as e:
            print(f"  -> [LOI gui gia truc tiep] {e}")
            return
        prev = price
        # Chay mai cho den khi bi yeu cau dung.
        # Loi mang tam thoi -> bo qua lan do, KHONG lam chet luong.
        while not stop.is_set():
            stop.wait(config.LIVE_INTERVAL)   # ngu, nhung dung ngay khi co lenh dung
            if stop.is_set():
                break
            try:
                price = market.get_price(symbol)
            except Exception:
                continue   # loi lay gia -> thu lai lan sau
            try:
                telegram_bot.edit_message(chat_id, mid, _live_price_line(symbol, price, prev))
                prev = price
            except Exception:
                continue   # loi gui Telegram (mang chap chon) -> bo qua, chay tiep
        # Sua lan cuoi -> hien "da dung" (cung bo qua neu loi mang)
        try:
            telegram_bot.edit_message(
                chat_id, mid, _live_price_line(symbol, price, prev, stopped=True)
            )
        except Exception:
            pass
        if _live_stop.get(key) is stop:
            _live_stop.pop(key, None)

    threading.Thread(target=run, daemon=True).start()


def stop_live_price(chat_id, symbol=None):
    """Dung gia truc tiep: 1 coin (symbol) hoac tat ca trong chat. Tra ve so phien da dung."""
    count = 0
    for key in list(_live_stop):
        if key[0] == str(chat_id) and (symbol is None or key[1] == symbol):
            _live_stop[key].set()
            count += 1
    return count


poll_commands._offset = None


# ---------- Quet thi truong ----------
def scan_once(subs=None, send=True):
    """Quet tat ca coin 1 lan. Gui tin hieu manh cho tat ca subscribers."""
    subs = subs if subs is not None else set()
    results = []
    for symbol in watchlist.get():
        try:
            candles = market.get_klines(symbol, config.INTERVAL, limit=200)
            res = strategy.analyze(symbol, candles)
        except Exception as e:
            print(f"[LOI] {symbol}: {e}")
            continue
        if res is None:
            continue
        results.append(res)

        tag = f"{res['side']}({res['score']:+d})"
        lev = f"x{res['leverage']}" if res.get("leverage") else "-"
        print(f"  {symbol:<10} {tag:<12} gia={_fmt_price(res['price']):<12} don_bay={lev}")

        if not send:
            continue
        # Chi tu dong bao khi la SETUP LENH thuc su (du yeu to + qua bo loc).
        if not res.get("actionable"):
            # Tin hieu khong con -> xoa khoa de lan sau vao lai la lenh moi
            locks.clear(symbol)
            continue

        changed = _last_side.get(symbol) != res["side"]
        last_t = _last_sent_time.get(symbol, 0)
        due = (time.time() - last_t) >= config.RESEND_MINUTES * 60

        # KHOA Entry/SL/TP khi tin hieu MOI -> giu CO DINH (dung chung voi /tinhieu, /von).
        disp = locks.apply(res, renew=changed)

        # Gui khi: tin hieu DOI CHIEU, HOAC den han gui lai (nhac lai tin hieu cu).
        # Neu ONLY_ON_CHANGE = True thi chi gui khi doi chieu (nhu cu).
        if not changed:
            if config.ONLY_ON_CHANGE or not due:
                continue

        text = format_signal(disp, repeat=not changed)
        sent = 0
        for cid in list(subs):
            try:
                telegram_bot.send_message(text, chat_id=cid)
                sent += 1
            except Exception as e:
                msg = str(e).lower()
                # Bot bi kick / nhom bi xoa / user chan -> tu xoa khoi danh sach
                if any(k in msg for k in ("403", "forbidden", "kicked", "deleted", "chat not found", "blocked")):
                    subs.discard(cid)
                    save_subscribers(subs)
                    print(f"    -> Da tu XOA noi khong gui duoc: {cid}")
                else:
                    print(f"    -> [LOI GUI {cid}] {e}")
        if sent:
            kind = "nhac lai" if not changed else "MOI"
            print(f"    -> Da gui tin hieu {res['side']} {symbol} ({kind}) cho {sent} nguoi")
            _last_side[symbol] = res["side"]
            _last_sent_time[symbol] = time.time()

    return results


def start_health_server():
    """Web server nho de cloud (Render...) thay co cong mo -> khong tat dich vu."""
    import http.server
    import socketserver

    port = int(os.environ.get("PORT", "10000"))

    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"BTC signal bot is running")

        def do_HEAD(self):
            # UptimeRobot mac dinh ping bang HEAD. Khong co ham nay ->
            # Python tra 501 Not Implemented -> UptimeRobot bao "Down".
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass  # khong in log HTTP cho do roi

    try:
        srv = socketserver.TCPServer(("", port), _H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"Health server chay tren cong {port}")
    except Exception as e:
        print(f"[health server loi] {e}")


def main():
    once = "--once" in sys.argv
    subs = load_subscribers()

    if not config.TELEGRAM_TOKEN:
        print("!!! CHUA CO TELEGRAM_TOKEN. Tren cloud: vao Environment dat bien "
              "TELEGRAM_TOKEN. O may: dien vao file .env. Bot se khong doc/gui duoc.")

    print("=== BTC Signal Bot ===")
    print(f"Coin: {', '.join(config.SYMBOLS)}")
    print(f"Khung: {config.INTERVAL} | Quet moi: {config.LOOP_SECONDS}s | MIN_SCORE={config.MIN_SCORE}")
    print(f"So nguoi dung da nho: {len(subs)}")
    print("=" * 40)

    if once:
        scan_once(subs=subs, send=bool(subs))
        return

    start_health_server()   # cho cloud (Render) thay cong mo
    print("Bot dang chay. Vao Telegram go /start de bat dau (Ctrl+C de dung).")
    last_scan = 0.0
    while True:
        # 1) Lang nghe & tra loi lenh (lien tuc)
        poll_commands(subs)

        # 2) Quet thi truong dinh ky
        now = time.time()
        if now - last_scan >= config.LOOP_SECONDS:
            last_scan = now
            ts = config.now_vn().strftime("%H:%M:%S")
            print(f"\n[{ts}] Dang quet... ({len(subs)} nguoi dung)")
            try:
                scan_once(subs=subs, send=True)
            except Exception as e:
                print(f"[LOI VONG LAP] {e}")

        time.sleep(2)  # nghi ngan de khong quay CPU


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDa dung bot.")
