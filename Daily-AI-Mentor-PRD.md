# Product Requirements Document: Daily AI Mentor — Student Companion Upgrade

**Version:** 1.0
**Owner:** [Your name]
**Status:** Draft
**Last updated:** August 2026

---

## 1. Overview

Daily AI Mentor is currently a Telegram bot that delivers AI-summarized news briefings on a personalized schedule. This upgrade transforms it from a pure information feed into a **daily student companion** — combining news delivery with goal tracking, task management, routine reminders, progress visibility, and light motivational support.

The guiding principle: every new feature should feel like part of one coherent daily check-in, not a collection of bolted-on tools.

---

## 2. Problem Statement

Students using the bot today get news, but nothing that helps them act on their goals. There's no way to:
- Track how many days remain until an exam
- Plan and follow through on daily study tasks
- See whether they're actually making progress over time
- Get encouragement that reflects their real behavior, not generic quotes

This upgrade addresses all four gaps using a single daily interaction point (the briefing) as the anchor.

---

## 3. Goals

- Increase daily active usage by giving users a reason to open the bot beyond news (tasks, streaks, countdowns)
- Help users build consistent study habits through lightweight tracking, not heavy gamification
- Keep the "mentor" tone — supportive, data-driven, non-punitive — across every new feature
- Ship in independent, testable phases without touching the existing news pipeline

## 4. Non-Goals

- No social feed, public leaderboards, or competitive ranking
- No complex project-management-style to-do (subtasks, dependencies, priority matrices) — kept intentionally simple
- No push notifications outside Telegram's native messaging
- No monetization in this phase (may be considered later, separately)

---

## 5. Target User

Students preparing for competitive exams, board exams, or college coursework, already using the bot for news and looking for help staying consistent with study routines.

---

## 6. Feature Requirements

### 6.1 Goal & Deadline Tracking
- User can set one or more goals, each with a name and target date (e.g., "UPSC Prelims — 15 June 2026")
- Nearest upcoming goal's countdown is shown at the top of the daily briefing
- Countdown tone adapts by proximity: neutral (>30 days), gentle urgency (7–30 days), high urgency (<7 days)
- User can view, edit, or remove goals at any time

### 6.2 Routine Reminders
- User can set multiple reminder slots per day, independent of the news delivery time (e.g., "Physics — 6 PM")
- Each reminder can be marked done, skipped, or ignored (no action)
- A missed reminder (no response) is softly acknowledged in the next day's briefing, framed as an offer to reschedule — not a penalty
- Optional weekly view of the full routine schedule, sent once a week

### 6.3 To-Do List
- User can add, view, complete, and delete tasks
- Tasks can optionally be tagged to a goal (e.g., linked to "Semester Exam")
- Each morning, user is prompted to set up to 3 priority tasks for the day (capped intentionally to stay realistic)
- Recurring tasks supported (daily or weekly repeat)
- Incomplete tasks roll over to the next day, visibly marked as "carried over," without penalty

### 6.4 Progress System
- Daily completion rate tracked: tasks completed ÷ tasks planned
- Weekly summary shows completion rate trend vs. the previous week
- If tasks are tagged to a goal, progress is shown per goal/subject
- Two separate streaks tracked:
  - **Briefing streak** — consecutive days the news briefing was opened
  - **Task streak** — consecutive days with at least one completed task
- Milestone messages at meaningful points (e.g., 7-day streak, 30 tasks completed), kept low-key and consistent with the mentor tone

### 6.5 Motivation Layer
- Daily motivational line in the briefing, generated from the user's actual data (streak status, progress %, days to goal) rather than random quotes
- Weekly reflection message (e.g., sent Sunday evening): summarizes tasks completed, current streaks, and goal countdown, with one encouraging line
- No generic "quote of the day" — every motivational message ties back to the user's real activity

### 6.6 Daily Tech Quiz
- One multiple-choice tech question delivered daily, either appended to the news briefing or sent as a short separate message
- Instant right/wrong feedback with a one-line explanation on answer
- Separate quiz streak and lifetime correct-answer count tracked
- Weekly quiz performance folded into the existing weekly reflection message (no separate quiz recap)

### 6.7 Supporting Features (small additions)
- **Mood check-in**: one-tap emoji (🙂 😐 😔) before the briefing; low mood softens urgency framing that day
- **Skip today**: lets a user mark a task or reminder as intentionally skipped (planned rest), so it doesn't count against streaks the way a genuine miss would
- **Weekly top priority**: one big goal set for the week (e.g., "Finish Chapter 5"), surfaced daily as a small reminder alongside tasks
- **Study buddy pairing**: optional pairing of two users with similar goals; each can see the other's streak only (no scores, no ranking)
- **End-of-day one-line journal**: optional free-text reflection ("how did today go"), resurfaced in the weekly reflection for context

---

## 7. User Flows (high level)

**Daily flow:**
Mood check-in → Briefing (countdown + news + motivational line) → Tech quiz question → Today's 3 priority tasks prompt → Routine reminders through the day → End-of-day task check-in → Optional one-line journal

**Weekly flow:**
Sunday/Monday: Routine schedule overview → Sunday evening: Weekly reflection (completion rate, streaks, quiz performance, goal countdown, encouraging note)

---

## 8. Data Considerations

Each user profile will need to track, conceptually:
- Goals (name, target date)
- Routine reminders (time, label, status per day)
- Tasks (text, tag/goal link, recurrence, status, date)
- Streaks (briefing, task, quiz — tracked separately)
- Mood log (daily, lightweight)
- Quiz history (correct/incorrect count, streak)
- Study buddy pairing (optional, mutual opt-in)
- Journal entries (optional, free text)

No code or schema is specified here — this is a data scope reference for whoever implements storage.

---

## 9. Success Metrics

- % of users who set at least one goal within first week of upgrade
- Daily task completion rate (target: track and improve, not hit a fixed number initially)
- 7-day and 30-day retention comparison (before vs. after upgrade)
- Quiz answer rate (% of users who answer the daily question)
- Weekly reflection open/read rate

---

## 10. Rollout Plan

**Phase 1 — Foundation**
Goal/deadline countdown (single goal), basic to-do (add/view/complete/delete)

**Phase 2 — Routine layer**
Daily reminder slots, recurring tasks, task rollover

**Phase 3 — Progress layer**
Completion rate tracking, dual streaks (briefing + task), weekly summary

**Phase 4 — Motivation + Quiz**
Contextual daily motivational line, weekly reflection message, daily tech quiz with its own streak

**Phase 5 — Supporting features**
Mood check-in, skip-today, weekly top priority, study buddy pairing, end-of-day journal

**Phase 6 — Polish**
Multiple concurrent goals with nearest-deadline priority, per-goal progress breakdown

---

## 11. Risks & Open Questions

- **Notification fatigue**: multiple daily touchpoints (mood check-in, briefing, quiz, task prompts, reminders, end-of-day check-in) risk feeling like too much — may need a "compact mode" that bundles several into one message
- **Streak pressure**: need to keep tone supportive so streaks motivate rather than stress users out — skip-today feature is meant to offset this, should be monitored
- **Data storage scale**: current GitHub-based storage may need reevaluation once per-user data grows (goals, tasks, streaks, mood, journal, quiz history)
- **Open question**: should study buddy pairing be opt-in only, or suggested automatically based on similar goals?
- **Open question**: what happens to a user's data/streaks if they stop using the bot for an extended period — reset, pause, or keep indefinitely?

---

## 12. Out of Scope for This Version

- Multiple quiz questions per day
- Public leaderboards
- Payment/premium tiers
- Notifications outside Telegram
