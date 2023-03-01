from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(
        db.Integer, primary_key=True
    )
    password = db.Column(db.String(25))
    username = db.Column(db.String(25), unique=True)
    role = db.Column(db.String(10))
