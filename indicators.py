"""Cac chi bao ky thuat, viet bang Python thuan (khong can numpy/pandas)."""


def ema(values, period):
    """Duong trung binh dong ham mu (EMA). Tra ve list cung do dai voi values."""
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes, period=14):
    """Chi so suc manh tuong doi (RSI) theo phuong phap Wilder. Tra ve list (dau bang None)."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsis = [None] * period

    def _rsi(ag, al):
        if al == 0:
            return 100.0
        rs = ag / al
        return 100 - (100 / (1 + rs))

    rsis.append(_rsi(avg_gain, avg_loss))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsis.append(_rsi(avg_gain, avg_loss))
    return rsis


def macd(closes, fast=12, slow=26, signal=9):
    """Tra ve (macd_line, signal_line, histogram) - moi cai la list."""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, hist


def atr(candles, period=14):
    """Average True Range - do bien dong, dung de dat SL/TP. Tra ve list."""
    if len(candles) < 2:
        return [None] * len(candles)
    trs = [candles[0]["high"] - candles[0]["low"]]
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return ema(trs, period)  # dung EMA cho muot; du chinh xac cho muc dich SL/TP
