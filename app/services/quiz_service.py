"""Daily tech quiz service using Groq AI."""

import os
import json
import threading
from datetime import datetime, timezone, timedelta
from openai import OpenAI
from app.services.student_service import update_streak, ensure_student_fields

IST = timezone(timedelta(hours=5, minutes=30))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
) if GROQ_API_KEY else None

# Cache today's quiz to avoid regeneration
_quiz_cache = {"date": None, "quiz": None}
_cache_lock = threading.Lock()


def generate_daily_quiz():
    """Generate a single tech MCQ for today, cached per day."""
    today = datetime.now(IST).strftime("%Y-%m-%d")
    
    with _cache_lock:
        if _quiz_cache["date"] == today and _quiz_cache["quiz"]:
            return _quiz_cache["quiz"]
    
    if not client:
        return _fallback_quiz()
    
    prompt = """Generate exactly ONE multiple-choice tech/science quiz question suitable for a student.

Return ONLY valid JSON in this exact format, nothing else:
{
    "question": "What does CPU stand for?",
    "options": ["Central Processing Unit", "Central Program Utility", "Computer Personal Unit", "Central Peripheral Unit"],
    "correct": 0,
    "explanation": "CPU stands for Central Processing Unit, the primary component that processes instructions in a computer."
}

Rules:
- The question should be about technology, computer science, or general science
- Exactly 4 options, one correct
- "correct" is the 0-based index of the right answer
- Keep explanation to 1-2 sentences
- Make it educational but not too easy
- Vary topics: AI, networking, programming, physics, space, biology, etc."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a quiz generator. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=300
        )
        raw = response.choices[0].message.content.strip()
        
        # Clean up potential markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        
        quiz = json.loads(raw)
        
        # Validate structure
        assert "question" in quiz
        assert "options" in quiz and len(quiz["options"]) == 4
        assert "correct" in quiz and 0 <= quiz["correct"] <= 3
        assert "explanation" in quiz
        
        with _cache_lock:
            _quiz_cache["date"] = today
            _quiz_cache["quiz"] = quiz
        
        return quiz
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return _fallback_quiz()


def _fallback_quiz():
    """Return a random fallback quiz when AI generation is unavailable."""
    import random
    fallbacks = [
        {
            "question": "What programming language is known as the 'language of the web'?",
            "options": ["Python", "JavaScript", "Java", "C++"],
            "correct": 1,
            "explanation": "JavaScript is the primary language for web development, running in browsers to create interactive web experiences."
        },
        {
            "question": "What does RAM stand for in computing?",
            "options": ["Random Access Memory", "Read And Modify", "Rapid Application Memory", "Run Access Mode"],
            "correct": 0,
            "explanation": "RAM stands for Random Access Memory, a type of volatile memory that stores data temporarily while programs are running."
        },
        {
            "question": "Which planet is known as the Red Planet?",
            "options": ["Venus", "Jupiter", "Mars", "Saturn"],
            "correct": 2,
            "explanation": "Mars appears red due to iron oxide (rust) on its surface, earning it the nickname 'Red Planet'."
        },
        {
            "question": "What does HTML stand for?",
            "options": ["Hyper Text Markup Language", "High Tech Modern Language", "Hyper Transfer Machine Language", "Home Tool Markup Language"],
            "correct": 0,
            "explanation": "HTML stands for HyperText Markup Language, the standard markup language for creating web pages."
        },
    ]
    return random.choice(fallbacks)


def format_quiz_question(quiz):
    """Format quiz for Telegram display."""
    if not quiz:
        return "⚠️ Quiz unavailable right now. Try again later!"
    
    labels = ["A", "B", "C", "D"]
    lines = [
        "🧠 <b>Daily Tech Quiz</b>\n",
        f"<i>{quiz['question']}</i>\n",
    ]
    for i, opt in enumerate(quiz["options"]):
        lines.append(f"  {labels[i]}. {opt}")
    
    return "\n".join(lines)


def get_quiz_keyboard():
    """Return inline keyboard for quiz answers."""
    return {
        "inline_keyboard": [
            [
                {"text": "A", "callback_data": "quiz_0"},
                {"text": "B", "callback_data": "quiz_1"},
                {"text": "C", "callback_data": "quiz_2"},
                {"text": "D", "callback_data": "quiz_3"},
            ]
        ]
    }


def check_answer(user_data, answer_index):
    """Check quiz answer. Returns (is_correct, feedback_message)."""
    user_data = ensure_student_fields(user_data)
    quiz = generate_daily_quiz()
    if not quiz:
        return False, "Quiz not available."
    
    labels = ["A", "B", "C", "D"]
    correct_idx = quiz["correct"]
    is_correct = (answer_index == correct_idx)
    
    user_data["quiz"]["attempted"] += 1
    if is_correct:
        user_data["quiz"]["correct"] += 1
    
    # Update quiz streak
    milestone = update_streak(user_data, "quiz")
    
    if is_correct:
        msg = f"✅ <b>Correct!</b> The answer is {labels[correct_idx]}.\n\n💡 {quiz['explanation']}"
        stats = user_data["quiz"]
        msg += f"\n\n📊 Score: {stats['correct']}/{stats['attempted']}"
    else:
        msg = f"❌ <b>Wrong.</b> The correct answer was <b>{labels[correct_idx]}. {quiz['options'][correct_idx]}</b>\n\n💡 {quiz['explanation']}"
        stats = user_data["quiz"]
        msg += f"\n\n📊 Score: {stats['correct']}/{stats['attempted']}"
    
    if milestone:
        msg += f"\n\n{milestone}"
    
    return is_correct, msg
