import os
import requests
import google.generativeai as genai
from datetime import datetime, timezone, timedelta

# Read secrets from environment variables
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

prompt = """
Generate exactly 6 short, interesting facts or updates about what's happening in the world right now.

Each point MUST be from a DIFFERENT category. Pick 6 from (one MUST be Telugu States):
- 🌍 Global Events & Geopolitics (wars, conflicts, diplomacy, elections, treaties)
- 💰 Economy & Price Hikes (inflation, commodity prices, fuel, food costs, stock market)
- 🤖 New AI Tools & Inventions (new models like OpenClaw, NemoClaw, new startups, breakthroughs)
- 🔬 Science & Technology (space missions, medical breakthroughs, quantum computing, robotics)
- ⚠️ Risks & Threats (cybersecurity, climate disasters, pandemics, supply chain issues)
- 🏛️ Policy & Regulations (new laws, tech regulations, trade policies, sanctions)
- 🚀 Startups & Business (funding rounds, acquisitions, IPOs, new products)
- 💼 Job Markets & Careers (hiring trends, layoffs, in-demand skills, remote work, salary shifts)
- 🏵️ Telugu States News (Andhra Pradesh & Telangana — politics, development, CM decisions, IT hubs, new projects, state economy)

FORMAT STRICTLY LIKE THIS (use HTML tags, NOT markdown):

<b>Category Emoji Category Name</b>
Point text here in 2-3 lines. Keep it crisp and informative.

Example output:
<b>🤖 AI Tools & Inventions</b>
OpenAI launched GPT-5 with real-time reasoning capabilities. It can now browse the web and execute code autonomously. Available to Plus subscribers first.

<b>💰 Economy & Price Hikes</b>
Gold prices hit $2,800/oz as central banks stockpile reserves. Crude oil climbed to $88/barrel amid Middle East tensions. Analysts predict further inflation in Q3.

Rules:
- Simple English, easy to understand
- Maximum 3 lines per point
- Share real, interesting, and recent-sounding information
- NO introductions, conclusions, or extra commentary
- NO numbering (no 1., 2., etc.) — just bold category headers
- NO markdown formatting — use ONLY HTML <b> tags for bold
- Put a blank line between each point
- Use relevant emojis within the text
"""

# Generate content
response = model.generate_content(prompt)

# Get today's date in IST
ist = timezone(timedelta(hours=5, minutes=30))
today = datetime.now(ist).strftime("%d %B %Y")

# Build the formatted message
header = f"📰 <b>Daily World Briefing</b>\n🗓️ <i>{today}</i>\n{'━' * 28}\n\n"
footer = f"\n{'━' * 28}\n💡 <i>Powered by Gemini AI | Delivered daily at 8 AM</i>"

message = header + response.text.strip() + footer

# Send to Telegram
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": message,
    "parse_mode": "HTML",
}

r = requests.post(url, json=payload)

if r.status_code == 200:
    print("✅ Message sent successfully!")
else:
    print(f"❌ Failed to send message: {r.status_code}")
    print(r.json())
    raise SystemExit(1)
