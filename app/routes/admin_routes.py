from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import AdminUser
from app.config import Config
from app.services.github_service import (
    get_users_from_github, save_users_to_github, 
    delete_single_user, update_user_status, normalize_users
)
from app.services.telegram_service import send_news_with_logging
from app.services.news_service import generate_news
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
    
    # Topic counts (deduplicated by canonical name)
    topic_counts = {}
    total_topic_subs = 0
    for chat_id, data in users.items():
        for topic in data.get("topics", []):
            # Normalize: strip emoji prefix for dedup key
            canonical = topic
            for emoji in ["💻", "🚀", "📈", "🔬", "🧠", "🌍", "🏏"]:
                canonical = canonical.replace(emoji, "").strip()
            if canonical not in topic_counts:
                topic_counts[canonical] = {"display": topic, "count": 0}
            topic_counts[canonical]["count"] += 1
            total_topic_subs += 1
    
    sorted_topics = sorted(topic_counts.values(), key=lambda x: x["count"], reverse=True)
    
    # Compute stats
    active_users = sum(1 for u in users.values() if u.get("status") != "paused")
    avg_topics = round(total_topic_subs / total_users, 1) if total_users > 0 else 0
    sent_today = delivery_log_service.get_today_count()
    
    # Prepare user list for table
    user_list = []
    for chat_id, data in users.items():
        user_list.append({
            "chat_id": chat_id,
            "topics": data.get("topics", []),
            "status": data.get("status", "active"),
            "joined_at": data.get("joined_at", "Unknown"),
            "time": data.get("time", "08:00"),
        })
    user_list.sort(key=lambda x: x["joined_at"], reverse=True)
    
    # Delivery logs
    logs, log_total = delivery_log_service.get_logs(limit=50)
    
    return render_template('admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        sent_today=sent_today,
        avg_topics=avg_topics,
        topics=sorted_topics,
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
        user_topics = users[chat_id].get("topics", [])
        news = generate_news(user_topics)
        success = send_news_with_logging(chat_id, user_topics, news)
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
