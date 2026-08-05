import json
import urllib.request
import re
from app.config import Config

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    
    max_length = 3900
    if len(text) <= max_length:
        chunks = [text]
    else:
        parts = text.split('\n\n')
        chunks = []
        current_chunk = ""
        for part in parts:
            if len(current_chunk) + len(part) + 2 < max_length:
                if current_chunk:
                    current_chunk += "\n\n" + part
                else:
                    current_chunk = part
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part
        if current_chunk:
            chunks.append(current_chunk)
            
    final_success = True
    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
        }
        if reply_markup and i == len(chunks) - 1:
            payload["reply_markup"] = reply_markup
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode()
            print(f"HTTP Error sending chunk {i+1}: {error_msg}")
            
            plain_text = re.sub('<[^<]+>', '', chunk)
            payload["text"] = plain_text
            payload.pop("parse_mode", None)
            
            req_fb = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req_fb, timeout=10) as resp:
                    print(f"Fallback plain text sent for chunk {i+1}")
            except Exception as e2:
                print(f"Fallback failed for chunk {i+1}: {e2}")
                final_success = False
        except Exception as e:
            print(f"Error sending chunk {i+1}: {e}")
            final_success = False
            
    return final_success


def send_news_with_logging(chat_id, topics, news_text):
    """Send news and log the delivery attempt."""
    from app.services.delivery_log_service import add_log
    
    success = send_telegram_message(chat_id, news_text)
    if success:
        add_log(chat_id, topics, "delivered")
    else:
        add_log(chat_id, topics, "failed", "Message delivery failed")
    return success
