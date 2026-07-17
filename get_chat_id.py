"""
Cong cu lay CHAT_ID.

Cach dung:
  1) Add bot (@rose_monitor_bot) vao group, HOAC nhan Start voi bot.
  2) Gui 1 tin nhan bat ky vao group / cho bot (vi du: "hello").
  3) Chay:  py get_chat_id.py
  4) Copy so ID hien ra, dat vao config.CHAT_ID hoac bien moi truong TELEGRAM_CHAT_ID.
"""
import telegram_bot


def main():
    print("Dang lay tin nhan gan day tu Telegram...\n")
    res = telegram_bot.get_updates()
    if not res.get("ok"):
        print("Loi:", res)
        return

    results = res.get("result", [])
    if not results:
        print("Chua thay tin nhan nao.")
        print("=> Hay gui 1 tin nhan cho bot / trong group roi chay lai file nay.")
        return

    seen = {}
    for u in results:
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        cid = chat.get("id")
        if cid is None:
            continue
        title = chat.get("title") or chat.get("username") or chat.get("first_name") or "?"
        seen[cid] = (chat.get("type", "?"), title)

    if not seen:
        print("Khong tim thay chat nao trong cac update.")
        return

    print("Danh sach chat tim duoc:")
    print("-" * 50)
    for cid, (ctype, title) in seen.items():
        print(f"  CHAT_ID = {cid:<18} | loai: {ctype:<10} | ten: {title}")
    print("-" * 50)
    print("\n=> Copy CHAT_ID phu hop, dat vao config.py (bien CHAT_ID).")


if __name__ == "__main__":
    main()
