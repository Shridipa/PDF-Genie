from flask_login import UserMixin
from datetime import datetime
from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    translations = db.relationship('Translation', backref='user', lazy=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Translation(db.Model):
    __tablename__ = 'translation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    original_name = db.Column(db.String(200), nullable=False)
    translated_name = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    notes = db.Column(db.Text)
    retranslate_reason = db.Column(db.Text)

    duration_seconds = db.Column(db.Float)

