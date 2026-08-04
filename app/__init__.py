from flask import Flask
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import Config

login_manager = LoginManager()
login_manager.login_view = 'admin.login'
scheduler = BackgroundScheduler()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import AdminUser
        return AdminUser.get(user_id)

    # Import and register blueprints
    from app.routes.bot_routes import bot_bp
    from app.routes.admin_routes import admin_bp

    app.register_blueprint(bot_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register scheduler job
    from app.services.scheduler_service import scheduled_job
    
    # Ensure scheduler is only started once (prevent duplicate jobs in debug mode)
    if not scheduler.running:
        scheduler.add_job(func=scheduled_job, trigger="cron", minute="*")
        scheduler.start()

    return app
