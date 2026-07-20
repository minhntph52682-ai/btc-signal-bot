"""
Chien luoc quyet dinh LONG / SHORT.

Tong hop nhieu chi bao ky thuat thanh 1 diem so (score) tu -4 den +4:
  - score > 0  -> thien ve LONG  (mua)
  - score < 0  -> thien ve SHORT (ban)
  - score = 0  -> trung lap (khong ro xu huong)

4 tin hieu (moi cai +1 cho LONG hoac -1 cho SHORT):
  1) Xu huong EMA:  EMA nhanh > EMA cham -> LONG,  nguoc lai -> SHORT
  2) Gia vs EMA cham: gia dong cua tren EMA cham -> LONG, duoi -> SHORT
  3) MACD: histogram > 0 -> LONG, < 0 -> SHORT
  4) RSI: RSI < oversold -> LONG (qua ban, cho hoi phuc)
          RSI > overbought -> SHORT (qua mua, cho dieu chinh)
          (vung giua khong tinh diem)

Ket qua tra ve gom: huong (LONG/SHORT/NEUTRAL), diem, SL, TP va ly do.
"""
import config
import okx
from indicators import ema, rsi, macd, atr

# Cac muc don bay "dep" de lam tron goi y (thay vi x7.3 thi bao x5).
_LEV_STEPS = [1, 2, 3, 5, 10, 15, 20, 25, 50, 75, 100, 125]


def _leverage_cap(symbol):
    """Tran don bay: uu tien lay theo OKX; neu khong co thi dung config.MAX_LEVERAGE."""
    cap = config.MAX_LEVERAGE
    if getattr(config, "USE_OKX_LEVERAGE", False):
        okx_max = okx.get_max_leverage(symbol, default=None)
        if okx_max:
            cap = okx_max
    return cap


def _round_leverage(lev, cap):
    """Lam tron don bay xuong muc dep gan nhat, khong vuot 'cap'."""
    lev = min(lev, cap)
    best = 1
    for step in _LEV_STEPS:
        if step <= lev and step <= cap:
            best = step
    return best


def suggest_leverage(price, sl, strength, symbol):
    """
    Goi y don bay dua tren:
      - Khoang cach den SL (bien dong): SL cang xa -> don bay cang thap.
      - Do manh tin hieu (strength 1..4): manh hon -> tu tin hon.
    Cong thuc: don bay sao cho khi cham SL chi mat ~RISK_PER_TRADE_PCT von.
    Tran don bay lay theo muc OKX cho phep voi coin do.
    Tra ve (don_bay_goi_y, tran_okx).
    """
    cap = _leverage_cap(symbol)
    if not config.LEVERAGE_ENABLED or sl is None or price <= 0:
        return None, cap
    sl_dist_pct = abs(price - sl) / price * 100
    if sl_dist_pct <= 0:
        return None, cap
    # Don bay co so: cham SL mat dung RISK_PER_TRADE_PCT von ky quy.
    raw = config.RISK_PER_TRADE_PCT / sl_dist_pct
    # Nhan he so tu tin theo do manh (2/4=0.5 ... 4/4=1.0).
    raw *= strength / 4.0
    return _round_leverage(raw, cap), cap


def _htf_trend(closes, factor):
    """
    Xu huong khung lon hon: gom nen theo he so 'factor' (tinh tu cuoi len),
    roi so EMA nhanh vs EMA cham. Tra ve +1 (tang), -1 (giam), 0 (khong ro).
    """
    coarse = [closes[k] for k in range(len(closes) - 1, -1, -factor)][::-1]
    if len(coarse) < config.EMA_SLOW + 2:
        return 0
    ef = ema(coarse, config.EMA_FAST)[-1]
    es = ema(coarse, config.EMA_SLOW)[-1]
    if ef > es:
        return 1
    if ef < es:
        return -1
    return 0


def position_size(account, entry, sl, leverage, risk_pct=None):
    """
    Tinh khoi luong vao lenh theo quan ly von.
    - account: tong von (USDT)
    - entry, sl: gia vao va cat lo
    - leverage: don bay dung
    - risk_pct: % tong von chap nhan mat neu cham SL (mac dinh config.RISK_ACCOUNT_PCT)

    Tra ve dict: risk_amount, notional (gia tri lenh), margin (tien ky quy bo vao),
                 qty (so coin), sl_dist_pct.
    """
    if risk_pct is None:
        risk_pct = config.RISK_ACCOUNT_PCT
    if not entry or not sl or entry <= 0 or leverage <= 0:
        return None
    sl_dist = abs(entry - sl) / entry           # ti le khoang cach den SL
    if sl_dist <= 0:
        return None
    risk_amount = account * risk_pct / 100.0    # so tien chap nhan mat
    notional = risk_amount / sl_dist            # gia tri lenh (position size)
    margin = notional / leverage                # tien ky quy phai bo vao
    # Khong cho margin vuot qua tong von
    if margin > account:
        margin = account
        notional = margin * leverage
    qty = notional / entry
    return {
        "risk_amount": risk_amount,
        "notional": notional,
        "margin": margin,
        "qty": qty,
        "sl_dist_pct": sl_dist * 100,
    }


def analyze(symbol, candles):
    """Phan tich 1 coin. Tra ve dict ket qua, hoac None neu thieu du lieu."""
    closes = [c["close"] for c in candles]
    if len(closes) < config.EMA_SLOW + 5:
        return None

    ema_fast = ema(closes, config.EMA_FAST)
    ema_slow = ema(closes, config.EMA_SLOW)
    rsi_vals = rsi(closes, config.RSI_PERIOD)
    _, _, hist = macd(closes)
    atr_vals = atr(candles, config.ATR_PERIOD)

    price = closes[-1]
    ef = ema_fast[-1]
    es = ema_slow[-1]
    r = rsi_vals[-1]
    h = hist[-1]
    a = atr_vals[-1]

    score = 0
    reasons = []

    # 1) Xu huong EMA
    if ef > es:
        score += 1
        reasons.append(f"EMA{config.EMA_FAST} > EMA{config.EMA_SLOW} (xu huong tang)")
    elif ef < es:
        score -= 1
        reasons.append(f"EMA{config.EMA_FAST} < EMA{config.EMA_SLOW} (xu huong giam)")

    # 2) Gia so voi EMA cham
    if price > es:
        score += 1
        reasons.append(f"Gia tren EMA{config.EMA_SLOW}")
    elif price < es:
        score -= 1
        reasons.append(f"Gia duoi EMA{config.EMA_SLOW}")

    # 3) MACD histogram
    if h is not None:
        if h > 0:
            score += 1
            reasons.append("MACD histogram > 0 (dong luong tang)")
        elif h < 0:
            score -= 1
            reasons.append("MACD histogram < 0 (dong luong giam)")

    # 4) RSI theo DONG LUONG (thuan xu huong, khong danh nguoc):
    #    RSI > 50 -> ung ho LONG ; RSI < 50 -> ung ho SHORT.
    #    Tranh vao lenh khi da qua mua/qua ban (de bi dao chieu).
    if r is not None:
        long_min = config.RSI_MID + config.RSI_MOMENTUM_MARGIN   # vd 55
        short_max = config.RSI_MID - config.RSI_MOMENTUM_MARGIN   # vd 45
        if r > long_min and r < config.RSI_OVERBOUGHT:
            score += 1
            reasons.append(f"RSI={r:.0f} > {long_min:.0f} (dong luong tang)")
        elif r < short_max and r > config.RSI_OVERSOLD:
            score -= 1
            reasons.append(f"RSI={r:.0f} < {short_max:.0f} (dong luong giam)")
        elif r >= config.RSI_OVERBOUGHT:
            reasons.append(f"RSI={r:.0f} qua mua - than trong")
        elif r <= config.RSI_OVERSOLD:
            reasons.append(f"RSI={r:.0f} qua ban - than trong")
        else:
            reasons.append(f"RSI={r:.0f} quanh 50 (dong luong yeu, khong tinh diem)")

    # Xac dinh huong. 'lean' = huong nghieng theo diem (luon co khi diem != 0),
    # dung khi nguoi dung HOI THANG 1 coin. 'side' = tin hieu du manh de tu dong bao.
    if score > 0:
        lean = "LONG"
    elif score < 0:
        lean = "SHORT"
    else:
        lean = "NEUTRAL"
    side = lean

    # LOC TREND MANH: chi vao lenh khi 2 EMA tach nhau du xa (co xu huong ro),
    # tranh vung di ngang (choppy) - noi gay thua nhieu nhat.
    if side != "NEUTRAL" and config.MIN_TREND_PCT > 0:
        sep_pct = abs(ef - es) / price * 100
        if sep_pct < config.MIN_TREND_PCT:
            side = "NEUTRAL"
            reasons.append(f"Bo qua: 2 EMA qua sat ({sep_pct:.2f}%<{config.MIN_TREND_PCT}%), thi truong di ngang")

    # LOC DA KHUNG: chi giu tin hieu khi khop xu huong khung lon hon
    htf = 0
    if config.MTF_CONFIRM and side != "NEUTRAL":
        htf = _htf_trend(closes, config.MTF_FACTOR)
        if htf == 1 and side == "SHORT":
            side = "NEUTRAL"
            reasons.append(f"Bo qua: khung lon dang TANG, khong SHORT nguoc trend")
        elif htf == -1 and side == "LONG":
            side = "NEUTRAL"
            reasons.append(f"Bo qua: khung lon dang GIAM, khong LONG nguoc trend")
        elif htf != 0:
            reasons.append(f"Khop xu huong khung lon ({'TANG' if htf > 0 else 'GIAM'})")

    # Tinh SL/TP theo ATR - tinh theo 'lean' (huong nghieng) de luon co so
    # khi nguoi dung hoi thang 1 coin.
    sl = tp = None
    if a is not None and lean != "NEUTRAL":
        if lean == "LONG":
            sl = price - a * config.ATR_SL_MULT
            tp = price + a * config.ATR_TP_MULT
        else:  # SHORT
            sl = price + a * config.ATR_SL_MULT
            tp = price - a * config.ATR_TP_MULT

    leverage, lev_cap = suggest_leverage(price, sl, abs(score), symbol)

    # SETUP LENH thuc su: phai co huong (qua bo loc trend/da khung) VA hoi tu
    # du so yeu to (SETUP_MIN_SCORE). Thieu yeu to -> chi QUAN SAT, khong vao lenh.
    actionable = side in ("LONG", "SHORT") and abs(score) >= config.SETUP_MIN_SCORE

    return {
        "symbol": symbol,
        "price": price,
        "side": side,          # tin hieu du manh (da qua bo loc) - dung cho tu dong bao
        "lean": lean,          # huong nghieng theo diem - dung khi hoi thang 1 coin
        "actionable": actionable,
        "score": score,
        "strength": abs(score),   # 0..4
        "rsi": r,
        "ema_fast": ef,
        "ema_slow": es,
        "atr": a,
        "sl": sl,
        "tp": tp,
        "leverage": leverage,
        "leverage_max": lev_cap,   # tran don bay OKX cho coin nay
        "reasons": reasons,
    }
