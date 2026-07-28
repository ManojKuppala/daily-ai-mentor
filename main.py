import os
import requests
import google.generativeai as genai

# -------------------------------
# Read Environment Variables
# -------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing!")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

# -------------------------------
# Read Chat IDs
# -------------------------------
with open("chat_ids.txt", "r") as f:
    CHAT_IDS = [line.strip() for line in f if line.strip()]

if not CHAT_IDS:
    raise ValueError("chat_ids.txt is empty!")

# -------------------------------
# Configure Gemini
# -------------------------------
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

prompt = """
You are my personal AI mentor.

Generate today's learning message.

Requirements:
- Exactly 3 learning points.
- Each point should be 2-3 sentences.
- Keep it simple and interesting.
- Choose from Python, JavaScript, React, Django, AI/ML,
  Data Structures & Algorithms, Quantum Computing,
  Interview Preparation, or Computer Science.
- Do not repeat yesterday's content.
- Format nicely using Markdown.
- Add suitable emojis.
"""

response = model.generate_content(prompt)

message = f"""📚 *Daily AI Mentor*

{response.text}

Have a productive day! 🚀
"""

# -------------------------------
# Send to Telegram
# -------------------------------
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

for chat_id in CHAT_IDS:
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=20
        )

        if response.status_code == 200:
            print(f"✅ Sent successfully to {chat_id}")
        else:
            print(f"❌ Failed for {chat_id}")
            print(response.text)

    except Exception as e:
        print(f"❌ Error sending to {chat_id}: {e}")

print("🎉 Finished sending Daily AI Mentor messages.")
