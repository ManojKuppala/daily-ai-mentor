import os
import requests
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types

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
    print("⚠️ chat_ids.txt is empty! No one to send to.")
    exit(0)

# -------------------------------
# Configure Gemini with Google Search
# -------------------------------
client = genai.Client(api_key=GEMINI_API_KEY)

google_search_tool = types.Tool(
    google_search=types.GoogleSearch()
)

prompt = """
You are an expert tech journalist and world news briefing assistant. Use Google Search to find real, verified news from TODAY or YESTERDAY.
You MUST generate exactly 8 crisp, fascinating news updates. NO generic high-level fluff. You must name real companies, exact device models, hardware specs (like RAM or chip names), and real events.

MANDATORY GUARANTEED TOPICS (You MUST include ALL 3 of these first every single day):
1. 💻 Tech Gadgets & AI Hardware: Report a newly announced or trending piece of hardware (e.g., an AI PC/laptop with massive RAM like Lenovo Yoga / ASUS / MacBook AI PCs, new NVIDIA/Intel/AMD AI processor, or innovative smart device). State exact hardware specs!
2. 🚀 Startup Companies & New Technologies: Report on an exciting emerging tech startup, a disruptive company invention, a massive funding round, or a breakthrough proprietary tool. Name the company and explain their tech!
3. 🏵️ Telugu States News: Real, verified current news from Andhra Pradesh or Telangana (e.g., IT announcements in Hyderabad or Amaravati, CM decisions, regional infrastructure, tech investment).

REMAINING 5 TOPICS (Pick 5 diverse topics from this list):
- 🤖 New AI Tools & Models (latest AI software capabilities, coding assistants, OpenClaw/NemoClaw/LLM breakthroughs)
- 💰 Economy & Price Hikes (inflation trends, commodity/gold/oil prices, stock market shifts)
- 💼 Job Markets & Careers (tech hiring trends, in-demand technical skills, salary shifts, corporate hiring)
- 🌍 Global Events & Geopolitics (major international diplomacy, treaties, critical global updates)
- 🔬 Science & Research Advances (space exploration missions, quantum computing, scientific discovery)
- ⚠️ Risks & Threats (cybersecurity warnings, climate disasters, supply chain alerts)
- 🏛️ Policy & Regulations (new tech regulations, government AI laws, global trade policies)

FORMAT STRICTLY AS HTML (no markdown, no numbered lists):

<b>Category Emoji Category Name</b>
2-3 lines of real current facts, naming specific devices, startups, specs, or people. Include relevant emojis.

Rules:
- STRICTLY use HTML tags (<b> for headers). Do NOT use markdown (**bold**) or numbering (1., 2.).
- CRITICAL: NEVER use the "&" symbol (write the word "and" instead). NEVER use "<" or ">" symbols (except for the <b> tags). Telegram will crash if you use them!
- Put a single empty line between each news block.
- Be precise, exciting, and specific!
"""

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[google_search_tool],
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ]
        )
    )
    raw_text = response.text.strip()
except Exception as e:
    print(f"❌ Gemini API Error: {e}")
    if 'response' in locals() and hasattr(response, 'candidates') and response.candidates:
        print(f"Finish reason: {response.candidates[0].finish_reason}")
    import sys
    sys.exit(1)

# Get today's date in IST
ist = timezone(timedelta(hours=5, minutes=30))
today = datetime.now(ist).strftime("%d %B %Y, %A")

# Build the formatted message
header = f"📰 <b>Daily World Briefing</b>\n🗓️ <i>{today}</i>\n{'━' * 28}\n\n"
footer = f"\n{'━' * 28}\n💡 <i>Powered by Gemini AI + Google Search</i>\n📬 <i>Delivered daily at 9:00 AM IST</i>"

import html
# 1. Escape all raw text to make it 100% safe for Telegram's strict parser
safe_body = html.escape(raw_text)
# 2. Restore ONLY the bold and italic tags we instructed the AI to use
safe_body = safe_body.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
safe_body = safe_body.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")

message = header + safe_body + footer

# -------------------------------
# Send to all registered users
# -------------------------------
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

success_count = 0
fail_count = 0

for chat_id in CHAT_IDS:
    try:
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=20
        )

        if r.status_code == 200:
            print(f"✅ Sent successfully to {chat_id}")
            success_count += 1
        else:
            print(f"❌ Failed HTML for {chat_id}: {r.text}")
            print("⚠️ Falling back to plain text...")
            r2 = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": message,
                },
                timeout=20
            )
            if r2.status_code == 200:
                print(f"✅ Sent plain text successfully to {chat_id}")
                success_count += 1
            else:
                print(f"❌ Failed plain text for {chat_id}: {r2.text}")
                fail_count += 1

    except Exception as e:
        print(f"❌ Error sending to {chat_id}: {e}")
        fail_count += 1

import sys

print(f"\n🎉 Done! Sent: {success_count} | Failed: {fail_count}")

if success_count == 0 and fail_count > 0:
    print("❌ All messages failed. Exiting with error so GitHub Actions reports failure.")
    sys.exit(1)
