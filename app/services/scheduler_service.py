from datetime import datetime, timezone, timedelta
from app.services.github_service import get_users_from_github
from app.services.news_service import generate_news
from app.services.telegram_service import send_telegram_message

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
