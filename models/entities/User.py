from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin):

    def __init__(self, user_id, username, password, fullname="") -> None:
        self.user_id = user_id
        self.username = username
        self.password = password
        self.fullname = fullname

    def get_id(self):
        return str(self.user_id)

    @staticmethod
    def check_password(hashed_password, password):
        return check_password_hash(hashed_password, password)

