"""
Xu ly cac lenh nguoi dung gui cho bot (/start, /gia, /tinhieu, /help...).
Moi ham tra ve chuoi HTML de gui lai cho dung nguoi da nhan.
"""
import config
import market
import strategy
import watchlist
import backtest
import okx_private


def _norm_symbol(text):
    """Chuyen 'btc' -> 'BTCUSDT', 'ethusdt' -> 'ETHUSDT'."""
    s = text.strip().upper()
    if not s.endswith("USDT"):
        s += "USDT"
    return s


def _fmt_price(p):
    if p is None:
        return "-"
    if p >= 100:
        return f"{p:,.2f}"
    if p >= 1:
        return f"{p:,.4f}"
    return f"{p:.6f}"


def cmd_start():
    coins = ", ".join(s.replace("USDT", "") for s in watchlist.get())
    return (
        "\U0001F44B <b>Chao mung den Bot tin hieu Crypto!</b>\n\n"
        "Bot bao gia va goi y <b>LONG / SHORT</b> + don bay dua tren phan tich ky thuat.\n\n"
        "<b>Cac lenh:</b>\n"
        "/p <code>btc</code> — gia CHAY TRUC TIEP lien tuc (khong dung)\n"
        "/dunggia — dung gia truc tiep\n"
        "/p — gia tat ca coin (1 lan)\n"
        "/tinhieu <code>btc</code> — phan tich 1 coin (LONG/SHORT, don bay, TP, SL)\n"
        "/tinhieu — phan tich TAT CA coin dang theo doi\n"
        "/them <code>doge</code> — them coin vao danh sach theo doi\n"
        "/xoa <code>doge</code> — bo coin khoi danh sach\n"
        "/von <code>350</code> — tinh khoi luong vao lenh theo von\n"
        "/kiemtra <code>btc</code> — ti le thang lich su\n"
        "/lenh — xem lenh dang mo tren OKX\n"
        "/list — danh sach coin theo doi\n"
        "/dung — tat tin hieu tu dong cho noi nay\n"
        "/help — xem huong dan\n\n"
        f"<i>Dang theo doi:</i> {coins}\n"
        f"<i>Khung thoi gian:</i> {config.INTERVAL}\n\n"
        "Ban co the xem BAT KY coin nao: <code>/tinhieu xrp</code>, <code>/gia doge</code>...\n"
        "\U0001F465 <b>Dung trong NHOM:</b> add bot vao nhom roi go <code>/start</code> "
        "ngay trong nhom — bot se tu dong gui tin hieu vao nhom do.\n"
        "Bot cung se <b>tu dong gui tin hieu</b> khi co co hoi manh.\n"
        "<i>Chi mang tinh tham khao, khong phai loi khuyen dau tu.</i>"
    )


def cmd_help():
    return (
        "\U0001F4D6 <b>Huong dan</b>\n\n"
        "/p <code>btc</code> — gia chay truc tiep lien tuc (khong dung)\n"
        "/dunggia [<code>btc</code>] — dung gia truc tiep (1 coin hoac tat ca)\n"
        "/p — gia tat ca coin (1 lan)\n"
        "/tinhieu <code>sol</code> — phan tich chi tiet 1 coin\n"
        "/tinhieu — phan tich tat ca coin\n"
        "/kiemtra <code>btc</code> — ti le thang lich su (do chuan that)\n"
        "/lenh — xem lenh dang mo tren OKX\n"
        "/von <code>350</code> — tinh khoi luong vao lenh theo von\n"
        "/them <code>doge</code> — them coin theo doi\n"
        "/xoa <code>doge</code> — bo coin theo doi\n"
        "/list — coin dang theo doi\n"
        "/start — man hinh chao\n\n"
        "Vi du: <code>/tinhieu btc</code> , <code>/gia eth</code> , <code>/them xrp</code>"
    )


def cmd_list():
    lines = ["\U0001F4CB <b>Coin dang theo doi:</b>"]
    for s in watchlist.get():
        lines.append(f"  • {s}")
    lines.append(f"\nKhung: {config.INTERVAL} | Quet moi {config.LOOP_SECONDS}s")
    return "\n".join(lines)


def cmd_them(arg):
    if not arg:
        return "Cu phap: <code>/them doge</code>"
    sym, existed = watchlist.add(arg)
    if existed:
        return f"<b>{sym}</b> da co trong danh sach roi."
    return f"✅ Da them <b>{sym}</b> vao danh sach theo doi."


def cmd_xoa(arg):
    if not arg:
        return "Cu phap: <code>/xoa doge</code>"
    sym, removed = watchlist.remove(arg)
    if removed:
        return f"\U0001F5D1 Da xoa <b>{sym}</b> khoi danh sach."
    return f"<b>{sym}</b> khong co trong danh sach."


def cmd_gia(arg):
    """Gia hien tai. arg=None -> tat ca coin."""
    symbols = [_norm_symbol(arg)] if arg else watchlist.get()
    lines = ["\U0001F4B0 <b>Gia hien tai</b>"]
    for sym in symbols:
        try:
            p = market.get_price(sym)
            lines.append(f"  <b>{sym.replace('USDT','')}</b>: {_fmt_price(p)} USDT")
        except Exception:
            lines.append(f"  {sym}: khong lay duoc gia")
    return "\n".join(lines)


def cmd_von(args):
    """
    Tinh khoi luong vao lenh theo von. Cu phap:
      /von 350          -> tinh cho tat ca coin dang co tin hieu
      /von 350 sol      -> tinh cho 1 coin
    """
    if not args:
        return (
            "Cu phap: <code>/von 350</code> hoac <code>/von 350 sol</code>\n"
            "So la tong von (USDT)."
        )
    parts = args.split()
    try:
        account = float(parts[0].replace(",", "").replace("$", ""))
    except ValueError:
        return "Von khong hop le. Vi du: <code>/von 350</code>"
    if account <= 0:
        return "Von phai lon hon 0."

    coin = parts[1] if len(parts) > 1 else None
    symbols = [_norm_symbol(coin)] if coin else watchlist.get()

    lines = [
        f"\U0001F4B5 <b>Vao lenh voi von {account:,.0f} USDT</b>",
        f"<i>Rui ro moi lenh: {config.RISK_ACCOUNT_PCT}% von "
        f"(~{account * config.RISK_ACCOUNT_PCT / 100:,.1f} USDT neu cham SL)</i>\n",
    ]
    found = False
    for sym in symbols:
        try:
            candles = market.get_klines(sym, config.INTERVAL, limit=200)
            res = strategy.analyze(sym, candles)
        except Exception:
            continue
        if res is None:
            continue
        # Hoi thang 1 coin -> dung huong nghieng (lean, luon co).
        # Tinh cho tat ca -> chi coin co tin hieu du manh.
        direction = res.get("lean") if coin else res["side"]
        if direction == "NEUTRAL" or not res.get("leverage"):
            continue
        if not coin and res["strength"] < config.MIN_SCORE:
            continue
        ps = strategy.position_size(account, res["price"], res["sl"], res["leverage"])
        if not ps:
            continue
        found = True
        weak = "  ⚠️ <i>tin hieu yeu</i>\n" if not res.get("actionable") else ""
        lines.append(
            f"<b>{sym.replace('USDT','')}</b> — {direction} x{res['leverage']}\n"
            f"{weak}"
            f"  • Ky quy bo vao (margin): <b>{ps['margin']:,.1f} USDT</b>\n"
            f"  • Gia tri lenh (volume): <b>{ps['notional']:,.0f} USDT</b>\n"
            f"  • So luong: ~{ps['qty']:.4f} {sym.replace('USDT','')}\n"
            f"  • Vao ~{_fmt_price(res['price'])} | SL {_fmt_price(res['sl'])} "
            f"| TP {_fmt_price(res['tp'])}"
        )
    if not found:
        if coin:
            lines.append("Coin nay hien di ngang, chua ro huong de vao lenh.")
        else:
            lines.append("Hien khong co coin nao co tin hieu du manh de vao lenh.")
    lines.append("\n<i>Chi tham khao. Luon dat SL. Khong bao gio all-in.</i>")
    return "\n".join(lines)


def _huong_dan_okx_key():
    return (
        "\U0001F511 <b>Chua cau hinh OKX API key</b>\n\n"
        "De xem lenh dang mo, ban can tao API key (CHI DOC) tren OKX:\n\n"
        "1. Vao OKX -> bam avatar -> <b>API</b> (hoac Settings -> API keys)\n"
        "2. Bam <b>Create API key</b>\n"
        "3. Dat <b>Passphrase</b> (tu chon, nho ky)\n"
        "4. Quyen (Permissions): CHI chon <b>Read</b> (Doc). "
        "<b>KHONG</b> bat Trade/Withdraw cho an toan.\n"
        "5. Tao xong, copy: <b>API Key</b>, <b>Secret Key</b>, <b>Passphrase</b>\n"
        "6. Dan vao file <code>local_config.py</code> tren may:\n"
        "<code>OKX_API_KEY = \"...\"\n"
        "OKX_API_SECRET = \"...\"\n"
        "OKX_API_PASSPHRASE = \"...\"</code>\n"
        "7. Khoi dong lai bot roi go /lenh lai.\n\n"
        "<i>Key chi doc: du lo cung khong ai giao dich/rut tien duoc.</i>"
    )


def cmd_lenh():
    """Xem cac vi the / lenh dang mo tren OKX."""
    if not okx_private.has_keys():
        return _huong_dan_okx_key()
    try:
        positions = okx_private.get_positions()
    except Exception as e:
        return f"Khong lay duoc vi the OKX:\n{e}"
    if not positions:
        return "\U0001F4C2 Hien khong co lenh nao dang mo tren OKX."

    lines = ["\U0001F4C2 <b>Cac lenh dang mo tren OKX</b>\n"]
    total_upl = 0.0
    for p in positions:
        inst = p.get("instId", "")
        name = inst.split("-")[0]
        pos = float(p.get("pos") or 0)
        side = p.get("posSide")
        if side not in ("long", "short"):
            side = "long" if pos > 0 else "short"
        side_txt = "\U0001F7E2 LONG" if side == "long" else "\U0001F534 SHORT"
        entry = float(p.get("avgPx") or 0)
        mark = float(p.get("markPx") or 0)
        upl = float(p.get("upl") or 0)
        upl_ratio = float(p.get("uplRatio") or 0) * 100
        lever = p.get("lever") or "-"
        try:
            liq = _fmt_price(float(p.get("liqPx")))
        except (TypeError, ValueError):
            liq = "-"
        total_upl += upl
        pnl_icon = "\U0001F4C8" if upl >= 0 else "\U0001F4C9"
        lines.append(
            f"{side_txt} <b>{name}</b> x{lever}\n"
            f"  • Entry: {_fmt_price(entry)} | Mark: {_fmt_price(mark)}\n"
            f"  • {pnl_icon} Lai/Lo: <b>{upl:+.2f} USDT</b> ({upl_ratio:+.1f}%)\n"
            f"  • Gia thanh ly (liq): {liq}"
        )
    lines.append(f"\n\U0001F4B0 <b>Tong lai/lo tam tinh: {total_upl:+.2f} USDT</b>")
    return "\n".join(lines)


def cmd_kiemtra(arg):
    """Backtest: ti le thang lich su that su cua chien luoc."""
    symbols = [_norm_symbol(arg)] if arg else watchlist.get()
    lines = ["\U0001F9EA <b>Kiem tra lich su (backtest)</b>"]
    lines.append(f"<i>Khung {config.INTERVAL}, {config.MIN_SCORE}/4 diem tro len:</i>\n")
    for sym in symbols:
        try:
            st = backtest.backtest(sym)
        except Exception as e:
            lines.append(f"<b>{sym}</b>: loi ({e})")
            continue
        if st["trades"] == 0:
            lines.append(f"<b>{sym}</b>: chua du tin hieu de danh gia")
            continue
        icon = "✅" if st["profitable"] else "⚠️"
        lines.append(
            f"{icon} <b>{sym}</b>: thang <b>{st['win_rate']:.0f}%</b> "
            f"({st['wins']}/{st['trades']} lenh), can >{st['breakeven']:.0f}% de hoa von"
        )
    lines.append(
        "\n<i>Day la ti le THAT tren du lieu qua khu — khong dam bao tuong lai. "
        "Khong co he thong nao dung 100%.</i>"
    )
    return "\n".join(lines)


def cmd_tinhieu(arg, format_signal):
    """
    Phan tich. arg co coin -> hien chi tiet 1 coin (ke ca chua co tin hieu).
    arg trong -> chi hien CHI TIET coin co tin hieu LONG/SHORT; coin chua co
    tin hieu gom lai 1 dong ngan cho gon.
    """
    # Yeu cau 1 coin cu the -> LUON hien huong (long/short), du manh hay yeu
    if arg:
        sym = _norm_symbol(arg)
        try:
            candles = market.get_klines(sym, config.INTERVAL, limit=200)
            res = strategy.analyze(sym, candles)
        except Exception as e:
            return f"<b>{sym}</b>: loi lay du lieu ({e})"
        if res is None:
            return f"<b>{sym}</b>: chua du du lieu"
        return format_signal(res, on_demand=True)

    # Tat ca coin -> hien huong (long/short) cua TUNG coin, giong khi hoi rieng.
    # Coin manh xep truoc, coin yeu/di ngang xep sau.
    strong, weak = [], []
    for sym in watchlist.get():
        try:
            candles = market.get_klines(sym, config.INTERVAL, limit=200)
            res = strategy.analyze(sym, candles)
        except Exception:
            continue
        if res is None:
            continue
        block = format_signal(res, on_demand=True)
        if res.get("actionable"):
            strong.append(block)
        else:
            weak.append(block)

    blocks = strong + weak
    if not blocks:
        return "Chua lay duoc du lieu coin nao."
    return "\n\n———\n\n".join(blocks)


def handle(text, format_signal):
    """
    Nhan text tin nhan, tra ve chuoi tra loi (HTML) hoac None neu khong phai lenh.
    """
    text = (text or "").strip()
    if not text.startswith("/"):
        return None

    parts = text.split()
    cmd = parts[0][1:].lower()
    cmd = cmd.split("@")[0]          # bo @tenbot neu co (trong group)
    arg = parts[1] if len(parts) > 1 else None

    if cmd in ("start",):
        return cmd_start()
    if cmd in ("help", "huongdan"):
        return cmd_help()
    if cmd in ("list", "coin", "danhsach"):
        return cmd_list()
    if cmd in ("them", "add", "theodoi"):
        return cmd_them(arg)
    if cmd in ("xoa", "remove", "bo", "del"):
        return cmd_xoa(arg)
    if cmd in ("gia", "price", "p"):
        return cmd_gia(arg)
    if cmd in ("tinhieu", "signal", "s"):
        return cmd_tinhieu(arg, format_signal)
    if cmd in ("kiemtra", "backtest", "bt", "dochuan"):
        return cmd_kiemtra(arg)
    if cmd in ("lenh", "vithe", "positions", "pos"):
        return cmd_lenh()
    if cmd in ("von", "von", "size", "khoiluong"):
        # /von can ca phan sau lenh (co the co 2 tham so: so tien + coin)
        return cmd_von(text.split(None, 1)[1] if len(text.split(None, 1)) > 1 else "")

    # Lenh khong biet
    return (
        f"Khong hieu lenh <code>/{cmd}</code>.\n"
        "Go /help de xem cac lenh co san."
    )
