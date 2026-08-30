import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-do-not-use-in-prod")
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    GITHUB_REPO = os.environ.get("GITHUB_REPO", "ManojKuppala/daily-ai-mentor")
    USERS_FILE = "users.json"
    
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password123")
