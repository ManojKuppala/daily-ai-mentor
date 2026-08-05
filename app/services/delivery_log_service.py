from datetime import datetime, timezone, timedelta
import threading

_logs = []
_lock = threading.Lock()
MAX_LOGS = 200

def add_log(chat_id, topics, status, error_message=None):
    """Record a delivery attempt."""
    ist = timezone(timedelta(hours=5, minutes=30))
    entry = {
        "id": len(_logs) + 1,
        "sent_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
        "chat_id": str(chat_id),
        "topics": topics if isinstance(topics, list) else [],
        "status": status,  # "delivered" | "failed" | "bounced"
        "error_message": error_message
    }
    with _lock:
        _logs.insert(0, entry)
        if len(_logs) > MAX_LOGS:
            _logs.pop()
    return entry

def get_logs(limit=50, offset=0, status_filter=None):
    """Return paginated logs, optionally filtered by status."""
    with _lock:
        filtered = list(_logs)
    if status_filter and status_filter != "all":
        filtered = [l for l in filtered if l["status"] == status_filter]
    total = len(filtered)
    return filtered[offset:offset + limit], total

def get_today_count():
    """Count messages sent today (IST)."""
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).strftime("%Y-%m-%d")
    with _lock:
        return sum(1 for l in _logs if l["sent_at"].startswith(today))

def get_total_count():
    """Total logged deliveries."""
    with _lock:
        return len(_logs)
