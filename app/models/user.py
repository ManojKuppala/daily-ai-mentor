from flask_login import UserMixin
from werkzeug.security import check_password_hash
from app.config import Config

class AdminUser(UserMixin):
    def __init__(self, id):
        self.id = id

    @staticmethod
    def get(user_id):
        if user_id == "admin":
            return AdminUser(user_id)
        return None

    @staticmethod
    def check_password(password):
        # In a real database, this would check a hash. For our simple admin panel, 
        # we check against the environment variable. 
        # Note: If ADMIN_PASSWORD is raw, we just do a string comparison.
        return password == Config.ADMIN_PASSWORD
