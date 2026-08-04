from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import AdminUser
from app.services.github_service import get_users_from_github, save_users_to_github

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
    total_users = len(users)
    
    topic_counts = {}
    for chat_id, data in users.items():
        for topic in data.get("topics", []):
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    
    return render_template('admin/dashboard.html', total_users=total_users, topics=sorted_topics)

@admin_bp.route('/delete_users', methods=['POST'])
@login_required
def delete_users():
    users, sha = get_users_from_github()
    success = save_users_to_github({}, sha)
    if success:
        flash('Database successfully cleared!', 'success')
    else:
        flash('Failed to clear database.', 'error')
    return redirect(url_for('admin.dashboard'))
