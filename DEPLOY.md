# Huong dan chay bot 24/7 tren Cloud mien phi

Bot can chay 1 tien trinh lien tuc. Duoi day la 2 cach mien phi on dinh nhat.
**Truoc khi bat dau:** vao @BotFather -> /revoke -> tao token moi, roi dat token
qua bien moi truong (khong ghi thang vao code neu se day len GitHub cong khai).

---

## CACH 1 — Oracle Cloud Always Free (khuyen dung, mien phi vinh vien)

Ban se co 1 may chu ao (VPS) Linux mien phi, chay 24/7 that su.

### B1. Tao tai khoan
1. Vao https://www.oracle.com/cloud/free/
2. Dang ky (can email + the visa/mastercard de XAC MINH, KHONG bi tru tien).
3. Chon vung gan: Singapore / Tokyo / Seoul.

### B2. Tao may chu (Instance)
1. Menu -> Compute -> Instances -> Create Instance.
2. Image: chon **Ubuntu 22.04**.
3. Shape: chon loai co chu **"Always Free-eligible"**
   (VD: VM.Standard.E2.1.Micro hoac Ampere A1).
4. Phan SSH keys: bam **Save private key** (luu file .key ve may) -> Create.

### B3. Ket noi vao may chu
- Windows: dung **PowerShell**:
  ```
  ssh -i duong_dan_toi_file.key ubuntu@DIA_CHI_IP_MAY_CHU
  ```
  (DIA_CHI_IP xem trong trang Instance vua tao)

### B4. Cai va chay bot
Tren may chu, go lan luot:
```bash
sudo apt update && sudo apt install -y python3 git
git clone <link-github-cua-ban> btc-signal-bot   # hoac dung scp de chep code len
cd btc-signal-bot

# Chay thu:
python3 bot.py --once

# Cai chay 24/7 (tu bat lai khi loi / khi reboot):
sudo cp deploy/btc-signal-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/btc-signal-bot.service   # sua TELEGRAM_TOKEN va duong dan neu can
sudo systemctl daemon-reload
sudo systemctl enable --now btc-signal-bot
```

### B5. Kiem tra
```bash
journalctl -u btc-signal-bot -f     # xem log truc tiep
```
Vao Telegram go /start -> bot phai tra loi. Xong! Tat may cua ban, bot van chay.

---

## CACH 2 — Fly.io (deploy nhanh bang lenh)

### B1. Cai cong cu
- Tai flyctl: https://fly.io/docs/hractl/installing/
- Dang ky: `fly auth signup` (can the de xac minh).

### B2. Deploy
Trong thu muc du an:
```bash
fly launch --no-deploy      # tao app, giu file fly.toml co san (chon No khi hoi ghi de)
fly secrets set TELEGRAM_TOKEN=TOKEN_MOI_CUA_BAN
fly deploy
```

### B3. Xem log / kiem tra
```bash
fly logs
```
Vao Telegram go /start -> bot tra loi la thanh cong.

---

## Luu y quan trong

- **Bao mat token:** neu day code len GitHub CONG KHAI, token trong config.py se bi lo.
  Hay xoa token trong config.py (de trong chuoi mac dinh) va chi dat qua bien moi truong.
- **Du lieu nguoi dung** (subscribers.json, watchlist.json) da bi .gitignore bo qua ->
  tren cloud bot se tu tao lai khi co nguoi go /start.
- Chi chay **1 ban bot** tai 1 thoi diem (dung token). Chay 2 noi cung token -> loi 409.
