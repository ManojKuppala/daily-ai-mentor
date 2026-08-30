import os
from openai import OpenAI
import feedparser
from datetime import datetime, timezone, timedelta
import html

# Try to get Groq API key, otherwise fallback to a generic OpenAI env pattern if needed
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Initialize Groq client using the standard OpenAI SDK
# Only initialize if key is present to prevent crashes on startup
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
) if GROQ_API_KEY else None

RSS_FEEDS = {
    "Tech & Hardware": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Startups & Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Stock Market & Finance": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Science & Space": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "Global News": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Educational Facts & History": "https://feeds.bbci.co.uk/news/education/rss.xml",
    "Cricket News": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"
}

def dedup_topics(topics):
    """Deduplicate topics by canonical name, preferring emoji-prefixed versions."""
    seen = {}
    for topic in topics:
        # Strip emoji to get canonical key
        canonical = topic
        for emoji in ["💻", "🚀", "📈", "🔬", "🧠", "🌍", "🏏"]:
            canonical = canonical.replace(emoji, "").strip()
        # Keep the emoji-prefixed version if we've seen this topic before
        if canonical not in seen or len(topic) > len(seen[canonical]):
            seen[canonical] = topic
    return list(seen.values())


def search_news(topics):
    """Fetches the latest news from RSS feeds for the given topics."""
    topics = dedup_topics(topics)
    search_results = []
    
    for topic in topics:
        clean_topic = topic
        for emoji in ["💻", "🚀", "📈", "🔬", "🧠", "🌍", "🏏"]:
            clean_topic = clean_topic.replace(emoji, "").strip()
            
        feed_url = RSS_FEEDS.get(clean_topic)
        if not feed_url:
            continue
            
        try:
            feed = feedparser.parse(feed_url)
            # Get top 3 news snippets for this topic
            for entry in feed.entries[:3]:
                search_results.append(f"[{topic}] {entry.title}: {entry.get('summary', '')}")
        except Exception as e:
            print(f"RSS Fetch error for {topic}: {e}")
            
    return "\n".join(search_results)

def generate_news(topics):
    """Generates the daily briefing based on specific topics."""
    if not client:
        return "⚠️ Error: GROQ_API_KEY is not set. Please set it in your environment variables."
        
    if not topics:
        topics = ["Tech & Hardware", "Startups & Business", "Global News"]
    
    topics = dedup_topics(topics)
        
    # 1. Fetch real-time data
    print(f"Fetching real-time data for: {topics}")
    live_data = search_news(topics)
    
    # 2. Build the prompt
    current_year = datetime.now().year
    prompt = f"""
You are an expert tech journalist and world news briefing assistant living in the year {current_year}. 
I have fetched the latest real-time search results for the user's favorite topics.

USER'S SELECTED TOPICS:
{', '.join(topics)}

REAL-TIME SEARCH SNIPPETS (Use these to ground your facts!):
{live_data}

INSTRUCTIONS:
CRITICAL: You are living in the year {current_year}. Only talk about current events. DO NOT talk about outdated events (like the iPhone 14 or COVID-19 pandemic) as if they are current.
You MUST generate an attractive, crisp, highly readable briefing based on the search snippets provided.
Use exactly 2 bullet points per topic. Write exactly 1 short, punchy sentence per bullet point. Eliminate ALL fluff and long run-on sentences. Keep it beautiful and easy to read.
If the search snippets are empty or don't have enough info for a topic, state a timeless, fascinating educational fact related to the topic instead of inventing fake news.
Be precise, name real companies, specific events, or actual scientific facts.

FORMAT STRICTLY AS HTML (no markdown, no numbered lists):

<b>Category Emoji Category Name</b>
▪️ <i>Short, punchy, attractive headline 1.</i>
▪️ <i>Short, punchy, attractive headline 2.</i>

Rules:
- STRICTLY use HTML tags (<b> for headers, <i> for italics). Do NOT use markdown (**bold**) or numbering (1., 2.).
- CRITICAL: NEVER use the "&" symbol (write the word "and" instead). NEVER use "<" or ">" symbols (except for the HTML tags).
- Make the output incredibly easy and attractive to read at a glance.
- Put a single empty line between each news block.
"""

    # 3. Call Groq with dynamically discovered active models
    models_to_try = []
    try:
        available_models = client.models.list()
        for m in available_models.data:
            m_id = m.id.lower()
            # filter out non-chat models (audio, whisper, guard, embeddings)
            if any(skip in m_id for skip in ["whisper", "embed", "guard", "audio", "tts", "moderation"]):
                continue
            models_to_try.append(m.id)
        print(f"🔍 Discovered {len(models_to_try)} active Groq models: {models_to_try}")
    except Exception as e:
        print(f"⚠️ Could not fetch models list from Groq: {e}")

    # Fallback list of modern models if list() was unreachable
    fallbacks = [
        "llama-3.3-70b-versatile",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "deepseek-r1-distill-llama-70b",
        "qwen-2.5-32b",
        "gemma2-9b-it"
    ]
    for fb in fallbacks:
        if fb not in models_to_try:
            models_to_try.append(fb)

    raw_text = None
    last_error = None

    for model_name in models_to_try:
        try:
            print(f"🤖 Attempting generation with Groq model: {model_name}")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful AI news assistant that strictly outputs HTML."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            raw_text = response.choices[0].message.content.strip()
            if raw_text:
                print(f"✅ Success with model: {model_name}")
                break
        except Exception as e:
            last_error = e
            print(f"⚠️ Failed with model {model_name}: {e}")
            continue

    if not raw_text:
        print(f"❌ All Groq models failed. Last Error: {last_error}")
        return "❌ <i>Unable to generate daily briefing right now. Please check back shortly.</i>"

    # 4. Format and Escape
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).strftime("%d %B %Y, %A")

    header = f"📰 <b>Daily World Briefing</b>\n🗓️ <i>{today}</i>\n{'━' * 28}\n\n"
    footer = f"\n{'━' * 28}"

    # Escape raw text to make it safe for Telegram's strict parser
    safe_body = html.escape(raw_text)
    # Restore ONLY the bold and italic tags we instructed the AI to use
    safe_body = safe_body.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    safe_body = safe_body.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")

    return header + safe_body + footer
