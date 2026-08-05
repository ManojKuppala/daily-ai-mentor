"""Student companion features: goals, tasks, streaks, quiz, mood, journal."""

from datetime import datetime, timezone, timedelta
import random

IST = timezone(timedelta(hours=5, minutes=30))

def _now_ist():
    return datetime.now(IST)

def _today_str():
    return _now_ist().strftime("%Y-%m-%d")

# ===================================================================
#  GOAL MANAGEMENT
# ===================================================================

def ensure_student_fields(user_data):
    """Ensure a user record has all student companion fields."""
    defaults = {
        "goals": [],
        "tasks": [],
        "reminders": [],
        "streaks": {
            "briefing": 0, "task": 0, "quiz": 0,
            "last_briefing": None, "last_task": None, "last_quiz": None
        },
        "quiz": {"correct": 0, "attempted": 0},
        "mood_today": None,
        "mood_date": None,
        "journal": {},
        "weekly_priority": None,
        "study_buddy": None,
        "task_id_counter": 0,
        "goal_id_counter": 0,
        "reminder_id_counter": 0,
    }
    for key, val in defaults.items():
        if key not in user_data:
            user_data[key] = val
    return user_data


def add_goal(user_data, name, target_date_str):
    """Add a goal with a target date. Returns (success, message)."""
    user_data = ensure_student_fields(user_data)
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD (e.g., 2026-06-15)"
    
    if target <= _now_ist().date():
        return False, "Target date must be in the future."
    
    user_data["goal_id_counter"] += 1
    goal = {
        "id": user_data["goal_id_counter"],
        "name": name.strip(),
        "target_date": target_date_str,
        "created_at": _today_str()
    }
    user_data["goals"].append(goal)
    days_left = (target - _now_ist().date()).days
    return True, f"✅ Goal set: <b>{name}</b>\n📅 Target: {target_date_str} ({days_left} days away)"


def remove_goal(user_data, goal_id):
    """Remove a goal by ID."""
    user_data = ensure_student_fields(user_data)
    before = len(user_data["goals"])
    user_data["goals"] = [g for g in user_data["goals"] if g["id"] != goal_id]
    return len(user_data["goals"]) < before


def get_goals(user_data):
    """Return list of goals sorted by nearest deadline."""
    user_data = ensure_student_fields(user_data)
    today = _now_ist().date()
    goals = []
    for g in user_data["goals"]:
        target = datetime.strptime(g["target_date"], "%Y-%m-%d").date()
        days_left = (target - today).days
        goals.append({**g, "days_left": days_left})
    goals.sort(key=lambda x: x["days_left"])
    return goals


def get_countdown_text(user_data):
    """Generate countdown header for the daily briefing."""
    goals = get_goals(user_data)
    if not goals:
        return ""
    
    nearest = goals[0]
    days = nearest["days_left"]
    name = nearest["name"]
    
    if days < 0:
        return f"⏰ <b>{name}</b> deadline has passed ({abs(days)} days ago)\n"
    elif days == 0:
        return f"🔥 <b>{name}</b> is TODAY! You've got this! 💪\n"
    elif days <= 7:
        return f"🔴 <b>{days} days</b> until <b>{name}</b> — Final stretch! Every hour counts.\n"
    elif days <= 30:
        return f"🟡 <b>{days} days</b> until <b>{name}</b> — Stay focused, you're close.\n"
    else:
        return f"🟢 <b>{days} days</b> until <b>{name}</b> — Steady progress wins.\n"


def format_goals_list(user_data):
    """Format goals for display."""
    goals = get_goals(user_data)
    if not goals:
        return "📋 You haven't set any goals yet.\n\nUse the button below to add your first goal!"
    
    lines = ["🎯 <b>Your Goals</b>\n"]
    for g in goals:
        days = g["days_left"]
        if days < 0:
            badge = "⏰ PASSED"
        elif days <= 7:
            badge = f"🔴 {days}d"
        elif days <= 30:
            badge = f"🟡 {days}d"
        else:
            badge = f"🟢 {days}d"
        lines.append(f"  {badge}  <b>{g['name']}</b> — {g['target_date']}")
    return "\n".join(lines)


# ===================================================================
#  TASK MANAGEMENT
# ===================================================================

def add_task(user_data, text, goal_id=None, recurring=None):
    """Add a task. Returns (success, message)."""
    user_data = ensure_student_fields(user_data)
    user_data["task_id_counter"] += 1
    task = {
        "id": user_data["task_id_counter"],
        "text": text.strip(),
        "goal_id": goal_id,
        "status": "pending",
        "date": _today_str(),
        "recurring": recurring,  # None, "daily", or "weekly"
        "carried_over": False
    }
    user_data["tasks"].append(task)
    return True, f"✅ Task added: <b>{text}</b>"


def complete_task(user_data, task_id):
    """Mark a task as done."""
    user_data = ensure_student_fields(user_data)
    for task in user_data["tasks"]:
        if task["id"] == task_id and task["status"] == "pending":
            task["status"] = "done"
            task["completed_date"] = _today_str()
            # Update task streak
            update_streak(user_data, "task")
            return True
    return False


def delete_task(user_data, task_id):
    """Delete a task."""
    user_data = ensure_student_fields(user_data)
    before = len(user_data["tasks"])
    user_data["tasks"] = [t for t in user_data["tasks"] if t["id"] != task_id]
    return len(user_data["tasks"]) < before


def skip_task(user_data, task_id):
    """Mark a task as skipped (planned rest, doesn't break streak)."""
    user_data = ensure_student_fields(user_data)
    for task in user_data["tasks"]:
        if task["id"] == task_id and task["status"] == "pending":
            task["status"] = "skipped"
            return True
    return False


def get_today_tasks(user_data):
    """Get today's pending and carried-over tasks."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    tasks = []
    for t in user_data["tasks"]:
        if t["status"] == "pending" and (t["date"] == today or t.get("carried_over")):
            tasks.append(t)
    return tasks


def rollover_tasks(user_data):
    """Roll over yesterday's incomplete tasks to today."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    rolled = 0
    for task in user_data["tasks"]:
        if task["status"] == "pending" and task["date"] < today and not task.get("carried_over"):
            task["carried_over"] = True
            task["date"] = today
            rolled += 1
    
    # Handle recurring tasks: create new instances
    for task in list(user_data["tasks"]):
        if task["status"] == "done" and task.get("recurring"):
            if task["recurring"] == "daily" and task.get("completed_date", "") < today:
                add_task(user_data, task["text"], task.get("goal_id"), task["recurring"])
            # Weekly: only on same weekday
            elif task["recurring"] == "weekly":
                completed = datetime.strptime(task.get("completed_date", today), "%Y-%m-%d")
                if (_now_ist().date() - completed.date()).days >= 7:
                    add_task(user_data, task["text"], task.get("goal_id"), task["recurring"])
    
    return rolled


def format_tasks_list(user_data):
    """Format today's tasks for display."""
    tasks = get_today_tasks(user_data)
    if not tasks:
        return "📋 No tasks for today!\n\nUse /addtask to add something to work on."
    
    lines = ["📋 <b>Today's Tasks</b>\n"]
    for t in tasks:
        marker = "🔄 " if t.get("carried_over") else "⬜ "
        goal_tag = ""
        if t.get("goal_id"):
            goals = [g for g in user_data.get("goals", []) if g["id"] == t["goal_id"]]
            if goals:
                goal_tag = f" [📎 {goals[0]['name']}]"
        lines.append(f"  {marker}<b>{t['text']}</b>{goal_tag}")
    
    done_today = sum(1 for t in user_data.get("tasks", []) 
                     if t["status"] == "done" and t.get("completed_date") == _today_str())
    if done_today > 0:
        lines.append(f"\n✅ {done_today} task{'s' if done_today != 1 else ''} completed today")
    
    return "\n".join(lines)


# ===================================================================
#  REMINDER MANAGEMENT
# ===================================================================

def add_reminder(user_data, label, time_str):
    """Add a daily reminder. Returns (success, message)."""
    user_data = ensure_student_fields(user_data)
    user_data["reminder_id_counter"] += 1
    reminder = {
        "id": user_data["reminder_id_counter"],
        "label": label.strip(),
        "time": time_str
    }
    user_data["reminders"].append(reminder)
    return True, f"✅ Reminder set: <b>{label}</b> at <b>{time_str} IST</b>"


def remove_reminder(user_data, reminder_id):
    """Remove a reminder."""
    user_data = ensure_student_fields(user_data)
    before = len(user_data["reminders"])
    user_data["reminders"] = [r for r in user_data["reminders"] if r["id"] != reminder_id]
    return len(user_data["reminders"]) < before


def get_reminders(user_data):
    """Return reminders sorted by time."""
    user_data = ensure_student_fields(user_data)
    return sorted(user_data.get("reminders", []), key=lambda r: r["time"])


def format_reminders_list(user_data):
    """Format reminders for display."""
    reminders = get_reminders(user_data)
    if not reminders:
        return "⏰ No reminders set.\n\nUse /remind to add study reminders!"
    
    lines = ["⏰ <b>Your Daily Reminders</b>\n"]
    for r in reminders:
        lines.append(f"  🔔 <b>{r['time']}</b> — {r['label']}")
    return "\n".join(lines)


# ===================================================================
#  STREAK MANAGEMENT
# ===================================================================

def update_streak(user_data, streak_type):
    """Update a streak (briefing, task, or quiz). Call when the action happens."""
    user_data = ensure_student_fields(user_data)
    streaks = user_data["streaks"]
    today = _today_str()
    last_key = f"last_{streak_type}"
    
    last_date = streaks.get(last_key)
    if last_date == today:
        return  # Already counted today
    
    if last_date:
        yesterday = (_now_ist().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_date == yesterday:
            streaks[streak_type] += 1
        else:
            streaks[streak_type] = 1  # Reset — streak broken
    else:
        streaks[streak_type] = 1  # First day
    
    streaks[last_key] = today
    
    # Check for milestones
    return check_milestone(streaks[streak_type], streak_type)


def check_milestone(count, streak_type):
    """Return a milestone message if the count hits a notable number."""
    milestones = {
        3: "Nice start",
        7: "One full week",
        14: "Two weeks strong",
        21: "Habit forming",
        30: "Incredible consistency",
        50: "Half-century",
        100: "Legendary"
    }
    type_labels = {"briefing": "📰 Briefing", "task": "✅ Task", "quiz": "🧠 Quiz"}
    label = type_labels.get(streak_type, streak_type)
    
    if count in milestones:
        return f"🏆 <b>{label} streak: {count} days!</b> — {milestones[count]}!"
    return None


def format_streaks(user_data):
    """Format streak display."""
    user_data = ensure_student_fields(user_data)
    s = user_data["streaks"]
    lines = [
        "🔥 <b>Your Streaks</b>\n",
        f"  📰 Briefing: <b>{s['briefing']} day{'s' if s['briefing'] != 1 else ''}</b>",
        f"  ✅ Tasks: <b>{s['task']} day{'s' if s['task'] != 1 else ''}</b>",
        f"  🧠 Quiz: <b>{s['quiz']} day{'s' if s['quiz'] != 1 else ''}</b>",
    ]
    return "\n".join(lines)


# ===================================================================
#  PROGRESS & WEEKLY SUMMARY
# ===================================================================

def get_daily_completion_rate(user_data):
    """Calculate today's task completion rate."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    today_tasks = [t for t in user_data["tasks"] if t["date"] == today or t.get("carried_over")]
    total = len([t for t in today_tasks if t["status"] in ("done", "pending")])
    done = len([t for t in today_tasks if t["status"] == "done"])
    if total == 0:
        return 0, 0, 0
    return done, total, round(done / total * 100)


def format_progress(user_data):
    """Format progress display."""
    user_data = ensure_student_fields(user_data)
    done, total, rate = get_daily_completion_rate(user_data)
    s = user_data["streaks"]
    q = user_data["quiz"]
    
    lines = [
        "📊 <b>Your Progress</b>\n",
        f"<b>Today's Tasks:</b> {done}/{total} completed ({rate}%)",
        "",
        f"🔥 <b>Streaks</b>",
        f"  📰 Briefing: {s['briefing']} days",
        f"  ✅ Tasks: {s['task']} days",
        f"  🧠 Quiz: {s['quiz']} days",
        "",
        f"🧠 <b>Quiz Stats</b>",
        f"  Correct: {q['correct']}/{q['attempted']}",
    ]
    
    if q["attempted"] > 0:
        accuracy = round(q["correct"] / q["attempted"] * 100)
        lines.append(f"  Accuracy: {accuracy}%")
    
    goals = get_goals(user_data)
    if goals:
        lines.append("")
        lines.append("🎯 <b>Goals</b>")
        for g in goals[:3]:
            lines.append(f"  {'🔴' if g['days_left'] <= 7 else '🟡' if g['days_left'] <= 30 else '🟢'} {g['name']}: {g['days_left']}d left")
    
    return "\n".join(lines)


def generate_weekly_summary(user_data):
    """Generate the Sunday evening weekly reflection message."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    s = user_data["streaks"]
    q = user_data["quiz"]
    
    # Count this week's completed tasks
    week_start = (_now_ist().date() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_tasks = [t for t in user_data["tasks"] 
                  if t.get("completed_date", "") >= week_start and t["status"] == "done"]
    
    lines = [
        "📬 <b>Weekly Reflection</b>",
        f"━{'━' * 26}",
        "",
        f"✅ <b>Tasks completed this week:</b> {len(week_tasks)}",
        f"🔥 <b>Current streaks:</b> Briefing {s['briefing']}d | Tasks {s['task']}d | Quiz {s['quiz']}d",
    ]
    
    if q["attempted"] > 0:
        accuracy = round(q["correct"] / q["attempted"] * 100)
        lines.append(f"🧠 <b>Quiz accuracy:</b> {accuracy}% ({q['correct']}/{q['attempted']})")
    
    goals = get_goals(user_data)
    if goals:
        lines.append("")
        for g in goals[:3]:
            lines.append(f"🎯 {g['name']}: <b>{g['days_left']} days</b> remaining")
    
    wp = user_data.get("weekly_priority")
    if wp:
        lines.append(f"\n📌 Weekly priority was: <b>{wp}</b>")
    
    # Journal entries this week
    journal = user_data.get("journal", {})
    week_entries = {k: v for k, v in journal.items() if k >= week_start}
    if week_entries:
        lines.append(f"\n📝 You journaled {len(week_entries)} day{'s' if len(week_entries) != 1 else ''} this week")
    
    # Motivational closer
    lines.append("")
    lines.append(generate_motivational_line(user_data))
    
    return "\n".join(lines)


# ===================================================================
#  MOTIVATION
# ===================================================================

def generate_motivational_line(user_data):
    """Generate a data-driven motivational line, not a generic quote."""
    user_data = ensure_student_fields(user_data)
    s = user_data["streaks"]
    goals = get_goals(user_data)
    done, total, rate = get_daily_completion_rate(user_data)
    
    lines = []
    
    if s["briefing"] >= 7:
        lines.append(f"💡 {s['briefing']} days of showing up. That's not luck — that's discipline.")
    if s["task"] >= 3:
        lines.append(f"💡 {s['task']}-day task streak. Consistency is your superpower.")
    if rate >= 80 and total > 0:
        lines.append(f"💡 {rate}% completion today. You're operating at a high level.")
    if goals and goals[0]["days_left"] <= 7:
        lines.append(f"💡 {goals[0]['days_left']} days to {goals[0]['name']}. You've prepared for this. Trust your work.")
    if goals and goals[0]["days_left"] <= 30:
        lines.append(f"💡 Every session between now and {goals[0]['name']} compounds. Keep stacking.")
    
    if not lines:
        defaults = [
            "💡 Small steps today, big results tomorrow. Keep going.",
            "💡 You chose to show up today. That already puts you ahead.",
            "💡 The work you do today is a gift to your future self.",
            "💡 Progress isn't always visible, but it's always happening.",
        ]
        lines = [random.choice(defaults)]
    
    return random.choice(lines)


# ===================================================================
#  MOOD
# ===================================================================

def set_mood(user_data, mood):
    """Record today's mood (emoji)."""
    user_data = ensure_student_fields(user_data)
    user_data["mood_today"] = mood
    user_data["mood_date"] = _today_str()
    return True


def get_mood(user_data):
    """Get today's mood, or None if not logged."""
    user_data = ensure_student_fields(user_data)
    if user_data.get("mood_date") == _today_str():
        return user_data.get("mood_today")
    return None


# ===================================================================
#  JOURNAL
# ===================================================================

def add_journal_entry(user_data, text):
    """Add a one-line journal entry for today."""
    user_data = ensure_student_fields(user_data)
    today = _today_str()
    user_data["journal"][today] = text.strip()
    return True


# ===================================================================
#  WEEKLY PRIORITY
# ===================================================================

def set_weekly_priority(user_data, text):
    """Set the weekly top priority."""
    user_data = ensure_student_fields(user_data)
    user_data["weekly_priority"] = text.strip()
    return True
