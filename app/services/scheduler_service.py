"""Background Scheduler Service: Executes Morning Gameplans, Reminders, Evening Accountability, and Night Planning."""

from datetime import datetime, timezone, timedelta
from app.services.github_service import get_users_from_github, normalize_users, save_users_to_github
from app.services.telegram_service import send_telegram_message
from app.services import student_service as stu

IST = timezone(timedelta(hours=5, minutes=30))

def scheduled_job():
    """Runs every minute to check time-based triggers and reminders."""
    now_ist = datetime.now(IST)
    current_time = now_ist.strftime("%H:%M")
    current_day = now_ist.strftime("%A")
    
    users, sha = get_users_from_github()
    if not users:
        return

    users = normalize_users(users)
    changed = False

    for chat_id, prefs in users.items():
        user = stu.ensure_student_fields(prefs)
        
        # Skip paused users
        if user.get("status") == "paused":
            continue

        # -------------------------------------------------------------
        # 1. MORNING GAMEPLAN BRIEFING (User's customized delivery time, e.g. 08:30)
        # -------------------------------------------------------------
        if user.get("time", "08:30") == current_time:
            print(f"🌅 Delivering Morning Gameplan to {chat_id} at {current_time}")
            gameplan = stu.format_morning_gameplan(user)
            send_telegram_message(chat_id, gameplan)
            users[chat_id] = user
            changed = True

        # -------------------------------------------------------------
        # 2. EVENING ACCOUNTABILITY CHECK (09:00 PM / 21:00 IST)
        # -------------------------------------------------------------
        if current_time == "21:00":
            print(f"🌙 Delivering 9:00 PM Accountability Check to {chat_id}")
            evening_msg = stu.format_evening_review(user)
            send_telegram_message(chat_id, evening_msg)

        # -------------------------------------------------------------
        # 3. NIGHT PLANNING PROMPT (10:30 PM / 22:30 IST)
        # -------------------------------------------------------------
        if current_time == "22:30":
            print(f"🎯 Delivering 10:30 PM Night Planning Prompt to {chat_id}")
            planning_msg = stu.format_night_planning(user)
            send_telegram_message(chat_id, planning_msg)

        # -------------------------------------------------------------
        # 4. SCHEDULED TIMED REMINDERS
        # -------------------------------------------------------------
        for reminder in user.get("reminders", []):
            if reminder.get("time") == current_time:
                msg = f"🔔 <b>Reminder:</b> <b>{reminder['label']}</b>\n\nTime to execute! Action cures procrastination. 💪"
                send_telegram_message(chat_id, msg)

        # -------------------------------------------------------------
        # 5. DEEP WORK SESSION COMPLETION CHECK
        # -------------------------------------------------------------
        dw_alert = stu.check_deep_work_completion(user)
        if dw_alert:
            send_telegram_message(chat_id, dw_alert)
            users[chat_id] = user
            changed = True

        # -------------------------------------------------------------
        # 6. SUNDAY STRATEGIC WEEKLY REVIEW (Sunday 08:00 PM / 20:00 IST)
        # -------------------------------------------------------------
        if current_day == "Sunday" and current_time == "20:00":
            print(f"📊 Delivering Sunday Weekly Reflection to {chat_id}")
            summary = stu.format_weekly_summary(user)
            send_telegram_message(chat_id, summary)

    if changed:
        save_users_to_github(users, sha)
