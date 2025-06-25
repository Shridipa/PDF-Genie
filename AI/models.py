from flask_login import UserMixin
from datetime import datetime
from AI import db, login_manager

class User(UserMixin, db.Model):
    """Represents a registered user."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ Add this
    translations = db.relationship('Translation', backref='user', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Translation(db.Model):
    """Stores information about each translated PDF."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_name = db.Column(db.String(200))
    translated_name = db.Column(db.String(200))
    language = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    retranslate_reason = db.Column(db.Text)

