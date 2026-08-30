from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import AdminUser
from app.config import Config
from app.services.github_service import (
    get_users_from_github, save_users_to_github, 
    delete_single_user, update_user_status, normalize_users
)
from app.services.telegram_service import send_briefing_with_logging
from app.services import student_service as stu
from app.services import delivery_log_service

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = AdminUser.get(username)
        if user and AdminUser.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@login_required
def dashboard():
    users, sha = get_users_from_github()
    users = normalize_users(users)
    total_users = len(users)
    
    # Compute mentor stats
    active_users = sum(1 for u in users.values() if u.get("status") != "paused")
    total_goals = sum(len(stu.get_goals(u)) for u in users.values())
    total_tasks = sum(len(stu.get_pending_tasks(u)) for u in users.values())
    sent_today = delivery_log_service.get_today_count()
    
    # Prepare user list for table
    user_list = []
    for chat_id, data in users.items():
        u = stu.ensure_student_fields(data)
        user_list.append({
            "chat_id": chat_id,
            "goals_count": len(stu.get_goals(u)),
            "tasks_count": len(stu.get_pending_tasks(u)),
            "reminders_count": len(u.get("reminders", [])),
            "status": u.get("status", "active"),
            "joined_at": u.get("joined_at", "Unknown"),
            "time": u.get("time", "08:30"),
        })
    user_list.sort(key=lambda x: x["joined_at"], reverse=True)
    
    # Delivery logs
    logs, log_total = delivery_log_service.get_logs(limit=50)
    
    return render_template('admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        total_goals=total_goals,
        total_tasks=total_tasks,
        sent_today=sent_today,
        user_list=user_list,
        logs=logs,
        log_total=log_total,
        config=Config
    )

# --- API ENDPOINTS ---

@admin_bp.route('/api/users/<chat_id>/pause', methods=['POST'])
@login_required
def pause_user(chat_id):
    success = update_user_status(chat_id, "paused")
    return jsonify({"success": success, "status": "paused"})

@admin_bp.route('/api/users/<chat_id>/resume', methods=['POST'])
@login_required
def resume_user(chat_id):
    success = update_user_status(chat_id, "active")
    return jsonify({"success": success, "status": "active"})

@admin_bp.route('/api/users/<chat_id>/delete', methods=['POST'])
@login_required
def delete_user(chat_id):
    success = delete_single_user(chat_id)
    return jsonify({"success": success})

@admin_bp.route('/api/users/<chat_id>/resend', methods=['POST'])
@login_required
def resend_user(chat_id):
    users, sha = get_users_from_github()
    if chat_id in users:
        user = stu.ensure_student_fields(users[chat_id])
        gameplan = stu.format_morning_gameplan(user)
        success = send_briefing_with_logging(chat_id, gameplan)
        return jsonify({"success": success})
    return jsonify({"success": False, "error": "User not found"}), 404

@admin_bp.route('/api/delete_all', methods=['POST'])
@login_required
def delete_all_users():
    confirmation = request.json.get("confirmation", "")
    if confirmation != "DELETE":
        return jsonify({"success": False, "error": "Invalid confirmation"}), 400
    users, sha = get_users_from_github()
    success = save_users_to_github({}, sha)
    return jsonify({"success": success})

@admin_bp.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    limit = 50
    offset = (page - 1) * limit
    logs, total = delivery_log_service.get_logs(limit=limit, offset=offset, status_filter=status_filter)
    return jsonify({"logs": logs, "total": total, "page": page})
