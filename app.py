"""
app.py
======
Flask API server for the CRICSHOT prediction system.

Database schema (SQLite via SQLAlchemy):
  - users              : Registered accounts
  - shot_types         : Reference table of 18 cricket shot types
  - predictions        : Every prediction request (logged, user or anonymous)
  - anonymous_sessions : Server-side free-prediction quota per browser session
  - activity_logs      : Audit trail for auth events
"""

import os
import sys
import uuid
import random
import datetime
import logging

# Force UTF-8 output on Windows so emoji/unicode in print() never crashes
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from dotenv import load_dotenv
from predict import predict_image, predict_video, predict_frame
import json

# Try to import Flask-Limiter for rate limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False

# Load environment variables
load_dotenv()

BASE_DIR = os.path.dirname(__file__)

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cricshot-secret-key-12345")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    # On Render the app dir is read-only; use /tmp for SQLite
    "sqlite:////tmp/cricshot.db" if os.getenv("RENDER") else "sqlite:///cricshot.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"timeout": 30},       # wait up to 30s for lock
    "pool_pre_ping": True,
}
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB
# Security: session cookie settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # Set True in production with HTTPS

# Mail Configuration
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME"))

mail = Mail(app)
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# Rate limiter (optional dependency)
if HAS_LIMITER:
    limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"],
                      storage_uri="memory://")
else:
    limiter = None

# Security headers middleware
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Enable WAL mode for concurrent read/write access (fixes "database is locked")
from sqlalchemy import event
from sqlalchemy.engine import Engine as _Engine

@event.listens_for(_Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    import sqlite3
    if isinstance(dbapi_conn, sqlite3.Connection):
        try:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()
        except sqlite3.OperationalError:
            pass  # DB locked by another app (e.g. DB Browser) — skip

FREE_PREDICTION_LIMIT = 3

# ═══════════════════════════════════════════════════════════════════════
#  DATABASE MODELS
# ═══════════════════════════════════════════════════════════════════════

class User(db.Model, UserMixin):
    """Registered users (email or mobile)."""
    __tablename__ = "users"

    id            = db.Column(db.Integer,     primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=True, index=True)
    mobile        = db.Column(db.String(20),  unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(128), nullable=True)
    is_verified   = db.Column(db.Boolean,     default=False)
    otp_code      = db.Column(db.String(6),   nullable=True)
    otp_expiry    = db.Column(db.DateTime,    nullable=True)
    created_at    = db.Column(db.DateTime,    default=datetime.datetime.utcnow)
    last_login    = db.Column(db.DateTime,    nullable=True)

    # Relationships
    predictions   = db.relationship("Prediction",  backref="user", lazy=True)
    activity_logs = db.relationship("ActivityLog", backref="user", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "email":      self.email,
            "mobile":     self.mobile,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class ShotType(db.Model):
    """Reference table: all recognised cricket shot types."""
    __tablename__ = "shot_types"

    id         = db.Column(db.Integer,     primary_key=True)
    name       = db.Column(db.String(80),  unique=True, nullable=False)
    tag        = db.Column(db.String(120), nullable=True)
    category   = db.Column(db.String(60),  nullable=True)
    difficulty = db.Column(db.String(30),  nullable=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "tag":        self.tag,
            "category":   self.category,
            "difficulty": self.difficulty,
        }


class Prediction(db.Model):
    """Every prediction request — authenticated or anonymous."""
    __tablename__ = "predictions"

    id               = db.Column(db.Integer,     primary_key=True)
    user_id          = db.Column(db.Integer,     db.ForeignKey("users.id"), nullable=True, index=True)
    session_token    = db.Column(db.String(64),  nullable=True, index=True)  # anonymous session
    shot_name        = db.Column(db.String(80),  nullable=False)
    confidence       = db.Column(db.Float,       nullable=False)
    file_type        = db.Column(db.String(10),  nullable=False)  # "image" | "video"
    frame_count      = db.Column(db.Integer,     nullable=True)   # video only
    frames_processed = db.Column(db.Integer,     nullable=True)   # video only
    ip_address       = db.Column(db.String(50),  nullable=True)
    created_at       = db.Column(db.DateTime,    default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id":               self.id,
            "shot_name":        self.shot_name,
            "confidence":       round(self.confidence * 100, 1),
            "file_type":        self.file_type,
            "frame_count":      self.frame_count,
            "frames_processed": self.frames_processed,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }


class AnonymousSession(db.Model):
    """Server-side quota tracker for unauthenticated (free) predictions."""
    __tablename__ = "anonymous_sessions"

    id               = db.Column(db.Integer,    primary_key=True)
    session_token    = db.Column(db.String(64), unique=True, nullable=False, index=True)
    prediction_count = db.Column(db.Integer,    default=0)
    created_at       = db.Column(db.DateTime,   default=datetime.datetime.utcnow)
    last_used        = db.Column(db.DateTime,   default=datetime.datetime.utcnow,
                                                onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "session_token":    self.session_token,
            "prediction_count": self.prediction_count,
            "limit":            FREE_PREDICTION_LIMIT,
            "remaining":        max(0, FREE_PREDICTION_LIMIT - self.prediction_count),
        }


class ActivityLog(db.Model):
    """Audit trail for authentication and key user events."""
    __tablename__ = "activity_logs"

    id         = db.Column(db.Integer,    primary_key=True)
    user_id    = db.Column(db.Integer,    db.ForeignKey("users.id"), nullable=True, index=True)
    event      = db.Column(db.String(60), nullable=False)   # e.g. "signup", "login", "otp_sent"
    ip_address = db.Column(db.String(50), nullable=True)
    detail     = db.Column(db.String(200), nullable=True)   # optional extra info
    created_at = db.Column(db.DateTime,   default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "event":      self.event,
            "detail":     self.detail,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════
#  SHOT TYPES SEED DATA
# ═══════════════════════════════════════════════════════════════════════

SHOT_SEED = [
    {"name": "Cover Drive",     "tag": "Attacking · Off Side · Front Foot", "category": "Attacking",    "difficulty": "Intermediate"},
    {"name": "Defensive",       "tag": "Defensive · Both Sides",            "category": "Defensive",    "difficulty": "Beginner"},
    {"name": "Down The Wicket", "tag": "Attacking · Spin Countering",       "category": "Attacking",    "difficulty": "Advanced"},
    {"name": "Flick",           "tag": "Attacking · Leg Side · Wristy",     "category": "Attacking",    "difficulty": "Intermediate"},
    {"name": "Hook",            "tag": "Attacking · Leg Side · Cross-Bat",  "category": "Attacking",    "difficulty": "Advanced"},
    {"name": "Late Cut",        "tag": "Attacking · Off Side · Delicate",   "category": "Attacking",    "difficulty": "Advanced"},
    {"name": "Lofted Legside",  "tag": "Attacking · Leg Side · Aerial",     "category": "Power",        "difficulty": "Intermediate"},
    {"name": "Lofted Offside",  "tag": "Attacking · Off Side · Aerial",     "category": "Power",        "difficulty": "Intermediate"},
    {"name": "Pull",            "tag": "Attacking · Leg Side · Cross-Bat",  "category": "Attacking",    "difficulty": "Intermediate"},
    {"name": "Reverse Sweep",   "tag": "Unconventional · Off Side",         "category": "Improvised",   "difficulty": "Expert"},
    {"name": "Scoop",           "tag": "Innovative · Fine Leg · Airborne",  "category": "Improvised",   "difficulty": "Expert"},
    {"name": "Square Cut",      "tag": "Attacking · Off Side · Back Foot",  "category": "Attacking",    "difficulty": "Intermediate"},
    {"name": "Straight Drive",  "tag": "Attacking · Straight · Textbook",   "category": "Attacking",    "difficulty": "Beginner"},
    {"name": "Sweep",           "tag": "Attacking · Leg Side · Spin",       "category": "Attacking",    "difficulty": "Intermediate"},
    {"name": "Upper Cut",       "tag": "Audacious · Off Side · Aerial",     "category": "Improvised",   "difficulty": "Expert"},
    {"name": "drive",           "tag": "Classical · Both Sides · Front Foot","category": "Attacking",   "difficulty": "Beginner"},
    {"name": "legglance-flick", "tag": "Touch Shot · Leg Side · Off the Hip","category": "Attacking",   "difficulty": "Intermediate"},
    {"name": "pullshot",        "tag": "Attacking · Leg Side · Power",       "category": "Power",       "difficulty": "Intermediate"},
]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def seed_shot_types():
    """Insert missing shot types into the database."""
    for s in SHOT_SEED:
        if not ShotType.query.filter_by(name=s["name"]).first():
            db.session.add(ShotType(**s))
    db.session.commit()


# Create DB tables and seed reference data
with app.app_context():
    db.create_all()
    seed_shot_types()


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "bmp", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "avi", "mov", "mkv", "wmv"}


def _allowed(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def log_activity(user_id, event, detail=None):
    try:
        entry = ActivityLog(user_id=user_id, event=event,
                            ip_address=get_client_ip(), detail=detail)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()  # DB might be locked


def get_or_create_anon_session():
    """Return (session_token, AnonymousSession) from cookie or create new one."""
    token = request.cookies.get("anon_session")
    if not token:
        token = str(uuid.uuid4())
    anon = AnonymousSession.query.filter_by(session_token=token).first()
    if not anon:
        anon = AnonymousSession(session_token=token, prediction_count=0)
        try:
            db.session.add(anon)
            db.session.commit()
        except Exception:
            db.session.rollback()
    return token, anon


def _send_email_otp(to_email: str, otp: str) -> bool:
    """Send OTP via SMTP2GO (or any SMTP). Reads credentials from environment."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_server = os.getenv("MAIL_SERVER", "mail.smtp2go.com")
    smtp_port   = int(os.getenv("MAIL_PORT", 587))
    username    = os.getenv("MAIL_USERNAME", "")
    password    = os.getenv("MAIL_PASSWORD", "")
    sender      = os.getenv("MAIL_DEFAULT_SENDER", username)

    if not username or not password:
        print(f"[EMAIL] Credentials not set — OTP not emailed (OTP = {otp})")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "CRICSHOT — Your Verification Code"
        msg["From"]    = f"CRICSHOT <{sender}>"
        msg["To"]      = to_email

        text_body = (
            f"Your CRICSHOT verification code is: {otp}\n\n"
            f"This code expires in 10 minutes.\n"
            f"If you did not request this, ignore this email."
        )
        html_body = f"""
        <div style="font-family:sans-serif;max-width:420px;margin:auto;
                    background:#0d1b2a;color:#e0e0e0;padding:32px;border-radius:12px;">
          <h2 style="color:#00e88a;margin:0 0 8px">CRICSHOT 🏏</h2>
          <p style="color:#aaa;margin:0 0 24px;font-size:13px">Verification Code</p>
          <div style="background:#1a2a3a;border-radius:8px;padding:24px;text-align:center;
                      letter-spacing:12px;font-size:36px;font-weight:bold;color:#00e88a;">
            {otp}
          </div>
          <p style="margin:20px 0 4px;font-size:13px;color:#aaa;">
            This code expires in <strong>10 minutes</strong>.
          </p>
          <p style="font-size:12px;color:#666;">
            If you didn't request this, you can safely ignore this email.
          </p>
        </div>"""

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()  # required after STARTTLS
            server.login(username, password)
            server.send_message(msg)

        print(f"[EMAIL] OTP sent successfully to {to_email}")
        return True

    except Exception as e:
        print(f"[EMAIL] FAILED to send OTP to {to_email}: {e}")
        return False


def _send_sms_otp(to_number: str, otp: str) -> bool:
    """Send OTP via Twilio SMS. Reads credentials from environment."""
    account_sid   = os.getenv("TWI_ACCOUNT_SID", "")
    auth_token    = os.getenv("TWI_AUTH_TOKEN", "")
    twilio_number = os.getenv("TWI_PHONE_NUMBER", "")

    if not account_sid or not auth_token or not twilio_number:
        print(f"[SMS] Twilio credentials not set — OTP not sent via SMS (OTP = {otp})")
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"Your CRICSHOT verification code is: {otp}. Valid for 10 minutes.",
            from_=twilio_number,
            to=to_number
        )
        print(f"[SMS] OTP sent successfully to {to_number}")
        return True
    except ImportError:
        print("[SMS] twilio package not installed. Run: pip install twilio")
        return False
    except Exception as e:
        print(f"[SMS] FAILED to send OTP via SMS: {e}")
        return False


def send_otp(user, otp):
    """Route OTP delivery: email -> SMTP2GO, mobile -> Twilio. Falls back to console."""
    try:
        print(f"[OTP] Sending to: {user.email or user.mobile} | code: {otp}")
    except Exception:
        pass  # console encoding issue, non-fatal

    delivered = False
    if user.email:
        delivered = _send_email_otp(user.email, otp)
    elif user.mobile:
        delivered = _send_sms_otp(user.mobile, otp)

    if not delivered:
        try:
            print(f"[OTP] Fallback console delivery: code={otp}")
        except Exception:
            pass
    return True


# ═══════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/auth/status")
def auth_status():
    if current_user.is_authenticated:
        return jsonify({
            "is_logged_in": True,
            "user": {
                "email":      current_user.email,
                "mobile":     current_user.mobile,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            }
        })
    # Return anonymous quota
    try:
        token, anon = get_or_create_anon_session()
        resp = jsonify({"is_logged_in": False, "anon": anon.to_dict()})
        resp.set_cookie("anon_session", token, max_age=60*60*24*30, samesite="Lax")
        return resp
    except Exception:
        db.session.rollback()
        return jsonify({"is_logged_in": False, "anon": {"prediction_count": 0, "limit": FREE_PREDICTION_LIMIT}})


@app.route("/auth/signup", methods=["POST"])
def signup():
    data     = request.json
    email    = data.get("email")
    mobile   = data.get("mobile")
    password = data.get("password")

    if not email and not mobile:
        return jsonify({"error": "Email or Mobile required"}), 400
    if email and User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    if mobile and User.query.filter_by(mobile=mobile).first():
        return jsonify({"error": "Mobile already registered"}), 400

    user = User(
        email=email,
        mobile=mobile,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8") if password else None,
        is_verified=False
    )
    otp = generate_otp()
    user.otp_code  = otp
    user.otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)

    db.session.add(user)
    db.session.commit()

    log_activity(user.id, "signup", detail=email or mobile)
    log_activity(user.id, "otp_sent", detail=f"channel={'email' if email else 'sms'}")
    send_otp(user, otp)

    return jsonify({"message": "OTP sent", "user_id": user.id, "otp_debug": otp})


@app.route("/auth/login", methods=["POST"])
def login():
    data     = request.json
    email    = data.get("email")
    mobile   = data.get("mobile")
    password = data.get("password")
    user     = None

    if email:
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash and bcrypt.check_password_hash(user.password_hash, password):
            otp = generate_otp()
            user.otp_code   = otp
            user.otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
            db.session.commit()
            log_activity(user.id, "otp_sent", detail="login flow")
            send_otp(user, otp)
            return jsonify({"message": "OTP sent", "user_id": user.id,
                            "type": "otp_required", "otp_debug": otp})
        else:
            return jsonify({"error": "Invalid email or password"}), 401

    elif mobile:
        user = User.query.filter_by(mobile=mobile).first()
        if not user:
            user = User(mobile=mobile, is_verified=False)
            db.session.add(user)
        otp = generate_otp()
        user.otp_code   = otp
        user.otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
        db.session.commit()
        log_activity(user.id, "otp_sent", detail="mobile login")
        send_otp(user, otp)
        return jsonify({"message": "OTP sent", "user_id": user.id,
                        "type": "otp_required", "otp_debug": otp})

    return jsonify({"error": "Missing credentials"}), 400


@app.route("/auth/verify", methods=["POST"])
def verify():
    data    = request.json
    user_id = data.get("user_id")
    otp     = str(data.get("otp")).strip()

    try:
        user_id = int(str(user_id))
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    now = datetime.datetime.now()
    if user.otp_code == otp and user.otp_expiry > now:
        user.is_verified = True
        user.otp_code    = None
        user.last_login  = now
        db.session.commit()
        login_user(user, remember=True)
        log_activity(user.id, "login", detail="otp_verified")
        return jsonify({"message": "Login successful",
                        "email": user.email, "mobile": user.mobile})

    print(f"FAILED VERIFY: user={user.id} stored='{user.otp_code}' sent='{otp}'")
    return jsonify({"error": "Invalid or expired OTP"}), 401


@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    data   = request.json
    email  = data.get("email")
    mobile = data.get("mobile")
    user   = None

    if email:
        user = User.query.filter_by(email=email).first()
    elif mobile:
        user = User.query.filter_by(mobile=mobile).first()

    if user:
        otp = generate_otp()
        user.otp_code   = otp
        user.otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
        db.session.commit()
        log_activity(user.id, "otp_sent", detail="password_reset")
        send_otp(user, otp)
        return jsonify({"message": "Reset OTP sent", "user_id": user.id, "otp_debug": otp})

    return jsonify({"error": "User not found"}), 404


@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data         = request.json
    user_id      = data.get("user_id")
    otp          = str(data.get("otp")).strip()
    new_password = data.get("password")

    try:
        user_id = int(str(user_id))
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400

    user = User.query.get(user_id)
    if user and user.otp_code == otp and user.otp_expiry > datetime.datetime.now():
        user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        user.otp_code = None
        db.session.commit()
        log_activity(user.id, "password_reset")
        return jsonify({"message": "Password reset successful"})

    return jsonify({"error": "Invalid or expired OTP"}), 401


@app.route("/auth/logout")
@login_required
def logout():
    log_activity(current_user.id, "logout")
    logout_user()
    return jsonify({"message": "Logged out"})


# ═══════════════════════════════════════════════════════════════════════
#  PREDICTION ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


def _check_anon_quota():
    """Return (allowed, response) for anonymous users. allowed=True if under limit."""
    if current_user.is_authenticated:
        return True, None
    token, anon = get_or_create_anon_session()
    if anon.prediction_count >= FREE_PREDICTION_LIMIT:
        return False, (jsonify({
            "error": "free_limit_reached",
            "message": f"You have used all {FREE_PREDICTION_LIMIT} free predictions. Please sign in."
        }), 403)
    return True, None


def _log_prediction(result: dict, file_type: str, session_token: str = None):
    """Persist a Prediction row after a successful inference."""
    try:
        pred = Prediction(
            user_id          = current_user.id if current_user.is_authenticated else None,
            session_token    = None if current_user.is_authenticated else session_token,
            shot_name        = result.get("shot", "Unknown"),
            confidence       = result.get("confidence", 0.0),
            file_type        = file_type,
            frame_count      = result.get("frame_count"),
            frames_processed = result.get("frames_processed"),
            ip_address       = get_client_ip(),
        )
        db.session.add(pred)

        # Increment anonymous quota
        if not current_user.is_authenticated and session_token:
            anon = AnonymousSession.query.filter_by(session_token=session_token).first()
            if anon:
                anon.prediction_count += 1
                anon.last_used = datetime.datetime.utcnow()

        db.session.commit()
    except Exception:
        db.session.rollback()  # DB might be locked — prediction still returns


@app.route("/predict/image", methods=["POST"])
def api_predict_image():
    allowed, err = _check_anon_quota()
    if not allowed:
        return err

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400
    if not _allowed(file.filename, ALLOWED_IMAGE_EXT):
        return jsonify({"error": "Unsupported image format."}), 400

    result = predict_image(file.read())

    try:
        token, _ = get_or_create_anon_session()
        _log_prediction(result, "image", session_token=token)
        resp = jsonify(result)
        resp.set_cookie("anon_session", token, max_age=60*60*24*30, samesite="Lax")
        return resp, 200
    except Exception:
        db.session.rollback()
        return jsonify(result), 200  # return prediction even if DB logging fails


@app.route("/predict/video", methods=["POST"])
def api_predict_video():
    allowed, err = _check_anon_quota()
    if not allowed:
        return err

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400
    if not _allowed(file.filename, ALLOWED_VIDEO_EXT):
        return jsonify({"error": "Unsupported video format."}), 400

    result = predict_video(file.read())

    try:
        token, _ = get_or_create_anon_session()
        _log_prediction(result, "video", session_token=token)
        resp = jsonify(result)
        resp.set_cookie("anon_session", token, max_age=60*60*24*30, samesite="Lax")
        return resp, 200
    except Exception:
        db.session.rollback()
        return jsonify(result), 200


# ═══════════════════════════════════════════════════════════════════════
#  DATA / ANALYTICS ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/user/history")
@login_required
def user_history():
    """Return the authenticated user's prediction history."""
    preds = (Prediction.query
             .filter_by(user_id=current_user.id)
             .order_by(Prediction.created_at.desc())
             .limit(50)
             .all())
    return jsonify({"predictions": [p.to_dict() for p in preds], "total": len(preds)})


@app.route("/stats")
def stats():
    """Public stats: total predictions, top shots, registered users."""
    total_preds  = Prediction.query.count()
    total_users  = User.query.filter_by(is_verified=True).count()
    anon_preds   = Prediction.query.filter_by(user_id=None).count()
    auth_preds   = total_preds - anon_preds

    # Top 5 most predicted shots
    from sqlalchemy import func
    top_shots = (db.session.query(Prediction.shot_name,
                                  func.count(Prediction.id).label("count"))
                 .group_by(Prediction.shot_name)
                 .order_by(func.count(Prediction.id).desc())
                 .limit(5)
                 .all())

    return jsonify({
        "total_predictions":        total_preds,
        "authenticated_predictions": auth_preds,
        "anonymous_predictions":    anon_preds,
        "registered_users":         total_users,
        "top_shots": [{"shot": s, "count": c} for s, c in top_shots],
    })


@app.route("/shots")
def shot_types():
    """Return reference table of all 18 recognised cricket shot types."""
    shots = ShotType.query.order_by(ShotType.name).all()
    return jsonify({"shots": [s.to_dict() for s in shots]})


@app.route("/user/activity")
@login_required
def user_activity():
    """Return the current user's recent activity log."""
    logs = (ActivityLog.query
            .filter_by(user_id=current_user.id)
            .order_by(ActivityLog.created_at.desc())
            .limit(20)
            .all())
    return jsonify({"activity": [l.to_dict() for l in logs]})


# ═══════════════════════════════════════════════════════════════════════
#  PILLAR 1: REAL-TIME WEBCAM PREDICTION
# ═══════════════════════════════════════════════════════════════════════

@app.route("/predict/frame", methods=["POST"])
def api_predict_frame():
    """Lightweight prediction from a single base64 frame (for webcam)."""
    data = request.json
    if not data or "frame" not in data:
        return jsonify({"error": "No frame data provided."}), 400

    result = predict_frame(data["frame"])
    return jsonify(result), 200


# ═══════════════════════════════════════════════════════════════════════
#  PILLAR 3: PERFORMANCE METRICS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/metrics")
def metrics():
    """Return model confusion matrix, classification report, and confusion analysis."""
    model_dir = os.path.join(BASE_DIR, "model")
    result = {}

    # Confusion matrix
    cm_path = os.path.join(model_dir, "confusion_matrix.json")
    if os.path.exists(cm_path):
        with open(cm_path) as f:
            result["confusion_matrix"] = json.load(f)

    # Classification report
    cr_path = os.path.join(model_dir, "classification_report.json")
    if os.path.exists(cr_path):
        with open(cr_path) as f:
            result["classification_report"] = json.load(f)

    # Confusion analysis (why shots get confused)
    ca_path = os.path.join(BASE_DIR, "confusion_analysis.json")
    if os.path.exists(ca_path):
        with open(ca_path) as f:
            result["confusion_analysis"] = json.load(f)

    # Confusion matrix heatmap as base64 image
    heatmap_path = os.path.join(model_dir, "confusion_matrix.png")
    if os.path.exists(heatmap_path):
        import base64
        with open(heatmap_path, "rb") as f:
            result["heatmap_base64"] = "data:image/png;base64," + base64.b64encode(f.read()).decode()

    if not result:
        return jsonify({"error": "No metrics available. Run train_model.py first."}), 404

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
