import os
import requests
import json

# -------------------------------
# Read Environment Variables
# -------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

CHAT_IDS_FILE = "chat_ids.txt"
OFFSET_FILE = "last_update_id.txt"

# -------------------------------
# Welcome Message
# -------------------------------
WELCOME_MESSAGE = """👋 <b>Welcome to Daily World Briefing Bot!</b>

🤖 <b>Created by Manoj Kuppala</b>

📰 This bot sends you a <b>daily news briefing</b> every morning with:

• 💻 Latest Tech Gadgets & AI Hardware
• 🚀 Startup Companies & New Technologies
• 🌍 Global events & geopolitics
• 💰 Economy & price updates
• 🤖 Latest AI tools & software models
• 🔬 Science & breakthroughs
• 💼 Job market & career trends
• 🏵️ Telugu States (AP & Telangana) news

⏰ <b>Delivery Time:</b> Every day at <b>9:00 AM IST</b>

✅ You are now registered! Just sit back and wait for your first briefing tomorrow morning.

💡 <i>Powered by Gemini AI + Google Search for real-time news</i>"""


def load_existing_chat_ids():
    if not os.path.exists(CHAT_IDS_FILE):
        return set()
    with open(CHAT_IDS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_chat_ids(chat_ids):
    with open(CHAT_IDS_FILE, "w") as f:
        for chat_id in sorted(chat_ids):
            f.write(f"{chat_id}\n")


def load_last_offset():
    if not os.path.exists(OFFSET_FILE):
        return None
    with open(OFFSET_FILE, "r") as f:
        content = f.read().strip()
        return int(content) if content else None


def save_last_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def send_welcome(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": WELCOME_MESSAGE,
                "parse_mode": "HTML",
            },
            timeout=20
        )
        if r.status_code == 200:
            print(f"✅ Welcome message sent to {chat_id}")
        else:
            print(f"❌ Failed to send welcome to {chat_id}: {r.text}")
    except Exception as e:
        print(f"❌ Error sending welcome to {chat_id}: {e}")


def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 5}
    if offset:
        params["offset"] = offset

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                return data.get("result", [])
        elif r.status_code == 409 and "webhook is active" in r.text.lower():
            print("ℹ️ Telegram Webhook is active! Instant replies are operating via your deployment. Polling skipped safely.")
            return []
        print(f"⚠️ getUpdates response: {r.text}")
    except Exception as e:
        print(f"❌ Error fetching updates: {e}")

    return []


def main():
    existing_ids = load_existing_chat_ids()
    last_offset = load_last_offset()

    print(f"📋 Existing users: {len(existing_ids)}")
    print(f"📍 Last offset: {last_offset}")

    updates = get_updates(last_offset + 1 if last_offset else None)

    if not updates:
        print("📭 No new updates found (or webhook is handling registrations).")
        return False

    new_users_added = False
    max_update_id = last_offset or 0

    for update in updates:
        update_id = update.get("update_id", 0)
        max_update_id = max(max_update_id, update_id)

        message = update.get("message", {})
        text = message.get("text", "")
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        first_name = chat.get("first_name", "Unknown")

        if text.strip() == "/start" and chat_id:
            if chat_id not in existing_ids:
                print(f"🆕 New user: {first_name} (ID: {chat_id})")
                existing_ids.add(chat_id)
                send_welcome(chat_id)
                new_users_added = True
            else:
                print(f"👤 Existing user sent /start: {first_name} (ID: {chat_id})")
                send_welcome(chat_id)

    save_last_offset(max_update_id)

    if new_users_added:
        save_chat_ids(existing_ids)
        print(f"💾 Updated {CHAT_IDS_FILE} — now {len(existing_ids)} users")

    return new_users_added


if __name__ == "__main__":
    changed = main()
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")
    print("🎉 Registration check complete!")
