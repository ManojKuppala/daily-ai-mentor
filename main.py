import os
import requests
import google.generativeai as genai

# Read secrets
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

prompt = """
Generate exactly 3 short learning points.

Today's topic:
Python, JavaScript, React, Django, AI/ML, DSA, Quantum Computing, or Interview Preparation.

Rules:
- Simple English
- Maximum 3 lines per point
- Useful for software engineers
- No introductions
- Use emojis
"""

response = model.generate_content(prompt)

message = "🧠 *Daily AI Mentor*\n\n" + response.text

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(
    url,
    json={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
)
