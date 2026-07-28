import os
import json
import base64
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "ManojKuppala/daily-ai-mentor")
CHAT_IDS_FILE = "chat_ids.txt"

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


def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


def get_chat_ids_from_github():
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, skipping remote file fetch.")
        return set(), None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CHAT_IDS_FILE}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            content = base64.b64decode(data["content"]).decode("utf-8")
            sha = data["sha"]
            ids = set(line.strip() for line in content.splitlines() if line.strip())
            return ids, sha
    except Exception as e:
        print(f"Error fetching chat_ids: {e}")
        return set(), None


def add_chat_id_to_github(chat_id):
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, cannot update repository automatically.")
        return False

    existing_ids, sha = get_chat_ids_from_github()

    if str(chat_id) in existing_ids:
        print(f"Chat ID {chat_id} already registered")
        return True

    existing_ids.add(str(chat_id))
    new_content = "\n".join(sorted(existing_ids)) + "\n"
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CHAT_IDS_FILE}"
    data = json.dumps({
        "message": f"Auto-register user {chat_id} via Webhook",
        "content": encoded_content,
        "sha": sha,
        "committer": {
            "name": "Daily AI Mentor Bot",
            "email": "bot@daily-ai-mentor.com"
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"✅ Added chat ID {chat_id} to GitHub")
                return True
    except Exception as e:
        print(f"Error updating GitHub: {e}")
    return False


@app.route("/")
def home():
    return """
    <h1>🤖 Daily World Briefing Bot</h1>
    <p>Webhook Status: Online ✅</p>
    <p><a href="/setup-webhook"><button style="padding:10px 15px; font-size:16px; cursor:pointer;">⚡ One-Click Setup Telegram Webhook</button></a></p>
    """


@app.route("/setup-webhook")
def setup_webhook():
    if not BOT_TOKEN:
        return "❌ Error: TELEGRAM_BOT_TOKEN environment variable is missing!", 500

    # Derive HTTPS webhook URL automatically from incoming request
    webhook_url = request.host_url.rstrip("/") + "/webhook"
    # Ensure https scheme for Telegram requirement
    if not webhook_url.startswith("https://"):
        webhook_url = "https://" + request.host_url.lstrip("http://").rstrip("/") + "/webhook"

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={urllib.parse.quote(webhook_url)}"
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                return f"""
                <h2>✅ Telegram Webhook Activated Successfully!</h2>
                <p>Webhook URL set to: <b>{webhook_url}</b></p>
                <p>Telegram is now sending instant /start messages straight to your app!</p>
                <p><a href="https://t.me">👉 Go try it on Telegram now</a></p>
                """
            else:
                return f"❌ Telegram API Error: {data}", 400
    except Exception as e:
        return f"❌ Failed to set webhook: {e}", 500


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "no data"}), 200

    message = update.get("message", {})
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return jsonify({"status": "no chat_id"}), 200

    if text.strip().startswith("/start"):
        send_telegram_message(chat_id, WELCOME_MESSAGE)
        add_chat_id_to_github(chat_id)
        print(f"🆕 User interaction handled for ID: {chat_id}")

    return jsonify({"status": "ok"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
