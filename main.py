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
Generate exactly 3 short, interesting facts or updates about what's happening in the world right now.

Pick a random topic from one of these categories:
- 🌍 Global Events & Geopolitics (wars, conflicts, diplomacy, elections, treaties)
- 💰 Economy & Price Hikes (inflation, commodity prices, fuel, food costs, stock market)
- 🤖 New AI Tools & Inventions (new models like OpenClaw, NemoClaw, new startups, breakthroughs)
- 🔬 Science & Technology (space missions, medical breakthroughs, quantum computing, robotics)
- ⚠️ Risks & Threats (cybersecurity, climate disasters, pandemics, supply chain issues)
- 🏛️ Policy & Regulations (new laws, tech regulations, trade policies, sanctions)
- 🚀 Startups & Business (funding rounds, acquisitions, IPOs, new products)

Rules:
- Simple English, easy to understand
- Maximum 3 lines per point
- Share real, interesting, and recent-sounding information
- No introductions or conclusions
- Use numbered format (1., 2., 3.)
- Include the category emoji and topic name at the top
- Use relevant emojis in each point
- Make it feel like a quick morning news briefing
"""

# Generate content
response = model.generate_content(prompt)
message = "📰 *Daily World Briefing*\n\n" + response.text

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
