# Bot chi dung Python thuan, khong can thu vien ngoai.
FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Khong bo dem log -> thay log ngay tren cloud
ENV PYTHONUNBUFFERED=1

# Token va chat lay tu bien moi truong (dat tren cloud, khong ghi vao code)
# TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (tuy chon)

CMD ["python", "bot.py"]
