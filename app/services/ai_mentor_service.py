"""AI Mentor Service: Autonomous Natural Language Intent & Action Parser powered by Groq."""

import os
import json
import re
from datetime import datetime, timezone, timedelta
from openai import OpenAI
from app.services import student_service as stu

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
) if GROQ_API_KEY else None

IST = timezone(timedelta(hours=5, minutes=30))

def _get_active_models():
    """Discover active chat models from Groq."""
    if not client:
        return ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
    try:
        models = client.models.list()
        valid = [
            m.id for m in models.data 
            if not any(x in m.id.lower() for x in ["whisper", "embed", "guard", "audio", "tts", "moderation"])
        ]
        if valid:
            return valid
    except Exception as e:
        print(f"⚠️ Groq models list fallback: {e}")
    return ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "qwen-2.5-32b", "deepseek-r1-distill-llama-70b"]


SYSTEM_PARSER_PROMPT = """You are the core intelligence of an AI Discipline and Accountability Mentor bot.
Your job is to parse incoming user text messages into precise, structured action commands.

TODAY'S DATE IN IST: {today_date} (Format: YYYY-MM-DD)
CURRENT TIME IN IST: {current_time} (Format: HH:MM)

ACTIVE USER CONTEXT:
- Active Goals: {active_goals}
- Today's Pending Tasks: {pending_tasks}
- Scheduled Reminders: {active_reminders}
- Weekly Priority: {weekly_priority}

Analyze the user's message and return ONLY a valid JSON object with the following schema:
{{
  "intent": "add_tasks" | "complete_tasks" | "delete_task" | "add_reminder" | "delete_reminder" | "add_goal" | "delete_goal" | "set_weekly_priority" | "start_deep_work" | "procrastination_advice" | "view_status" | "general_chat",
  "data": {{
      "tasks_to_add": ["task 1 description", "task 2 description"],
      "tasks_to_complete": ["1", "dsa", "all"],
      "task_to_delete": "1" | "task name",
      "reminders_to_add": [
          {{"time": "08:00", "label": "DSA Practice"}},
          {{"time": "17:30", "label": "Review Resume"}}
      ],
      "reminder_to_delete": "1" | "label name",
      "goal_name": "Learn MERN Stack",
      "goal_date": "YYYY-MM-DD",
      "goal_to_delete": "1" | "goal name",
      "weekly_priority": "Build auth routes",
      "deep_work_minutes": 60,
      "deep_work_label": "React Project",
      "advice_topic": "procrastinating on graphs problem"
  }},
  "mentor_response": "A direct, crisp, inspiring 1-2 sentence mentor response confirming the action or offering sharp guidance. Format in clean HTML (<b>bold</b>, <i>italic</i>)."
}}

Rules:
1. If user lists multiple items (brain dump), extract ALL tasks and reminders into their respective arrays.
2. For times, ALWAYS format as 24-hour HH:MM (e.g. 8am -> "08:00", 5:30pm -> "17:30", 8:00 -> "08:00").
3. For dates, calculate exact future YYYY-MM-DD based on today's date ({today_date}).
4. If user says "completed task 1", "done with DSA", "finished all", set "complete_tasks" appropriately.
5. If user expresses feeling lazy, overwhelmed, or stuck, set intent to "procrastination_advice" and provide a sharp, tactical 2-minute actionable nudge in "mentor_response".
6. Return RAW JSON ONLY. No markdown wrapping, no ```json blocks.
"""


def process_natural_message(chat_id, user_data, text):
    """Parse user text with Groq AI and autonomously execute database mutations."""
    user_data = stu.ensure_student_fields(user_data)
    now_ist = datetime.now(IST)
    today_date = now_ist.strftime("%Y-%m-%d")
    current_time = now_ist.strftime("%H:%M")
    
    # 1. Fallback quick manual patterns if Groq is offline or text is trivial
    clean_text = text.strip()
    
    # Check if direct command pattern
    if clean_text == "/start":
        return _get_welcome_text(), False
    elif clean_text in ["/tasks", "/task", "tasks", "my tasks"]:
        return stu.format_tasks_list(user_data), False
    elif clean_text in ["/goals", "/goal", "goals", "my goals"]:
        return stu.format_goals_list(user_data), False
    elif clean_text in ["/reminders", "/remind", "reminders", "schedule"]:
        return stu.format_reminders_list(user_data), False
    elif clean_text in ["/gameplan", "/today", "gameplan", "today"]:
        return stu.format_morning_gameplan(user_data), False
    elif clean_text in ["/review", "review"]:
        return stu.format_evening_review(user_data), False

    if not client:
        return "⚠️ <i>AI Mentor is offline (GROQ_API_KEY missing). Please check your Render configuration.</i>", False

    # 2. Build context for AI parser
    goals_summary = [f"ID {g['id']}: {g['name']} ({g.get('days_left', '?')}d left)" for g in stu.get_goals(user_data)]
    tasks_summary = [f"ID {t['id']}: {t['text']}" for t in stu.get_pending_tasks(user_data)]
    rems_summary = [f"ID {r['id']}: {r['time']} - {r['label']}" for r in user_data.get("reminders", [])]
    
    prompt = SYSTEM_PARSER_PROMPT.format(
        today_date=today_date,
        current_time=current_time,
        active_goals=", ".join(goals_summary) if goals_summary else "None",
        pending_tasks=", ".join(tasks_summary) if tasks_summary else "None",
        active_reminders=", ".join(rems_summary) if rems_summary else "None",
        weekly_priority=user_data.get("weekly_priority") or "None"
    )
    
    models = _get_active_models()
    parsed_json = None
    
    for model_name in models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.2,
                max_tokens=600
            )
            raw = response.choices[0].message.content.strip()
            # Clean possible markdown wrap
            raw = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"^```\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            parsed_json = json.loads(raw)
            if parsed_json:
                break
        except Exception as e:
            print(f"⚠️ Groq parser attempt failed with {model_name}: {e}")
            continue

    if not parsed_json:
        # Graceful fallback: Treat as a new task addition
        task = stu.add_task(user_data, clean_text)
        return f"📋 <b>Task Added:</b> <i>{task['text']}</i>\n\nLocked in for today!", True

    # 3. Execute actions from parsed intent
    intent = parsed_json.get("intent", "general_chat")
    data = parsed_json.get("data", {})
    mentor_response = parsed_json.get("mentor_response", "Got it! Executed.")
    has_changes = False
    
    # --- ADD TASKS ---
    tasks_to_add = data.get("tasks_to_add", [])
    if tasks_to_add:
        added_names = []
        for t_text in tasks_to_add:
            t = stu.add_task(user_data, t_text)
            added_names.append(t['text'])
        has_changes = True
        if len(added_names) == 1:
            mentor_response = f"📋 <b>Task Added:</b> <i>{added_names[0]}</i>\n\n{mentor_response}"
        else:
            tasks_formatted = "\n".join([f"• <i>{name}</i>" for name in added_names])
            mentor_response = f"📋 <b>{len(added_names)} Tasks Added:</b>\n{tasks_formatted}\n\n{mentor_response}"

    # --- COMPLETE TASKS ---
    tasks_to_complete = data.get("tasks_to_complete", [])
    if tasks_to_complete:
        if "all" in [str(x).lower() for x in tasks_to_complete]:
            count = stu.complete_all_pending_tasks(user_data)
            has_changes = True
            mentor_response = f"🎉 <b>Execution Master!</b> All {count} pending tasks marked completed!"
        else:
            completed_names = []
            for target in tasks_to_complete:
                ok, name = stu.complete_task(user_data, target)
                if ok:
                    completed_names.append(name)
            if completed_names:
                has_changes = True
                mentor_response = f"✅ <b>Task Completed:</b> <i>{', '.join(completed_names)}</i>\n\nSolid execution. Keep pushing!"

    # --- DELETE TASK ---
    task_to_del = data.get("task_to_delete")
    if task_to_del:
        for t in list(user_data.get("tasks", [])):
            if str(t["id"]) == str(task_to_del) or str(task_to_del).lower() in t["text"].lower():
                stu.delete_task(user_data, t["id"])
                has_changes = True
                mentor_response = f"🗑 <b>Task Deleted:</b> <i>{t['text']}</i>"
                break

    # --- ADD REMINDERS ---
    reminders_to_add = data.get("reminders_to_add", [])
    if reminders_to_add:
        added_rems = []
        for rem_item in reminders_to_add:
            time_val = rem_item.get("time")
            label_val = rem_item.get("label", "Focus Reminder")
            if time_val:
                r = stu.add_reminder(user_data, time_val, label_val)
                added_rems.append(f"<code>{r['time']}</code> — {r['label']}")
        if added_rems:
            has_changes = True
            rems_formatted = "\n".join(added_rems)
            mentor_response = f"⏰ <b>Reminder Scheduled:</b>\n{rems_formatted}\n\nI will ping you right on time!"

    # --- DELETE REMINDER ---
    rem_to_del = data.get("reminder_to_delete")
    if rem_to_del:
        for r in list(user_data.get("reminders", [])):
            if str(r["id"]) == str(rem_to_del) or str(rem_to_del).lower() in r["label"].lower():
                stu.delete_reminder(user_data, r["id"])
                has_changes = True
                mentor_response = f"🗑 <b>Reminder Removed:</b> <i>{r['label']} ({r['time']})</i>"
                break

    # --- ADD GOAL ---
    goal_name = data.get("goal_name")
    goal_date = data.get("goal_date")
    if goal_name and goal_date:
        ok, msg = stu.add_goal(user_data, goal_name, goal_date)
        if ok:
            has_changes = True
            mentor_response = msg

    # --- DELETE GOAL ---
    goal_to_del = data.get("goal_to_delete")
    if goal_to_del:
        for g in list(user_data.get("goals", [])):
            if str(g["id"]) == str(goal_to_del) or str(goal_to_del).lower() in g["name"].lower():
                stu.delete_goal(user_data, g["id"])
                has_changes = True
                mentor_response = f"🗑 <b>Goal Removed:</b> <i>{g['name']}</i>"
                break

    # --- SET WEEKLY PRIORITY ---
    wp_val = data.get("weekly_priority")
    if wp_val:
        stu.set_weekly_priority(user_data, wp_val)
        has_changes = True
        mentor_response = f"📌 <b>Week Priority Locked:</b> <i>{wp_val}</i>\n\nEvery day's actions should align with this milestone."

    # --- START DEEP WORK ---
    dw_mins = data.get("deep_work_minutes")
    if dw_mins:
        dw_label = data.get("deep_work_label", "Deep Work Block")
        stu.start_deep_work(user_data, int(dw_mins), dw_label)
        has_changes = True
        mentor_response = f"⚡ <b>Deep Work Activated:</b> {dw_mins} minutes for <i>{dw_label}</i>.\n\nTurn off all notifications. I will ping you when your block ends!"

    # --- VIEW STATUS ---
    if intent == "view_status":
        return stu.format_morning_gameplan(user_data), has_changes

    return mentor_response, has_changes


def _get_welcome_text():
    return """👋 <b>Welcome to your AI Discipline & Accountability Mentor!</b>

🤖 <b>Created by Manoj Kuppala</b>

I am your 24/7 personal coach for <b>Goals, Daily Execution, and Focus</b>.

💬 <b>You don't need buttons — just talk to me naturally:</b>
• <i>"Remind me daily at 8:00 for DSA problems"</i>
• <i>"Add task: finish React authentication module"</i>
• <i>"Set goal: Crack MERN Job by 2026-10-30"</i>
• <i>"Completed task 1"</i>
• <i>"Starting 60 min deep work on Redux"</i>
• <i>"I'm procrastinating on my project"</i>

📅 <b>Your Daily Routine:</b>
• <b>08:30 AM</b> ➔ Morning Focus Gameplan
• <b>09:00 PM</b> ➔ Evening Accountability Review
• <b>10:30 PM</b> ➔ Night Planning for Tomorrow
• <b>Sunday 8 PM</b> ➔ Weekly Strategic Reflection

Let's win today. What is your #1 priority right now?"""
