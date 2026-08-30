"""Telegram Bot Routes: Routes webhook updates to Natural Language AI Mentor or Quick Actions."""

from flask import Blueprint, request, jsonify
import re
from datetime import datetime, timezone, timedelta
from app.services.github_service import get_users_from_github, save_users_to_github
from app.services.telegram_service import send_telegram_message
from app.services import student_service as stu
from app.services import ai_mentor_service

bot_bp = Blueprint('bot', __name__)

IST = timezone(timedelta(hours=5, minutes=30))

_conv_state = {}

def get_main_menu():
    """Minimalist quick-action keyboard."""
    return {"inline_keyboard": [
        [{"text": "🌅 Morning Gameplan", "callback_data": "action_gameplan"},
         {"text": "🌙 Evening Review", "callback_data": "action_review"}],
        [{"text": "📋 Active Tasks", "callback_data": "menu_tasks"},
         {"text": "🎯 Milestone Goals", "callback_data": "menu_goals"}],
        [{"text": "⏰ Daily Reminders", "callback_data": "menu_reminders"},
         {"text": "📌 Week Priority", "callback_data": "action_weekgoal"}],
        [{"text": "⚙️ Delivery Time", "callback_data": "menu_time"}]
    ]}


def get_tasks_keyboard(user_data):
    tasks = stu.get_pending_tasks(user_data)
    keyboard = []
    for t in tasks:
        label = f"⬜ {t['text'][:25]}"
        keyboard.append([
            {"text": label, "callback_data": f"donetask_{t['id']}"},
            {"text": "🗑", "callback_data": f"deltask_{t['id']}"}
        ])
    if tasks:
        keyboard.append([{"text": "✅ Done With All", "callback_data": "done_all_tasks"}])
    keyboard.append([{"text": "➕ Add Task", "callback_data": "addtask"}])
    keyboard.append([{"text": "🔙 Main Menu", "callback_data": "main_menu"}])
    return {"inline_keyboard": keyboard}


def get_goals_keyboard(user_data):
    goals = stu.get_goals(user_data)
    keyboard = []
    for g in goals:
        badge = "🔴" if g["days_left"] <= 7 else "🟡" if g["days_left"] <= 30 else "🟢"
        keyboard.append([
            {"text": f"{badge} {g['name'][:20]} ({g['days_left']}d)", "callback_data": f"viewgoal_{g['id']}"},
            {"text": "🗑", "callback_data": f"delgoal_{g['id']}"}
        ])
    keyboard.append([{"text": "➕ Add Goal", "callback_data": "addgoal"}])
    keyboard.append([{"text": "🔙 Main Menu", "callback_data": "main_menu"}])
    return {"inline_keyboard": keyboard}


def get_reminders_keyboard(user_data):
    reminders = user_data.get("reminders", [])
    keyboard = []
    for r in reminders:
        keyboard.append([
            {"text": f"🔔 {r['time']} — {r['label'][:22]}", "callback_data": f"viewremind_{r['id']}"},
            {"text": "🗑", "callback_data": f"delremind_{r['id']}"}
        ])
    keyboard.append([{"text": "➕ Add Reminder", "callback_data": "addreminder"}])
    keyboard.append([{"text": "🔙 Main Menu", "callback_data": "main_menu"}])
    return {"inline_keyboard": keyboard}


def _create_new_user():
    ist = timezone(timedelta(hours=5, minutes=30))
    user = {
        "time": "08:30", "status": "active",
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
    return "🤖 Daily AI Mentor Web Service is Running!", 200


@bot_bp.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    users, sha = get_users_from_github()

    # =========================================================================
    # 1. TEXT MESSAGE HANDLING (Natural Language Execution)
    # =========================================================================
    if "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"].strip()

        if chat_id not in users:
            users[chat_id] = _create_new_user()
            save_users_to_github(users, sha)
            users, sha = get_users_from_github()

        user = stu.ensure_student_fields(users[chat_id])
        state = _get_state(chat_id)

        # --- Interactive Manual Flow (If user triggered an Add button) ---
        if state == "awaiting_goal_name":
            _set_state(chat_id, "awaiting_goal_date", {"name": text})
            send_telegram_message(chat_id, f"Goal: <b>{text}</b>\n\nEnter the target date in <b>YYYY-MM-DD</b> format:\n(e.g., 2026-10-30)")
            return "OK", 200

        elif state == "awaiting_goal_date":
            name = _get_state_data(chat_id).get("name", "Milestone Goal")
            success, msg = stu.add_goal(user, name, text)
            _clear_state(chat_id)
            if success:
                users[chat_id] = user
                save_users_to_github(users, sha)
            send_telegram_message(chat_id, msg, get_main_menu())
            return "OK", 200

        elif state == "awaiting_task_text":
            task = stu.add_task(user, text)
            _clear_state(chat_id)
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, f"📋 <b>Task Added:</b> <i>{task['text']}</i>", get_tasks_keyboard(user))
            return "OK", 200

        elif state == "awaiting_reminder_label":
            _set_state(chat_id, "awaiting_reminder_time", {"label": text})
            send_telegram_message(chat_id, f"Reminder: <b>{text}</b>\n\nEnter the time in <b>HH:MM</b> format (24-hour IST):\n(e.g., 08:00 or 18:30)")
            return "OK", 200

        elif state == "awaiting_reminder_time":
            label = _get_state_data(chat_id).get("label", "Focus Reminder")
            if re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", text):
                rem = stu.add_reminder(user, text, label)
                _clear_state(chat_id)
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, f"⏰ <b>Reminder Scheduled:</b> <code>{rem['time']}</code> — {rem['label']}", get_reminders_keyboard(user))
            else:
                send_telegram_message(chat_id, "Invalid time format. Use HH:MM (e.g., 08:00 or 19:30)")
            return "OK", 200

        elif state == "awaiting_weekgoal":
            stu.set_weekly_priority(user, text)
            _clear_state(chat_id)
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, f"📌 <b>Weekly priority locked:</b> <i>{text}</i>", get_main_menu())
            return "OK", 200

        # --- Explicit Menu / Start commands ---
        if text.startswith("/start"):
            _clear_state(chat_id)
            send_telegram_message(chat_id, ai_mentor_service._get_welcome_text(), get_main_menu())
            return "OK", 200
        elif text in ["/menu", "menu", "/help"]:
            _clear_state(chat_id)
            send_telegram_message(chat_id, "🎛 <b>AI Mentor Control Panel</b>", get_main_menu())
            return "OK", 200

        # --- Dynamic AI Intent Parser ---
        response_text, has_changes = ai_mentor_service.process_natural_message(chat_id, user, text)
        if has_changes:
            users[chat_id] = user
            save_users_to_github(users, sha)

        send_telegram_message(chat_id, response_text)
        return "OK", 200

    # =========================================================================
    # 2. INLINE BUTTON CALLBACK QUERIES
    # =========================================================================
    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = str(cq["message"]["chat"]["id"])
        data = cq["data"]

        if chat_id not in users:
            users[chat_id] = _create_new_user()
            save_users_to_github(users, sha)
            users, sha = get_users_from_github()

        user = stu.ensure_student_fields(users[chat_id])
        _clear_state(chat_id)

        if data == "main_menu":
            send_telegram_message(chat_id, "🎛 <b>Main Menu</b>", get_main_menu())

        elif data == "action_gameplan":
            send_telegram_message(chat_id, stu.format_morning_gameplan(user), get_main_menu())

        elif data == "action_review":
            send_telegram_message(chat_id, stu.format_evening_review(user), get_tasks_keyboard(user))

        elif data == "menu_time":
            send_telegram_message(chat_id, "⏰ To change your morning briefing time, just text me (e.g., <i>'set morning briefing to 08:00'</i>).")

        # --- TASKS ---
        elif data == "menu_tasks":
            send_telegram_message(chat_id, stu.format_tasks_list(user), get_tasks_keyboard(user))

        elif data == "addtask":
            _set_state(chat_id, "awaiting_task_text")
            send_telegram_message(chat_id, "📋 What task do you want to add?\n\nType it below:")

        elif data.startswith("donetask_"):
            task_id = int(data.replace("donetask_", ""))
            ok, name = stu.complete_task(user, task_id)
            if ok:
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, f"✅ <b>Task Completed:</b> <i>{name}</i>", get_tasks_keyboard(user))

        elif data == "done_all_tasks":
            count = stu.complete_all_pending_tasks(user)
            users[chat_id] = user
            save_users_to_github(users, sha)
            send_telegram_message(chat_id, f"🎉 <b>All {count} tasks completed!</b> Excellent execution.", get_main_menu())

        elif data.startswith("deltask_"):
            task_id = int(data.replace("deltask_", ""))
            if stu.delete_task(user, task_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "🗑 Task deleted.", get_tasks_keyboard(user))

        # --- GOALS ---
        elif data == "menu_goals":
            send_telegram_message(chat_id, stu.format_goals_list(user), get_goals_keyboard(user))

        elif data == "addgoal":
            _set_state(chat_id, "awaiting_goal_name")
            send_telegram_message(chat_id, "🎯 What milestone goal do you want to set?\n(e.g., <i>Crack MERN Job</i>)")

        elif data.startswith("delgoal_"):
            goal_id = int(data.replace("delgoal_", ""))
            if stu.delete_goal(user, goal_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "🗑 Goal deleted.", get_goals_keyboard(user))

        # --- REMINDERS ---
        elif data == "menu_reminders":
            send_telegram_message(chat_id, stu.format_reminders_list(user), get_reminders_keyboard(user))

        elif data == "addreminder":
            _set_state(chat_id, "awaiting_reminder_label")
            send_telegram_message(chat_id, "⏰ What should I remind you about?\n(e.g., <i>DSA Problems</i>)")

        elif data.startswith("delremind_"):
            rem_id = int(data.replace("delremind_", ""))
            if stu.delete_reminder(user, rem_id):
                users[chat_id] = user
                save_users_to_github(users, sha)
                send_telegram_message(chat_id, "🗑 Reminder removed.", get_reminders_keyboard(user))

        # --- WEEK PRIORITY ---
        elif data == "action_weekgoal":
            _set_state(chat_id, "awaiting_weekgoal")
            current = user.get("weekly_priority")
            msg = "📌 Set your top priority for this week.\n"
            if current:
                msg += f"Current: <b>{current}</b>\n"
            msg += "\nType your weekly priority below:"
            send_telegram_message(chat_id, msg)

    return "OK", 200
