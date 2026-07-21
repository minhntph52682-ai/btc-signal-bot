"""
Kiem tra chien luoc tren du lieu LICH SU (backtest).

Muc dich: cho biet TI LE THANG THAT SU cua tin hieu la bao nhieu %,
thay vi tin vao con so "100%" ao. Day moi la "do chuan" co that.

Cach chay:
  py backtest.py            -> backtest tat ca coin
  py backtest.py BTCUSDT    -> backtest 1 coin
"""
import sys

import config
import market
import strategy
import okx


def _history(symbol, interval, limit):
    """Lay nhieu nen lich su: uu tien OKX phan trang, loi thi Binance."""
    try:
        c = okx.get_klines_history(symbol, interval, total=limit)
        if len(c) >= 100:
            return c
    except Exception:
        pass
    return market.get_klines(symbol, interval, limit=limit)


def backtest(symbol, interval=None, limit=1000):
    """
    Mo phong: moi khi co tin hieu manh, vao lenh tai gia dong cua,
    roi xem gia cham TP truoc hay SL truoc -> thang / thua.
    Tra ve dict thong ke.
    """
    interval = interval or config.INTERVAL
    candles = _history(symbol, interval, limit)
    n = len(candles)
    warmup = config.EMA_SLOW + 5

    wins = losses = open_trades = 0
    i = warmup
    while i < n - 1:
        res = strategy.analyze(symbol, candles[: i + 1])
        # Chi vao lenh khi la SETUP thuc su (du yeu to) - dung luat nhu live.
        if res is None or not res.get("actionable") or res["sl"] is None:
            i += 1
            continue

        side = res["side"]
        tp = res["tp"]
        sl = res["sl"]
        result = None
        j = i + 1
        while j < n:
            hi = candles[j]["high"]
            lo = candles[j]["low"]
            if side == "LONG":
                # Neu trong cung 1 nen cham ca 2 -> coi nhu THUA (than trong)
                if lo <= sl:
                    result = "loss"
                    break
                if hi >= tp:
                    result = "win"
                    break
            else:  # SHORT
                if hi >= sl:
                    result = "loss"
                    break
                if lo <= tp:
                    result = "win"
                    break
            j += 1

        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1
        else:
            open_trades += 1  # chua dong den cuoi du lieu

        # Nhay den sau khi lenh dong de tranh trung lap
        i = (j + 1) if result else (i + 1)

    total = wins + losses
    win_rate = (wins / total * 100) if total else 0.0
    rr = config.ATR_TP_MULT / config.ATR_SL_MULT  

    breakeven = 100 / (1 + rr)

    return {
        "symbol": symbol,
        "interval": interval,
        "candles": n,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "open": open_trades,
        "win_rate": win_rate,
        "rr": rr,
        "breakeven": breakeven,
        "profitable": win_rate > breakeven,
    }


def format_report(st):
    """Tao bao cao ngan gon (dung cho ca console va Telegram khong dinh dang)."""
    if st["trades"] == 0:
        return (
            f"{st['symbol']} ({st['interval']}): chua du tin hieu de backtest "
            f"tren {st['candles']} nen."
        )
    verdict = "CO LOI (win-rate > diem hoa von)" if st["profitable"] else "CHUA CO LOI"
    return (
        f"{st['symbol']} ({st['interval']}) - backtest {st['candles']} nen:\n"
        f"  So lenh: {st['trades']}  |  Thang: {st['wins']}  Thua: {st['losses']}\n"
        f"  TI LE THANG: {st['win_rate']:.1f}%\n"
        f"  Ti le Loi/Lo (RR): 1:{st['rr']:.1f}  -> can thang > {st['breakeven']:.1f}% moi hoa von\n"
        f"  Ket luan: {verdict}"
    )


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    symbols = [args[0].upper()] if args else config.SYMBOLS
    print(f"Backtest tren khung {config.INTERVAL} (SETUP_MIN_SCORE={config.SETUP_MIN_SCORE}/4)...\n")
    for sym in symbols:
        try:
            st = backtest(sym)
            print(format_report(st))
            print()
        except Exception as e:
            print(f"{sym}: loi backtest - {e}\n")


if __name__ == "__main__":
    main()
