import os
import json
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from bot_logic import generate_news

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "ManojKuppala/daily-ai-mentor")
USERS_FILE = "users.json"

AVAILABLE_TOPICS = [
    "💻 Tech & Hardware",
    "🚀 Startups & Business",
    "📈 Stock Market & Finance",
    "🔬 Science & Space",
    "🧠 Educational Facts & History",
    "🌍 Global News",
    "🏏 Cricket News"
]

WELCOME_MESSAGE = """👋 <b>Welcome to Daily World Briefing Bot!</b>

🤖 <b>Created by Manoj Kuppala</b>

📰 This bot sends you a custom <b>daily news briefing</b> tailored to your interests!

Please use the buttons below to set up your preferences:"""

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

# --- GITHUB JSON DATABASE FUNCTIONS ---

def get_users_from_github():
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, skipping remote file fetch.")
        return {}, None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            content = base64.b64decode(data["content"]).decode("utf-8")
            sha = data["sha"]
            return json.loads(content), sha
    except urllib.error.HTTPError as e:
        if e.code == 404: # File doesn't exist yet
            return {}, None
        print(f"Error fetching users: {e}")
        return {}, None
    except Exception as e:
        print(f"Error fetching users: {e}")
        return {}, None

def save_users_to_github(users_data, sha=None):
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, cannot update repository automatically.")
        # Fallback to local save for testing
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=4)
        return False

    new_content = json.dumps(users_data, indent=4)
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE}"
    payload = {
        "message": f"Auto-update users database",
        "content": encoded_content,
        "committer": {
            "name": "Daily AI Mentor Bot",
            "email": "bot@daily-ai-mentor.com"
        }
    }
    if sha:
        payload["sha"] = sha

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in [200, 201]:
                return True
    except Exception as e:
        print(f"Error updating GitHub: {e}")
    return False

def update_user_pref(chat_id, key, value):
    users, sha = get_users_from_github()
    chat_id = str(chat_id)
    if chat_id not in users:
        users[chat_id] = {"time": "09:00", "topics": ["💻 Tech & Hardware", "🚀 Startups & Business"]}
    
    if key == "topics_toggle":
        if value in users[chat_id]["topics"]:
            users[chat_id]["topics"].remove(value)
        else:
            users[chat_id]["topics"].append(value)
    else:
        users[chat_id][key] = value
        
    save_users_to_github(users, sha)
    return users[chat_id]

# --- KEYBOARDS ---

def get_main_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "⏰ Set Delivery Time", "callback_data": "menu_time"}],
            [{"text": "📚 Choose Topics", "callback_data": "menu_topics"}],
            [{"text": "⚡ Get News Now", "callback_data": "action_now"}]
        ]
    }

def get_time_keyboard():
    times = ["07:00", "08:00", "09:00", "17:00", "18:00", "20:00"]
    keyboard = []
    row = []
    for t in times:
        row.append({"text": t, "callback_data": f"set_time_{t}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    keyboard.append([{"text": "⬅️ Back", "callback_data": "menu_main"}])
    return {"inline_keyboard": keyboard}

def get_topics_keyboard(user_topics):
    keyboard = []
    for topic in AVAILABLE_TOPICS:
        prefix = "✅ " if topic in user_topics else "❌ "
        keyboard.append([{"text": prefix + topic, "callback_data": f"toggle_topic_{AVAILABLE_TOPICS.index(topic)}"}])
    keyboard.append([{"text": "⬅️ Back", "callback_data": "menu_main"}])
    return {"inline_keyboard": keyboard}

# --- WEBHOOK HANDLERS ---

@app.route("/")
def home():
    return """
    <h1>🤖 Daily World Briefing Bot</h1>
    <p>Webhook & Scheduler Status: Online ✅</p>
    <p><a href="/setup-webhook"><button style="padding:10px 15px; font-size:16px; cursor:pointer;">⚡ One-Click Setup Telegram Webhook</button></a></p>
    """

@app.route("/setup-webhook")
def setup_webhook():
    if not BOT_TOKEN:
        return "❌ Error: TELEGRAM_BOT_TOKEN environment variable is missing!", 500

    webhook_url = request.host_url.rstrip("/") + "/webhook"
    if not webhook_url.startswith("https://"):
        webhook_url = "https://" + request.host_url.lstrip("http://").rstrip("/") + "/webhook"

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={urllib.parse.quote(webhook_url)}"
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                return f"<h2>✅ Telegram Webhook Activated!</h2><p>URL: <b>{webhook_url}</b></p>"
            else:
                return f"❌ Telegram API Error: {data}", 400
    except Exception as e:
        return f"❌ Failed to set webhook: {e}", 500

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "no data"}), 200

    # Handle Callback Queries (Button clicks)
    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]
        message_id = query["message"]["message_id"]

        users, _ = get_users_from_github()
        user_prefs = users.get(str(chat_id), {"time": "09:00", "topics": ["💻 Tech & Hardware", "🚀 Startups & Business"]})

        new_markup = None
        new_text = "Select an option:"

        if data == "menu_main":
            new_markup = get_main_keyboard()
            new_text = WELCOME_MESSAGE
        elif data == "menu_time":
            new_markup = get_time_keyboard()
            new_text = f"⏰ Your current time: {user_prefs['time']}\nSelect a new delivery time (IST):"
        elif data == "menu_topics":
            new_markup = get_topics_keyboard(user_prefs["topics"])
            new_text = "📚 Select the topics you want in your daily briefing:"
        elif data.startswith("set_time_"):
            time_val = data.split("_")[2]
            update_user_pref(chat_id, "time", time_val)
            new_markup = get_time_keyboard()
            new_text = f"✅ Time updated to {time_val} IST!\nSelect another time or go back."
        elif data.startswith("toggle_topic_"):
            topic_idx = int(data.split("_")[2])
            topic_name = AVAILABLE_TOPICS[topic_idx]
            updated_prefs = update_user_pref(chat_id, "topics_toggle", topic_name)
            new_markup = get_topics_keyboard(updated_prefs["topics"])
            new_text = "📚 Select the topics you want in your daily briefing:"
        elif data == "action_now":
            send_telegram_message(chat_id, "⏳ Cooking your personalized news right now... please wait a few seconds!")
            news = generate_news(user_prefs["topics"])
            send_telegram_message(chat_id, news)
            return jsonify({"status": "ok"}), 200

        # Answer Callback to stop loading animation
        try:
            urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery?callback_query_id={query['id']}")
        except:
            pass
            
        # Edit Message
        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": new_text, "parse_mode": "HTML"}
        if new_markup: payload["reply_markup"] = new_markup
        req = urllib.request.Request(edit_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try: urllib.request.urlopen(req)
        except Exception as e: print("Error editing:", e)

        return jsonify({"status": "ok"}), 200

    # Handle standard messages
    message = update.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return jsonify({"status": "no chat_id"}), 200

    if text.strip().startswith("/start") or text.strip().startswith("/menu"):
        update_user_pref(chat_id, "active", True) # Just to ensure they exist in DB
        send_telegram_message(chat_id, WELCOME_MESSAGE, get_main_keyboard())
    elif text.strip().startswith("/now"):
        users, _ = get_users_from_github()
        user_prefs = users.get(str(chat_id), {"topics": ["💻 Tech & Hardware", "🚀 Startups & Business"]})
        send_telegram_message(chat_id, "⏳ Cooking your personalized news right now... please wait a few seconds!")
        news = generate_news(user_prefs["topics"])
        send_telegram_message(chat_id, news)
    elif text.strip().startswith("/time"):
        send_telegram_message(chat_id, "⏰ Select a delivery time (IST):", get_time_keyboard())
    elif text.strip().startswith("/topics"):
        users, _ = get_users_from_github()
        user_prefs = users.get(str(chat_id), {"topics": []})
        send_telegram_message(chat_id, "📚 Select the topics you want:", get_topics_keyboard(user_prefs["topics"]))

    return jsonify({"status": "ok"}), 200

# --- BACKGROUND SCHEDULER ---

def scheduled_job():
    print(f"[{datetime.now()}] Running scheduled job check...")
    ist = timezone(timedelta(hours=5, minutes=30))
    current_time_ist = datetime.now(ist).strftime("%H:%M")
    
    users, _ = get_users_from_github()
    if not users:
        return

    for chat_id, prefs in users.items():
        if prefs.get("time") == current_time_ist:
            print(f"Time match ({current_time_ist}) for user {chat_id}. Generating news...")
            news = generate_news(prefs.get("topics", []))
            send_telegram_message(chat_id, news)

# Start APScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_job, trigger="cron", minute="*") # Run every minute to check matches
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
