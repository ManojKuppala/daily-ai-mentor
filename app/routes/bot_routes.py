from flask import Blueprint, request, jsonify
import json
import re
from app.config import Config
from app.services.github_service import get_users_from_github, save_users_to_github
from app.services.telegram_service import send_telegram_message
from app.services.news_service import generate_news

bot_bp = Blueprint('bot', __name__)

WELCOME_MESSAGE = """👋 <b>Welcome to Daily World Briefing Bot!</b>

🤖 <b>Created by Manoj Kuppala</b>

📰 This bot sends you a custom <b>daily news briefing</b> tailored to your interests!

Please use the buttons below to set up your preferences:"""

def get_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "📚 Choose Topics", "callback_data": "menu_topics"}],
            [{"text": "⏰ Set Delivery Time", "callback_data": "menu_time"}],
            [{"text": "⚡ Get News Now", "callback_data": "action_get_news"}]
        ]
    }

def get_topics_keyboard(user_topics):
    keyboard = []
    for topic in Config.AVAILABLE_TOPICS:
        prefix = "✅ " if topic in user_topics else ""
        keyboard.append([{"text": f"{prefix}{topic}", "callback_data": f"topic_{topic}"}])
    keyboard.append([{"text": "💾 Save Topics", "callback_data": "save_topics"}])
    return {"inline_keyboard": keyboard}

@bot_bp.route(f"/", methods=["GET"])
def home():
    return "Daily AI Mentor Web Service is Running!", 200

@bot_bp.route(f"/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    users, sha = get_users_from_github()

    if "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"]

        if chat_id not in users:
            users[chat_id] = {"topics": [], "time": "08:00"}
            save_users_to_github(users, sha)

        if text.startswith("/start") or text.startswith("/menu"):
            send_telegram_message(chat_id, WELCOME_MESSAGE, get_main_menu())
        elif text.startswith("/now"):
            send_telegram_message(chat_id, "Fetching real-time data... This takes about 5 seconds. ⏳")
            user_topics = users[chat_id].get("topics", [])
            news = generate_news(user_topics)
            send_telegram_message(chat_id, news)
        elif text.startswith("/topics"):
            user_topics = users[chat_id].get("topics", [])
            send_telegram_message(chat_id, "Select your preferred news topics:", get_topics_keyboard(user_topics))
        elif text.startswith("/time"):
            send_telegram_message(chat_id, "Please type your preferred delivery time in HH:MM format (24-hour, IST timezone).\nExample: <b>08:00</b> or <b>18:30</b>")
        else:
            if re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", text):
                users[chat_id]["time"] = text
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, f"✅ Daily delivery time set to <b>{text} IST</b>.", get_main_menu())
            else:
                send_telegram_message(chat_id, "I didn't understand that command. Please use the menu.", get_main_menu())

    elif "callback_query" in update:
        callback_query = update["callback_query"]
        chat_id = str(callback_query["message"]["chat"]["id"])
        data = callback_query["data"]

        if chat_id not in users:
            users[chat_id] = {"topics": [], "time": "08:00"}
            save_users_to_github(users, sha)

        if data == "menu_topics":
            user_topics = users[chat_id].get("topics", [])
            send_telegram_message(chat_id, "Select your preferred news topics:", get_topics_keyboard(user_topics))
        
        elif data == "menu_time":
            send_telegram_message(chat_id, "Please type your preferred delivery time in HH:MM format (24-hour, IST timezone).\nExample: <b>08:00</b> or <b>18:30</b>")
            
        elif data == "action_get_news":
            send_telegram_message(chat_id, "Fetching real-time data... This takes about 5 seconds. ⏳")
            user_topics = users[chat_id].get("topics", [])
            news = generate_news(user_topics)
            send_telegram_message(chat_id, news)

        elif data.startswith("topic_"):
            topic = data.replace("topic_", "")
            user_topics = users[chat_id].get("topics", [])
            
            if topic in user_topics:
                user_topics.remove(topic)
            else:
                user_topics.append(topic)
                
            users[chat_id]["topics"] = user_topics
            save_users_to_github(users, sha)
            
            send_telegram_message(chat_id, f"Updated '{topic}'. Continue selecting:", get_topics_keyboard(user_topics))

        elif data == "save_topics":
            send_telegram_message(chat_id, "✅ Topics saved successfully!", get_main_menu())

    return "OK", 200
