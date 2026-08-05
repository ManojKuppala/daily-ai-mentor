from datetime import datetime, timezone, timedelta
from app.services.github_service import get_users_from_github, normalize_users, save_users_to_github
from app.services.news_service import generate_news
from app.services.telegram_service import send_telegram_message, send_news_with_logging
from app.services import student_service as stu

IST = timezone(timedelta(hours=5, minutes=30))

def scheduled_job():
    """Runs every minute. Checks for news delivery times and study reminders."""
    now_ist = datetime.now(IST)
    current_time = now_ist.strftime("%H:%M")
    current_day = now_ist.strftime("%A")
    
    print(f"[{now_ist}] Scheduler tick: {current_time}")
    
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

        # --- NEWS DELIVERY ---
        if user.get("time") == current_time:
            print(f"Time match ({current_time}) for user {chat_id}. Generating news...")
            user_topics = user.get("topics", [])
            
            # Rollover tasks from yesterday
            stu.rollover_tasks(user)
            
            # Build the full daily message
            countdown = stu.get_countdown_text(user)
            motivation = stu.generate_motivational_line(user)
            news = generate_news(user_topics)
            
            # Weekly priority reminder
            wp = user.get("weekly_priority")
            wp_text = f"\n📌 <b>This week's priority:</b> {wp}\n" if wp else ""
            
            full_msg = countdown + wp_text + news + "\n\n" + motivation
            
            # Update briefing streak
            stu.update_streak(user, "briefing")
            users[chat_id] = user
            changed = True
            
            send_news_with_logging(chat_id, user_topics, full_msg)

        # --- STUDY REMINDERS ---
        for reminder in user.get("reminders", []):
            if reminder.get("time") == current_time:
                msg = f"🔔 <b>Reminder:</b> {reminder['label']}\n\nTime to focus! You've got this. 💪"
                send_telegram_message(chat_id, msg)

    # --- WEEKLY SUMMARY (Sunday 8 PM IST) ---
    if current_day == "Sunday" and current_time == "20:00":
        for chat_id, prefs in users.items():
            user = stu.ensure_student_fields(prefs)
            if user.get("status") == "paused":
                continue
            summary = stu.generate_weekly_summary(user)
            send_telegram_message(chat_id, summary)

    if changed:
        save_users_to_github(users, sha)
