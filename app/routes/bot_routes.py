from flask import Blueprint, request, jsonify
import json
import re
from datetime import datetime, timezone, timedelta
from app.config import Config
from app.services.github_service import get_users_from_github, save_users_to_github
from app.services.telegram_service import send_telegram_message, send_news_with_logging
from app.services.news_service import generate_news
from app.services import student_service as stu

bot_bp = Blueprint('bot', __name__)

IST = timezone(timedelta(hours=5, minutes=30))

# In-memory conversation state: {chat_id: {"state": "...", "data": {...}}}
_conv_state = {}

WELCOME_MESSAGE = """👋 <b>Welcome to Daily AI Mentor!</b>

🤖 <b>Created by Manoj Kuppala</b>

📰 Your personal <b>daily companion</b> for news, goals, tasks, and more!

Use the menu below to get started:"""

def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "📚 Choose Topics", "callback_data": "menu_topics"},
         {"text": "⏰ Set Delivery Time", "callback_data": "menu_time"}],
        [{"text": "⚡ Get News Now", "callback_data": "action_get_news"}],
        [{"text": "🎯 My Goals", "callback_data": "menu_goals"},
         {"text": "📋 My Tasks", "callback_data": "menu_tasks"}],
        [{"text": "📊 Progress", "callback_data": "action_progress"},
         {"text": "⏰ Reminders", "callback_data": "menu_reminders"}],
        [{"text": "📌 Week Priority", "callback_data": "action_weekgoal"}],
    ]}

def get_topics_keyboard(user_topics):
    keyboard = []
    for topic in Config.AVAILABLE_TOPICS:
        prefix = "✅ " if topic in user_topics else ""
        keyboard.append([{"text": f"{prefix}{topic}", "callback_data": f"topic_{topic}"}])
    keyboard.append([{"text": "💾 Save Topics", "callback_data": "save_topics"}])
    return {"inline_keyboard": keyboard}

def get_goals_keyboard(user_data):
    goals = stu.get_goals(user_data)
    keyboard = []
    for g in goals:
        keyboard.append([
            {"text": f"{'🔴' if g['days_left']<=7 else '🟡' if g['days_left']<=30 else '🟢'} {g['name']} ({g['days_left']}d)", "callback_data": f"viewgoal_{g['id']}"},
            {"text": "🗑", "callback_data": f"delgoal_{g['id']}"}
        ])
    keyboard.append([{"text": "➕ Add Goal", "callback_data": "addgoal"}])
    keyboard.append([{"text": "🔙 Main Menu", "callback_data": "main_menu"}])
    return {"inline_keyboard": keyboard}

def get_tasks_keyboard(user_data):
    tasks = stu.get_today_tasks(user_data)
    keyboard = []
    for t in tasks:
        label = f"{'🔄 ' if t.get('carried_over') else ''}⬜ {t['text'][:30]}"
        keyboard.append([
            {"text": label, "callback_data": f"donetask_{t['id']}"},
            {"text": "⏭", "callback_data": f"skiptask_{t['id']}"},
            {"text": "🗑", "callback_data": f"deltask_{t['id']}"}
        ])
    keyboard.append([{"text": "➕ Add Task", "callback_data": "addtask"}])
    keyboard.append([{"text": "🔙 Main Menu", "callback_data": "main_menu"}])
    return {"inline_keyboard": keyboard}

def get_reminders_keyboard(user_data):
    reminders = stu.get_reminders(user_data)
    keyboard = []
    for r in reminders:
        keyboard.append([
            {"text": f"🔔 {r['time']} — {r['label']}", "callback_data": f"viewremind_{r['id']}"},
            {"text": "🗑", "callback_data": f"delremind_{r['id']}"}
        ])
    keyboard.append([{"text": "➕ Add Reminder", "callback_data": "addreminder"}])
    keyboard.append([{"text": "🔙 Main Menu", "callback_data": "main_menu"}])
    return {"inline_keyboard": keyboard}



def _create_new_user():
    ist = timezone(timedelta(hours=5, minutes=30))
    user = {
        "topics": [], "time": "08:00", "status": "active",
        "joined_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M")
    }
    return stu.ensure_student_fields(user)

def _set_state(chat_id, state, data=None):
    _conv_state[str(chat_id)] = {"state": state, "data": data or {}}

def _get_state(chat_id):
    return _conv_state.get(str(chat_id), {}).get("state")

def _get_state_data(chat_id):
    return _conv_state.get(str(chat_id), {}).get("data", {})

def _clear_state(chat_id):
    _conv_state.pop(str(chat_id), None)


@bot_bp.route("/", methods=["GET"])
def home():
    return "Daily AI Mentor Web Service is Running!", 200

@bot_bp.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    users, sha = get_users_from_github()

    # === TEXT MESSAGES ===
    if "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"].strip()

        if chat_id not in users:
            users[chat_id] = _create_new_user()
            save_users_to_github(users, sha)
            # Refresh sha after save
            users, sha = get_users_from_github()

        user = stu.ensure_student_fields(users[chat_id])
        state = _get_state(chat_id)

        # --- CONVERSATION STATE HANDLERS ---
        if state == "awaiting_goal_name":
            _set_state(chat_id, "awaiting_goal_date", {"name": text})
            send_telegram_message(chat_id, f"Goal: <b>{text}</b>\n\nNow enter the target date in <b>YYYY-MM-DD</b> format:\n(e.g., 2026-06-15)")
            return "OK", 200

        elif state == "awaiting_goal_date":
            name = _get_state_data(chat_id).get("name", "My Goal")
            success, msg = stu.add_goal(user, name, text)
            _clear_state(chat_id)
            if success:
                users[chat_id] = user
                save_users_to_github(users, sha)
            send_telegram_message(chat_id, msg, get_main_menu())
            return "OK", 200

        elif state == "awaiting_task_text":
            success, msg = stu.add_task(user, text)
            _clear_state(chat_id)
            if success:
                users[chat_id] = user
                save_users_to_github(users, sha)
            send_telegram_message(chat_id, msg, get_tasks_keyboard(user))
            return "OK", 200

        elif state == "awaiting_reminder_label":
            _set_state(chat_id, "awaiting_reminder_time", {"label": text})
            send_telegram_message(chat_id, f"Reminder: <b>{text}</b>\n\nNow enter the time in <b>HH:MM</b> format (24-hour IST):\n(e.g., 18:00)")
            return "OK", 200

        elif state == "awaiting_reminder_time":
            label = _get_state_data(chat_id).get("label", "Study")
            if re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", text):
                success, msg = stu.add_reminder(user, label, text)
                _clear_state(chat_id)
                if success:
                    users[chat_id] = user
                    save_users_to_github(users, sha)
                send_telegram_message(chat_id, msg, get_reminders_keyboard(user))
            else:
                send_telegram_message(chat_id, "Invalid time format. Use HH:MM (e.g., 18:00)")
            return "OK", 200



        elif state == "awaiting_weekgoal":
            stu.set_weekly_priority(user, text)
            _clear_state(chat_id)
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, f"📌 Weekly priority set: <b>{text}</b>", get_main_menu())
            return "OK", 200

        # --- SLASH COMMANDS ---
        if text.startswith("/start") or text.startswith("/menu"):
            _clear_state(chat_id)
            send_telegram_message(chat_id, WELCOME_MESSAGE, get_main_menu())

        elif text.startswith("/now"):
            send_telegram_message(chat_id, "Fetching real-time data... ⏳")
            user_topics = user.get("topics", [])
            countdown = stu.get_countdown_text(user)
            motivation = stu.generate_motivational_line(user)
            news = generate_news(user_topics)
            full_msg = countdown + news + "\n\n" + motivation
            stu.update_streak(user, "briefing")
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_news_with_logging(chat_id, user_topics, full_msg)

        elif text.startswith("/topics"):
            send_telegram_message(chat_id, "Select your preferred news topics:", get_topics_keyboard(user.get("topics", [])))

        elif text.startswith("/time"):
            send_telegram_message(chat_id, "Please type your preferred delivery time in HH:MM format (24-hour, IST).\nExample: <b>08:00</b> or <b>18:30</b>")

        elif text.startswith("/goal"):
            send_telegram_message(chat_id, stu.format_goals_list(user), get_goals_keyboard(user))

        elif text.startswith("/tasks"):
            stu.rollover_tasks(user)
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, stu.format_tasks_list(user), get_tasks_keyboard(user))

        elif text.startswith("/addtask"):
            _set_state(chat_id, "awaiting_task_text")
            send_telegram_message(chat_id, "📋 What task do you want to add?\n\nType it below:")

        elif text.startswith("/progress") or text.startswith("/streaks"):
            send_telegram_message(chat_id, stu.format_progress(user), get_main_menu())

        elif text.startswith("/remind"):
            send_telegram_message(chat_id, stu.format_reminders_list(user), get_reminders_keyboard(user))

        elif text.startswith("/routine"):
            send_telegram_message(chat_id, stu.format_reminders_list(user), get_reminders_keyboard(user))



        elif text.startswith("/weekgoal"):
            _set_state(chat_id, "awaiting_weekgoal")
            current = user.get("weekly_priority")
            msg = "📌 Set your top priority for this week.\n"
            if current:
                msg += f"Current: <b>{current}</b>\n"
            msg += "\nType your weekly goal:"
            send_telegram_message(chat_id, msg)

        else:
            # Check if it's a time setting
            if re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", text):
                users[chat_id]["time"] = text
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, f"✅ Daily delivery time set to <b>{text} IST</b>.", get_main_menu())
            else:
                send_telegram_message(chat_id, "I didn't understand that. Use /menu to see all options.", get_main_menu())

    # === CALLBACK QUERIES ===
    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = str(cq["message"]["chat"]["id"])
        data = cq["data"]

        if chat_id not in users:
            users[chat_id] = _create_new_user()
            save_users_to_github(users, sha)
            users, sha = get_users_from_github()

        user = stu.ensure_student_fields(users[chat_id])

        # --- MAIN MENU ---
        if data == "main_menu":
            _clear_state(chat_id)
            send_telegram_message(chat_id, "🏠 <b>Main Menu</b>", get_main_menu())

        # --- NEWS TOPICS ---
        elif data == "menu_topics":
            send_telegram_message(chat_id, "Select your preferred news topics:", get_topics_keyboard(user.get("topics", [])))
        elif data.startswith("topic_"):
            topic = data.replace("topic_", "")
            topics = user.get("topics", [])
            if topic in topics:
                topics.remove(topic)
            else:
                topics.append(topic)
            user["topics"] = topics
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, f"Updated '{topic}'.", get_topics_keyboard(topics))
        elif data == "save_topics":
            send_telegram_message(chat_id, "✅ Topics saved!", get_main_menu())

        # --- DELIVERY TIME ---
        elif data == "menu_time":
            send_telegram_message(chat_id, "Type your delivery time in HH:MM format (24-hour IST).\nExample: <b>08:00</b>")

        # --- GET NEWS ---
        elif data == "action_get_news":
            send_telegram_message(chat_id, "Fetching real-time data... ⏳")
            user_topics = user.get("topics", [])
            countdown = stu.get_countdown_text(user)
            motivation = stu.generate_motivational_line(user)
            news = generate_news(user_topics)
            full_msg = countdown + news + "\n\n" + motivation
            stu.update_streak(user, "briefing")
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_news_with_logging(chat_id, user_topics, full_msg)

        # --- GOALS ---
        elif data == "menu_goals":
            send_telegram_message(chat_id, stu.format_goals_list(user), get_goals_keyboard(user))
        elif data == "addgoal":
            _set_state(chat_id, "awaiting_goal_name")
            send_telegram_message(chat_id, "🎯 What's your goal?\n\nType the goal name (e.g., UPSC Prelims, Semester Exam):")
        elif data.startswith("delgoal_"):
            goal_id = int(data.replace("delgoal_", ""))
            if stu.remove_goal(user, goal_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "✅ Goal removed.", get_goals_keyboard(user))
            else:
                send_telegram_message(chat_id, "Goal not found.", get_goals_keyboard(user))

        # --- TASKS ---
        elif data == "menu_tasks":
            stu.rollover_tasks(user)
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, stu.format_tasks_list(user), get_tasks_keyboard(user))
        elif data == "addtask":
            _set_state(chat_id, "awaiting_task_text")
            send_telegram_message(chat_id, "📋 Type your task:")
        elif data.startswith("donetask_"):
            task_id = int(data.replace("donetask_", ""))
            if stu.complete_task(user, task_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "✅ Task completed! Great work!", get_tasks_keyboard(user))
            else:
                send_telegram_message(chat_id, "Task not found.", get_tasks_keyboard(user))
        elif data.startswith("skiptask_"):
            task_id = int(data.replace("skiptask_", ""))
            if stu.skip_task(user, task_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "⏭ Task skipped (planned rest).", get_tasks_keyboard(user))
        elif data.startswith("deltask_"):
            task_id = int(data.replace("deltask_", ""))
            if stu.delete_task(user, task_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "🗑 Task deleted.", get_tasks_keyboard(user))

        # --- PROGRESS ---
        elif data == "action_progress":
            send_telegram_message(chat_id, stu.format_progress(user), get_main_menu())

        # --- REMINDERS ---
        elif data == "menu_reminders":
            send_telegram_message(chat_id, stu.format_reminders_list(user), get_reminders_keyboard(user))
        elif data == "addreminder":
            _set_state(chat_id, "awaiting_reminder_label")
            send_telegram_message(chat_id, "⏰ What should I remind you about?\n\n(e.g., Physics, Maths revision)")
        elif data.startswith("delremind_"):
            rem_id = int(data.replace("delremind_", ""))
            if stu.remove_reminder(user, rem_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "✅ Reminder removed.", get_reminders_keyboard(user))



        # --- WEEK PRIORITY ---
        elif data == "action_weekgoal":
            _set_state(chat_id, "awaiting_weekgoal")
            current = user.get("weekly_priority")
            msg = "📌 Set your top priority for this week.\n"
            if current:
                msg += f"Current: <b>{current}</b>\n"
            msg += "\nType your weekly goal:"
            send_telegram_message(chat_id, msg)

    return "OK", 200
