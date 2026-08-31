"""AI Mentor Service: Goals, Tasks, Reminders, Deep Work, and Accountability."""

from datetime import datetime, timezone, timedelta
import random

IST = timezone(timedelta(hours=5, minutes=30))

def _now_ist():
    return datetime.now(IST)

def _today_str():
    return _now_ist().strftime("%Y-%m-%d")


# ===================================================================
#  USER DATA SCHEMA INITIALIZATION
# ===================================================================

def ensure_student_fields(user_data):
    """Ensure a user record has all mentor & accountability fields."""
    defaults = {
        "goals": [],
        "tasks": [],
        "reminders": [],
        "weekly_priority": None,
        "deep_work": None,
        "task_id_counter": 0,
        "goal_id_counter": 0,
        "reminder_id_counter": 0,
        "time": user_data.get("time", "08:30"),
        "status": user_data.get("status", "active")
    }
    for key, val in defaults.items():
        if key not in user_data:
            user_data[key] = val
            
    # Clean out any legacy keys
    for legacy_key in ["topics", "quiz", "streaks", "study_buddy"]:
        user_data.pop(legacy_key, None)
        
    return user_data


# ===================================================================
#  GOALS MANAGEMENT
# ===================================================================

def add_goal(user_data, name, target_date_str):
    """Add a long-term goal with a target deadline."""
    user_data = ensure_student_fields(user_data)
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD (e.g., 2026-10-30)."
    
    if target <= _now_ist().date():
        return False, "Target date must be in the future."
    
    user_data["goal_id_counter"] += 1
    goal = {
        "id": user_data["goal_id_counter"],
        "name": name.strip(),
        "target_date": target_date_str,
        "created_date": _today_str()
    }
    user_data["goals"].append(goal)
    days_left = (target - _now_ist().date()).days
    return True, f"🎯 Goal locked in: <b>{name}</b> ({days_left} days remaining until {target_date_str})!"


def delete_goal(user_data, goal_id):
    """Delete a goal by ID."""
    user_data = ensure_student_fields(user_data)
    before = len(user_data["goals"])
    user_data["goals"] = [g for g in user_data["goals"] if g["id"] != goal_id]
    return len(user_data["goals"]) < before


def get_goals(user_data):
    """Get active goals with days remaining."""
    user_data = ensure_student_fields(user_data)
    today = _now_ist().date()
    active = []
    for g in user_data["goals"]:
        try:
            target = datetime.strptime(g["target_date"], "%Y-%m-%d").date()
            days_left = (target - today).days
            active.append({**g, "days_left": days_left})
        except ValueError:
            continue
    active.sort(key=lambda x: x["days_left"])
    return active


def get_countdown_text(user_data):
    """Generate clean goal countdown string."""
    goals = get_goals(user_data)
    if not goals:
        return ""
    lines = ["🎯 <b>Milestone Countdowns:</b>"]
    for g in goals[:3]:
        badge = "🔴" if g["days_left"] <= 7 else "🟡" if g["days_left"] <= 30 else "🟢"
        lines.append(f"{badge} <b>{g['days_left']} days</b> until {g['name']}")
    return "\n".join(lines)


# ===================================================================
#  TASKS MANAGEMENT & PROCRASTINATION ENGINE
# ===================================================================

def add_task(user_data, text, for_tomorrow=False):
    """Add an actionable task."""
    user_data = ensure_student_fields(user_data)
    target_date = (_now_ist().date() + timedelta(days=1)).strftime("%Y-%m-%d") if for_tomorrow else _today_str()
    
    user_data["task_id_counter"] += 1
    task = {
        "id": user_data["task_id_counter"],
        "text": text.strip(),
        "date": target_date,
        "created_date": _today_str(),
        "status": "pending",
        "carried_over": for_tomorrow
    }
    user_data["tasks"].append(task)
    return task


import re

def complete_task(user_data, task_id_or_match):
    """Mark a task as completed with flexible ID, substring, and keyword matching."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    query = str(task_id_or_match).strip().lower()
    
    # 1. Exact ID match
    for t in user_data["tasks"]:
        if t["status"] == "pending" and str(t["id"]) == query:
            t["status"] = "done"
            t["completed_date"] = today
            return True, t["text"]

    # Clean query of common filler words
    cleaned_query = query
    for filler in ["completed", "complete", "done with", "done", "finished", "finish", "task", "the"]:
        cleaned_query = cleaned_query.replace(filler, "").strip()

    # 2. Substring match
    if cleaned_query:
        for t in user_data["tasks"]:
            if t["status"] == "pending":
                t_lower = t["text"].lower()
                if cleaned_query in t_lower or t_lower in cleaned_query:
                    t["status"] = "done"
                    t["completed_date"] = today
                    return True, t["text"]

    # 3. Keyword word-by-word overlap match
    if cleaned_query:
        query_words = set(w for w in re.findall(r'\w+', cleaned_query) if len(w) > 2)
        for t in user_data["tasks"]:
            if t["status"] == "pending":
                task_words = set(w for w in re.findall(r'\w+', t["text"].lower()) if len(w) > 2)
                if query_words & task_words:
                    t["status"] = "done"
                    t["completed_date"] = today
                    return True, t["text"]
                    
    return False, None


def complete_all_pending_tasks(user_data):
    """Mark all today's pending tasks as done."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    count = 0
    for t in user_data["tasks"]:
        if t["status"] == "pending" and (t["date"] == today or t.get("carried_over")):
            t["status"] = "done"
            t["completed_date"] = today
            count += 1
    return count


def delete_task(user_data, task_id):
    """Delete a task by ID."""
    user_data = ensure_student_fields(user_data)
    before = len(user_data["tasks"])
    user_data["tasks"] = [t for t in user_data["tasks"] if t["id"] != task_id]
    return len(user_data["tasks"]) < before


def get_pending_tasks(user_data):
    """Get active pending tasks for today."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    return [t for t in user_data["tasks"] if t["status"] == "pending" and (t["date"] <= today or t.get("carried_over"))]


def get_stale_tasks(user_data, days_threshold=2):
    """Detect tasks that have been pending for > 2 days (Procrastination Detection)."""
    user_data = ensure_student_fields(user_data)
    today = _now_ist().date()
    stale = []
    for t in user_data["tasks"]:
        if t["status"] == "pending":
            created = datetime.strptime(t.get("created_date", t["date"]), "%Y-%m-%d").date()
            days_pending = (today - created).days
            if days_pending >= days_threshold:
                stale.append({**t, "days_pending": days_pending})
    stale.sort(key=lambda x: x["days_pending"], reverse=True)
    return stale


def rollover_tasks(user_data):
    """Roll over uncompleted tasks from previous days to today."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    for t in user_data["tasks"]:
        if t["status"] == "pending" and t["date"] < today:
            t["date"] = today
            t["carried_over"] = True


# ===================================================================
#  REMINDERS & DEEP WORK MANAGEMENT
# ===================================================================

def add_reminder(user_data, time_str, label, daily=True):
    """Add a scheduled reminder."""
    user_data = ensure_student_fields(user_data)
    user_data["reminder_id_counter"] += 1
    rem = {
        "id": user_data["reminder_id_counter"],
        "time": time_str,
        "label": label.strip(),
        "daily": daily,
        "created_date": _today_str()
    }
    user_data["reminders"].append(rem)
    user_data["reminders"].sort(key=lambda x: x["time"])
    return rem


def delete_reminder(user_data, rem_id):
    """Delete a reminder by ID."""
    user_data = ensure_student_fields(user_data)
    before = len(user_data["reminders"])
    user_data["reminders"] = [r for r in user_data["reminders"] if r["id"] != rem_id]
    return len(user_data["reminders"]) < before


def start_deep_work(user_data, duration_minutes, label="Focused Deep Work"):
    """Start a deep work timer."""
    user_data = ensure_student_fields(user_data)
    end_time = _now_ist() + timedelta(minutes=duration_minutes)
    user_data["deep_work"] = {
        "label": label,
        "duration": duration_minutes,
        "end_time_str": end_time.strftime("%H:%M"),
        "end_timestamp": end_time.isoformat()
    }
    return user_data["deep_work"]


def check_deep_work_completion(user_data):
    """Check if deep work block has ended."""
    dw = user_data.get("deep_work")
    if not dw:
        return None
    try:
        end_time = datetime.fromisoformat(dw["end_timestamp"])
        if _now_ist() >= end_time:
            label = dw["label"]
            duration = dw["duration"]
            user_data["deep_work"] = None
            return f"⏰ <b>Deep Work Complete!</b>\n\nGreat execution! You just crushed <b>{duration} minutes</b> on <i>{label}</i>. Take a 10-min screen break."
    except Exception:
        user_data["deep_work"] = None
    return None


def set_weekly_priority(user_data, priority_text):
    """Set top weekly priority."""
    user_data = ensure_student_fields(user_data)
    user_data["weekly_priority"] = priority_text.strip()
    return user_data["weekly_priority"]


# ===================================================================
#  FORMATTERS: MORNING, EVENING, NIGHT & STATUS
# ===================================================================

DISCIPLINE_QUOTES = [
    "“We don't rise to the level of our expectations, we fall to the level of our training.”",
    "“Discipline equals freedom. Win the morning, win the day.”",
    "“Small daily improvements over time lead to stunning results.”",
    "“Action cures anxiety. Start with the hardest task first.”",
    "“You don't need motivation. You need a standard you refuse to lower.”",
    "“Focus on the process, and the outcomes will take care of themselves.”",
    "“Procrastination is the arrogant assumption that God owes you another chance.”"
]

def format_morning_gameplan(user_data):
    """Generate the 08:30 AM Morning Focus Gameplan."""
    user_data = ensure_student_fields(user_data)
    rollover_tasks(user_data)
    
    today_formatted = _now_ist().strftime("%A, %d %B %Y")
    lines = [
        f"🌅 <b>Morning Gameplan Briefing</b>",
        f"🗓️ <i>{today_formatted}</i>",
        "━" * 26,
        ""
    ]
    
    # 1. Goals & Countdowns
    countdown = get_countdown_text(user_data)
    if countdown:
        lines.append(countdown)
        lines.append("")
        
    # 2. Week Priority
    wp = user_data.get("weekly_priority")
    if wp:
        lines.append(f"📌 <b>Week Priority:</b> {wp}\n")
        
    # 3. Procrastination Alerts (Tasks pending > 2 days)
    stale = get_stale_tasks(user_data, days_threshold=2)
    if stale:
        lines.append("⚠️ <b>Reality Check (Pending > 2 Days):</b>")
        for st in stale[:2]:
            lines.append(f"• <i>{st['text']}</i> (stalled for {st['days_pending']} days — knock this out first!)")
        lines.append("")
        
    # 4. Today's Planned Tasks
    pending = get_pending_tasks(user_data)
    if pending:
        lines.append("📋 <b>Today's Execution List:</b>")
        for i, t in enumerate(pending, 1):
            lines.append(f"{i}. ⬜ {t['text']}")
    else:
        lines.append("📋 <b>Tasks:</b> No tasks scheduled yet today. Type a task or plan tonight!")
        
    lines.append("")
    
    # 5. Scheduled Reminders
    rems = user_data.get("reminders", [])
    if rems:
        lines.append("⏰ <b>Today's Schedule:</b>")
        for r in rems:
            lines.append(f"• <code>{r['time']}</code> — {r['label']}")
        lines.append("")
        
    # 6. Mindset Quote
    lines.append("💡 <i>" + random.choice(DISCIPLINE_QUOTES) + "</i>")
    lines.append("━" * 26)
    lines.append("💬 <i>Reply anytime to add tasks, complete items, or set reminders.</i>")
    
    return "\n".join(lines)


def format_evening_review(user_data):
    """Generate the 09:00 PM Accountability Check."""
    user_data = ensure_student_fields(user_data)
    pending = get_pending_tasks(user_data)
    
    lines = [
        "🌙 <b>Evening Accountability Check (9:00 PM)</b>",
        "━" * 26,
        ""
    ]
    
    if not pending:
        lines.append("🎉 <b>Incredible work!</b> All of today's tasks are completed!")
        lines.append("Take time to recharge, and prepare to lock in tomorrow's tasks at 10:30 PM.")
    else:
        lines.append("Let's review today's pending tasks:")
        for i, t in enumerate(pending, 1):
            lines.append(f"{i}. ⏳ {t['text']}")
        lines.append("\n💬 <b>Reply with what you finished</b> (e.g., <i>'done with 1'</i> or <i>'completed all'</i>) so we can close out today cleanly!")
        
    return "\n".join(lines)


def format_night_planning(user_data):
    """Generate the 10:30 PM Night Planning Prompt."""
    return """🎯 <b>Night Planning for Tomorrow (10:30 PM)</b>
━━━━━━━━━━━━━━━━━━━━

Win tomorrow before it even starts. What are your <b>top 2 to 4 priority tasks</b> for tomorrow?

💬 <b>Just reply with your brain dump</b>, for example:
• <i>1. Solve 2 LeetCode trees problems</i>
• <i>2. Build Express authentication API</i>
• <i>3. Remind me at 5pm to review resume</i>

I'll automatically organize them into your morning gameplan!"""


def format_weekly_summary(user_data):
    """Generate the Sunday 08:00 PM Strategic Review."""
    user_data = ensure_student_fields(user_data)
    today = _now_ist().date()
    week_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    
    done_tasks = [t for t in user_data["tasks"] if t.get("completed_date", "") >= week_start and t["status"] == "done"]
    pending_tasks = get_pending_tasks(user_data)
    
    lines = [
        "📊 <b>Sunday Weekly Executive Summary</b>",
        "━" * 26,
        f"✅ <b>Tasks Completed This Week:</b> {len(done_tasks)}",
        f"⏳ <b>Current Pending Tasks:</b> {len(pending_tasks)}",
        ""
    ]
    
    goals = get_goals(user_data)
    if goals:
        lines.append("🎯 <b>Active Goal Velocity:</b>")
        for g in goals[:3]:
            lines.append(f"• {g['name']}: <b>{g['days_left']} days left</b>")
        lines.append("")
        
    wp = user_data.get("weekly_priority")
    if wp:
        lines.append(f"📌 <b>Last week's priority:</b> {wp}")
        
    lines.append("\n💬 <i>Take 2 minutes to reply with your #1 priority focus for the upcoming week!</i>")
    return "\n".join(lines)


def format_tasks_list(user_data):
    """Format full task list view."""
    user_data = ensure_student_fields(user_data)
    pending = get_pending_tasks(user_data)
    if not pending:
        return "📋 <b>No pending tasks!</b>\n\nText me to add one (e.g., <i>'add task: revise system design'</i>)."
        
    lines = ["📋 <b>Your Active Tasks:</b>\n"]
    for i, t in enumerate(pending, 1):
        stale_indicator = " ⚠️ (stalled)" if datetime.strptime(t.get("created_date", t["date"]), "%Y-%m-%d").date() <= (_now_ist().date() - timedelta(days=2)) else ""
        lines.append(f"{i}. ⬜ <b>{t['text']}</b>{stale_indicator}")
        
    lines.append("\n💬 <i>To mark done, just text: 'done 1' or 'completed [task name]'</i>")
    return "\n".join(lines)


def format_goals_list(user_data):
    """Format full goals list view."""
    goals = get_goals(user_data)
    if not goals:
        return "🎯 <b>No goals set yet!</b>\n\nText me to add one (e.g., <i>'set goal: Crack MERN job by 2026-10-30'</i>)."
        
    lines = ["🎯 <b>Your Milestone Goals:</b>\n"]
    for i, g in enumerate(goals, 1):
        badge = "🔴" if g["days_left"] <= 7 else "🟡" if g["days_left"] <= 30 else "🟢"
        lines.append(f"{i}. {badge} <b>{g['name']}</b>\n   ⏳ <b>{g['days_left']} days remaining</b> (Target: {g['target_date']})\n")
    return "\n".join(lines)


def format_reminders_list(user_data):
    """Format reminders list view."""
    rems = user_data.get("reminders", [])
    if not rems:
        return "⏰ <b>No reminders set!</b>\n\nText me to add one (e.g., <i>'remind me daily at 8:00 for DSA'</i>)."
        
    lines = ["⏰ <b>Your Scheduled Reminders:</b>\n"]
    for i, r in enumerate(rems, 1):
        lines.append(f"{i}. 🔔 <code>{r['time']}</code> — <b>{r['label']}</b> (Daily)")
    return "\n".join(lines)
