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
You are a daily news briefing assistant. Search the web and generate exactly 6 SHORT news updates 
from TODAY or YESTERDAY — real, verified, current events only.

Each point MUST be from a DIFFERENT category. One MUST be Telugu States.
Pick 6 from:
- 🌍 Global Events & Geopolitics (wars, conflicts, diplomacy, elections, treaties)
- 💰 Economy & Price Hikes (inflation, commodity prices, fuel, food costs, stock market)
- 🤖 New AI Tools & Inventions (new AI models, tools, startups, breakthroughs)
- 🔬 Science & Technology (space missions, medical breakthroughs, quantum computing, robotics)
- ⚠️ Risks & Threats (cybersecurity, climate disasters, pandemics, supply chain issues)
- 🏛️ Policy & Regulations (new laws, tech regulations, trade policies, sanctions)
- 🚀 Startups & Business (funding rounds, acquisitions, IPOs, new products)
- 💼 Job Markets & Careers (hiring trends, layoffs, in-demand skills, remote work, salary shifts)
- 🏵️ Telugu States News (Andhra Pradesh & Telangana — politics, development, CM decisions, IT, state economy)

FORMAT STRICTLY LIKE THIS (use HTML tags, NOT markdown):

<b>Category Emoji Category Name</b>
2-3 lines of actual current news with relevant emojis. Must be real events from today or yesterday.

Rules:
- MUST be real, factual, current news — NOT made up
- Simple English, easy to understand
- Maximum 3 lines per point
- NO introductions, conclusions, or extra commentary
- NO numbering — just bold category headers with emoji
- NO markdown — use ONLY HTML <b> and <i> tags
- Put a blank line between each point
- Use relevant emojis within the text
"""

# Generate content with Google Search grounding
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[google_search_tool]
    )
)

# Get today's date in IST
ist = timezone(timedelta(hours=5, minutes=30))
today = datetime.now(ist).strftime("%d %B %Y, %A")

# Build the formatted message
header = f"📰 <b>Daily World Briefing</b>\n🗓️ <i>{today}</i>\n{'━' * 28}\n\n"
footer = f"\n{'━' * 28}\n💡 <i>Powered by Gemini AI + Google Search</i>\n📬 <i>Delivered daily at 9:00 AM IST</i>"

message = header + response.text.strip() + footer

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
            print(f"❌ Failed for {chat_id}: {r.text}")
            fail_count += 1

    except Exception as e:
        print(f"❌ Error sending to {chat_id}: {e}")
        fail_count += 1

print(f"\n🎉 Done! Sent: {success_count} | Failed: {fail_count}")
