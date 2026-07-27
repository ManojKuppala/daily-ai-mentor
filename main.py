import os
import requests
import google.generativeai as genai

# Read secrets from environment variables
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

prompt = """
Generate exactly 3 short learning points for a software engineer.

Pick a random topic from:
Python, JavaScript, React, Django, AI/ML, DSA, Quantum Computing, or Interview Preparation.

Rules:
- Simple English
- Maximum 3 lines per point
- Useful for software engineers
- No introductions or conclusions
- Use numbered format (1., 2., 3.)
- Include the topic name at the top
- Use emojis
"""

# Generate content
response = model.generate_content(prompt)
message = "🧠 *Daily AI Mentor*\n\n" + response.text

# Send to Telegram
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": message,
    "parse_mode": "Markdown",
}

r = requests.post(url, json=payload)

if r.status_code == 200:
    print("✅ Message sent successfully!")
else:
    print(f"❌ Failed to send message: {r.status_code}")
    print(r.json())
    raise SystemExit(1)
