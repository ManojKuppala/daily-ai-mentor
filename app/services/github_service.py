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
