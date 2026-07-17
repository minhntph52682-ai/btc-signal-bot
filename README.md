# BTC Signal Bot

Bot Telegram bao gia BTC (va cac coin khac) + goi y **LONG / SHORT** dua tren
phan tich ky thuat tu du lieu gia Binance (public API, khong can API key).

## Cach hoat dong

1. Lay nen (candlestick) tu Binance cho cac coin trong `config.SYMBOLS`.
2. Tinh cac chi bao: **EMA 20/50, RSI 14, MACD, ATR**.
3. Cham diem tu -4 (SHORT manh) den +4 (LONG manh) — xem `strategy.py`.
4. Neu do manh >= `MIN_SCORE`, gui tin hieu ve Telegram kem
   **gia, huong LONG/SHORT, don bay goi y, TP, SL, ly do**.

## Don bay (leverage) duoc tinh nhu the nao?

Bot KHONG phang x100 bua. Don bay goi y = *rui ro co kiem soat*:

- SL duoc dat theo **ATR** (do bien dong). Bien dong lon -> SL xa -> don bay thap.
- Cong thuc: don bay sao cho neu gia cham SL thi chi mat khoang
  `RISK_PER_TRADE_PCT`% von ky quy (mac dinh 30%).
- Nhan them he so theo do manh tin hieu (3/4 hay 4/4 moi duoc don bay cao).
- Tran don bay lay **theo dung muc OKX cho phep** tung coin
  (BTC/ETH/SOL x100, BNB/DOGE x50...) khi `USE_OKX_LEVERAGE = True`.
  Neu tat, dung `MAX_LEVERAGE` co dinh (mac dinh **x20**).

Tin nhan hien ca hai: <b>don bay goi y</b> va <b>tran OKX toi da</b>.

> **Canh bao:** OKX cho toi x100/x125. Xai het tran = gia dao ~1% la chay tai
> khoan. Bot goi y muc THAP hon nhieu (theo rui ro) — do la co y, khong phai loi.

Luon dung **che do co lap (isolated)** de 1 lenh thua khong keo sap ca vi.

## Cai dat

Chi can **Python 3.8+**, khong can thu vien ngoai (dung urllib co san).

```
py --version
```

## Chay lan dau (rat don gian)

Bot **tu dong nhan dien chat ID** — KHONG can dat CHAT_ID thu cong.

### 1. Chay bot
```
py bot.py
```

### 2. Vao Telegram, nhan Start voi bot roi go /start
Bot se tu nho chat cua ban (luu vao `subscribers.json`) va tra loi ngay.

### Cac lenh trong Telegram
| Lenh | Y nghia |
|------|---------|
| `/start` | Man hinh chao + huong dan |
| `/gia btc` | Gia CHAY TRUC TIEP lien tuc, khong dung (chay nhieu coin cung luc) |
| `/dunggia` | Dung gia truc tiep (`/dunggia btc` = dung 1 coin) |
| `/tinhieu btc` | Phan tich LONG/SHORT + don bay + TP/SL (BAT KY coin nao) |
| `/tinhieu` | Phan tich tat ca coin dang theo doi |
| `/kiemtra btc` | Ti le thang lich su that (backtest) |
| `/von 350` | Tinh khoi luong / ky quy vao lenh theo tong von |
| `/them doge` | Them coin vao danh sach tu dong theo doi |
| `/xoa doge` | Bo coin khoi danh sach |
| `/list` | Coin dang theo doi |
| `/help` | Huong dan |

> Xem coin bat ky ma khong can them vao danh sach: chi can `/tinhieu xrp`,
> `/gia doge`... Danh sach theo doi (`/them`, `/xoa`) chi anh huong den viec bot
> TU DONG quet & gui tin hieu.

Ngoai ra bot **tu dong** gui tin hieu manh (>= `MIN_SCORE`) cho tat ca
nguoi da tung nhan tin, moi `LOOP_SECONDS` giay.

> **Quan trong:** bot chay tren MAY CUA BAN. Phai giu `py bot.py` dang chay
> thi bot moi tra loi. Tat cua so / tat may -> bot ngung.

### Test nhanh 1 lan (khong lang nghe lenh)
```
py bot.py --once
```

## Cau hinh (config.py)

| Bien | Y nghia | Mac dinh |
|------|---------|----------|
| `SYMBOLS` | Danh sach coin theo doi | BTC, ETH, SOL, BNB |
| `INTERVAL` | Khung nen (4h cho win-rate cao & on dinh; 1d con cao hon) | `4h` |
| `MIN_TREND_PCT` | Loc vung di ngang (2 EMA phai tach >X%) | `0.6` |
| `LOOP_SECONDS` | Chu ky quet (giay) | `300` (5 phut) |
| `MIN_SCORE` | Do manh toi thieu de bao (0..4) | `3` |
| `ONLY_ON_CHANGE` | `True`=chi bao khi doi chieu; `False`=nhac lai ca tin hieu cu | `False` |
| `RESEND_MINUTES` | Gian cach nhac lai tin hieu cu (khi ONLY_ON_CHANGE=False) | `30` |
| `ATR_SL_MULT` / `ATR_TP_MULT` | He so tinh SL / TP | `2.0` / `2.0` |
| `LEVERAGE_ENABLED` | Bat/tat goi y don bay | `True` |
| `RISK_PER_TRADE_PCT` | % von chap nhan mat khi cham SL | `30` |
| `MAX_LEVERAGE` | Tran don bay goi y | `20` |

## Bao mat

Token bot la bi mat. Nen dat qua bien moi truong thay vi ghi thang vao file:

```powershell
$env:TELEGRAM_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
py bot.py
```

Neu lo token: vao `@BotFather` -> `/revoke` de tao token moi.

## Luu y

Tin hieu **chi mang tinh tham khao**, khong phai loi khuyen dau tu.
Thi truong crypto rui ro cao — luon tu quan ly von va dat SL.
