import json
import base64
import urllib.request
from app.config import Config

def get_users_from_github():
    if not Config.GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, skipping remote file fetch.")
        return {}, None

    url = f"https://api.github.com/repos/{Config.GITHUB_REPO}/contents/{Config.USERS_FILE}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            content = base64.b64decode(data["content"]).decode("utf-8")
            sha = data["sha"]
            return json.loads(content), sha
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}, None
        print(f"Error fetching users: {e}")
        return {}, None
    except Exception as e:
        print(f"Error fetching users: {e}")
        return {}, None

def save_users_to_github(users_data, sha=None):
    if not Config.GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, cannot update repository automatically.")
        with open(Config.USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=4)
        return False

    new_content = json.dumps(users_data, indent=4)
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{Config.GITHUB_REPO}/contents/{Config.USERS_FILE}"
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
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }, method="PUT")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in [200, 201]
    except Exception as e:
        print(f"Error saving to github: {e}")
        return False


def delete_single_user(chat_id):
    """Remove a single user from the database."""
    users, sha = get_users_from_github()
    chat_id = str(chat_id)
    if chat_id in users:
        del users[chat_id]
        return save_users_to_github(users, sha)
    return False


def update_user_status(chat_id, status):
    """Set a user's status to 'active' or 'paused'."""
    users, sha = get_users_from_github()
    chat_id = str(chat_id)
    if chat_id in users:
        users[chat_id]["status"] = status
        return save_users_to_github(users, sha)
    return False


def normalize_users(users):
    """Ensure all user records have required fields with defaults."""
    for chat_id, data in users.items():
        if "status" not in data:
            data["status"] = "active"
        if "joined_at" not in data:
            data["joined_at"] = "Unknown"
        if "topics" not in data:
            data["topics"] = []
        if "time" not in data:
            data["time"] = "08:00"
        # Deduplicate topics: keep emoji-prefixed version, remove plain duplicates
        data["topics"] = _dedup_user_topics(data["topics"])
    return users


def _dedup_user_topics(topics):
    """Remove duplicate topics, keeping the emoji-prefixed version."""
    seen = {}
    for topic in topics:
        canonical = topic
        for emoji in ["💻", "🚀", "📈", "🔬", "🧠", "🌍", "🏏"]:
            canonical = canonical.replace(emoji, "").strip()
        # Prefer the longer (emoji-prefixed) version
        if canonical not in seen or len(topic) > len(seen[canonical]):
            seen[canonical] = topic
    return list(seen.values())
