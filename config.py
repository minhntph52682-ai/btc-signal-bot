"""
Cau hinh cho bot tin hieu.
Co the sua truc tiep trong file nay, HOAC dat bien moi truong (environment variable) de ghi de.
LUU Y BAO MAT: Token bot la bi mat. Neu bi lo, vao @BotFather -> /revoke de tao token moi.
"""
import os

# ====== BI MAT (token, API key) ======
# Tat ca token / API key nam trong file .env (da bi .gitignore chan, khong len GitHub).
# Thu tu uu tien: bien moi truong that -> file .env -> file local_config.py (cu).
def _load_dotenv():
    env = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


_dotenv = _load_dotenv()

try:
    import local_config as _lc   # ho tro cach cu, khong bat buoc
except ImportError:
    _lc = None


def _secret(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    if name in _dotenv:
        return _dotenv[name]
    if _lc is not None and hasattr(_lc, name):
        return getattr(_lc, name)
    return default


TELEGRAM_TOKEN = _secret("TELEGRAM_TOKEN")

# ====== OKX API (de xem vi the / lenh dang mo) ======
# Tao API key READ-ONLY tren OKX roi dan vao local_config.py. Xem huong dan /lenh.
OKX_API_KEY = _secret("OKX_API_KEY")
OKX_API_SECRET = _secret("OKX_API_SECRET")
OKX_API_PASSPHRASE = _secret("OKX_API_PASSPHRASE")

# ID cua group/kenh nhan tin hieu.
# De trong roi chay:  py get_chat_id.py  de lay ID sau khi da add bot vao group.
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ====== DANH SACH COIN THEO DOI ======
# Ten cap giao dich theo chuan Binance (kt thuc bang USDT).
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
]

# Khung thoi gian nen: 1m,3m,5m,15m,30m,1h,2h,4h,6h,12h,1d ...
# 4h cho ti le thang cao & on dinh hon 1h (it nhieu hon). Doi "1d" de win cao hon nua.
INTERVAL = os.environ.get("INTERVAL", "4h")

# So giay giua moi lan quet (60 = 1 phut, 300 = 5 phut)
LOOP_SECONDS = int(os.environ.get("LOOP_SECONDS", "60"))

# ====== THAM SO CHIEN LUOC ======
EMA_FAST = 20        # EMA nhanh (xu huong ngan)
EMA_SLOW = 50        # EMA cham (xu huong dai)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
# Nguong DONG LUONG cho RSI: chi cong diem khi RSI du XA khoi 50.
#   LONG  can RSI > 50 + MARGIN  (mac dinh > 55)
#   SHORT can RSI < 50 - MARGIN  (mac dinh < 45)
# Tang MARGIN -> tin hieu chat hon. Vi du RSI=51 se KHONG con duoc tinh diem
# (tranh "4/4" gia tao khi RSI chi nhinh tren 50 mot chut).
RSI_MID = 50
RSI_MOMENTUM_MARGIN = 5
ATR_PERIOD = 14
ATR_SL_MULT = 2.0    # He so ATR de tinh cat lo (Stop Loss)
ATR_TP_MULT = 2.0    # He so ATR de tinh chot loi (Take Profit)

# Do manh toi thieu de bao tin hieu (so diem tren tong 4). >=3 la manh.
MIN_SCORE = 3

# So YEU TO toi thieu (tren 4) phai HOI TU cung huong thi moi coi la SETUP LENH
# thuc su (hien Entry / don bay / TP / SL). Thieu yeu to nao -> chi QUAN SAT.
#   4 = phai DU CA 4 yeu to (EMA, gia vs EMA, MACD, RSI) -> chat che nhat.
#   3 = cho phep thieu 1 yeu to.
SETUP_MIN_SCORE = 4

# ====== DON BAY (LEVERAGE) ======
# Bot goi y don bay dua tren do manh tin hieu + do bien dong (ATR).
# Bien dong cang cao -> don bay cang thap (de tranh chay tai khoan).
LEVERAGE_ENABLED = True
# Muc lo toi da chap nhan tren VON KY QUY khi dinh SL, tinh theo %.
# Vi du 30 nghia la: neu gia cham SL thi mat ~30% von cho lenh do.
RISK_PER_TRADE_PCT = 30
# % TONG VON chap nhan mat moi lenh (dung de tinh khoi luong vao lenh /von).
# 2-3% la muc quan ly von an toan pho bien. KHONG nen de qua 5%.
RISK_ACCOUNT_PCT = 3
# Tran don bay cho phep goi y (dung khi KHONG lay theo OKX).
MAX_LEVERAGE = 20
# Lay tran don bay theo dung muc san OKX cho phep tung coin (BTC x100, BNB x50...).
# Bat True de dung theo OKX. Luu y: OKX cho toi x100/x125 -> RAT RUI RO neu xai het.
USE_OKX_LEVERAGE = True

# Chi bao khi tin hieu THAY DOI so voi lan truoc.
#   True  = chi gui khi doi chieu (LONG<->SHORT), khong nhac lai tin hieu cu.
#   False = van nhac lai tin hieu cu (kem LONG/SHORT/SL/TP) moi RESEND_MINUTES phut.
ONLY_ON_CHANGE = False
# Khi ONLY_ON_CHANGE = False: gian cach nhac lai tin hieu cu (phut) de tranh spam.
RESEND_MINUTES = 30

# ====== GIA CHAY TRUC TIEP (/gia <coin>) ======
# So lan cap nhat va khoang cach giay giua moi lan (vd 40 lan x 3s = 2 phut).
LIVE_UPDATES = 40
LIVE_INTERVAL = 3

# ====== LOC DA KHUNG THOI GIAN (Multi-timeframe) ======
# Chi vao lenh khi khop ca xu huong KHUNG LON hon -> giam tin hieu nhieu,
# tang do tin cay. Vi du khung 1h thi khung lon = 1h x 4 = 4h.
MTF_CONFIRM = True
MTF_FACTOR = 4   # khung lon = khung hien tai x MTF_FACTOR

# Chi vao lenh khi 2 EMA tach nhau it nhat X% (loc bo vung di ngang gay thua).
# Tang len -> it lenh hon nhung chat luong hon. 0 = tat loc.
MIN_TREND_PCT = 0.6

# ====== NGUON GIA ======
# Lay gia theo web OKX. "SWAP" = gia hop dong vinh cuu (futures, co don bay);
# "SPOT" = gia mua ban giao ngay. Bot dung don bay nen mac dinh SWAP.
OKX_PRICE_TYPE = "SWAP"
