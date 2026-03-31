"""
main.py — CRICSHOT Flask Route Layer
=====================================
All HTTP routes for the CRICSHOT prediction application.
Organised into five sections:
  1. Page Routes       — HTML template endpoints
  2. Auth API Routes   — Sign-up / Login / OTP / Reset
  3. Prediction Routes — Image / Video / Webcam frame
  4. Data Routes       — Stats / History / Activity
  5. Utility Routes    — Health check / Static assets

Run with:
  python main.py          # development (debug=True)
  gunicorn main:app       # production (Render)
"""

import os
import datetime
from flask import (Flask, request, jsonify,
                   render_template, send_from_directory,
                   session)
from flask_login  import login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

# ── Import shared app instance, db, models, helpers ─────────────────
# (defined in app.py — main.py is a clean route-only layer)
from app import (
    app, db, bcrypt,
    login_manager, mail,
    generate_otp, send_otp, log_activity,
    predict_frame,
    _check_anon_quota, _log_prediction, _allowed,
    get_or_create_anon_session,
    ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT,
    BASE_DIR, TEMPLATES_DIR, STATIC_DIR,
    JOBS_STORE, run_inference
)

# ════════════════════════════════════════════════════════════════════
#  1. PAGE ROUTES  (GET → render HTML templates)
# ════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Landing page — main app (index.html in project root)."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/login")
def page_login():
    """Login page with OTP and forgot-password flow."""
    return render_template("login.html")


@app.route("/register")
def page_register():
    """Registration page with 3-step OTP verification."""
    return render_template("register.html")


@app.route("/upload/image")
def page_upload_image():
    """Image upload page — drag-and-drop with live result panel."""
    return render_template("upload_image.html")


@app.route("/upload/video")
def page_upload_video():
    """Video upload page — XHR progress bar and frame analysis."""
    return render_template("upload_video.html")


@app.route("/shots")
def page_shot_library():
    """Shot Library — 18 shot types with YouTube tutorials."""
    return render_template("shot_library.html")


@app.route("/performance")
def page_performance():
    """Performance Metrics — live stats, history, personal analytics."""
    return render_template("performance.html")


# ════════════════════════════════════════════════════════════════════
#  2. AUTH API ROUTES  (JSON request / JSON response)
# ════════════════════════════════════════════════════════════════════

@app.route("/auth/signup", methods=["POST"])
def signup():
    """Register a new user and send email OTP for verification."""
    data     = request.json or {}
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    otp    = generate_otp()
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
    user   = User(
        name        = name,
        email       = email,
        mobile      = data.get("mobile"),
        fav_sport   = data.get("fav_sport"),
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8"),
        otp_code    = otp,
        otp_expiry  = expiry,
        is_verified = False,
    )
    db.session.add(user)
    db.session.commit()

    send_otp(user, otp)
    log_activity(user.id, "signup")
    return jsonify({"user_id": user.id, "message": "OTP sent to your email."})


@app.route("/auth/login", methods=["POST"])
def login():
    """Authenticate credentials and send OTP for two-factor verification."""
    data  = request.json or {}
    email = (data.get("email") or "").strip().lower()
    pw    = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, pw):
        return jsonify({"error": "Incorrect email or password."}), 401
    if not user.is_verified:
        return jsonify({"error": "Account not verified. Please complete OTP."}), 403

    otp    = generate_otp()
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
    user.otp_code   = otp
    user.otp_expiry = expiry
    db.session.commit()

    send_otp(user, otp)
    log_activity(user.id, "login_attempt")
    return jsonify({"type": "otp_required", "user_id": user.id})


@app.route("/auth/verify", methods=["POST"])
def verify():
    """Verify OTP and complete login / registration session."""
    from flask_login import login_user
    data    = request.json or {}
    user_id = data.get("user_id")
    otp     = str(data.get("otp", "")).strip()

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user ID."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    if user.otp_code != otp or user.otp_expiry < datetime.datetime.now():
        return jsonify({"error": "Invalid or expired OTP."}), 401

    user.is_verified = True
    user.otp_code    = None
    db.session.commit()
    login_user(user, remember=True)
    log_activity(user.id, "login_success")
    return jsonify({"message": "Login successful", "user": {"id": user.id, "name": user.name}})


@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    """Send OTP to reset forgotten password."""
    email = (request.json or {}).get("email", "").strip().lower()
    user  = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "No account found with this email."}), 404

    otp    = generate_otp()
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
    user.otp_code   = otp
    user.otp_expiry = expiry
    db.session.commit()
    send_otp(user, otp)
    log_activity(user.id, "forgot_password")
    return jsonify({"user_id": user.id, "message": "OTP sent."})


@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    """Verify OTP and update user password."""
    data     = request.json or {}
    user_id  = data.get("user_id")
    otp      = str(data.get("otp", "")).strip()
    new_pw   = data.get("password", "")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user ID."}), 400

    user = User.query.get(user_id)
    if not user or user.otp_code != otp or user.otp_expiry < datetime.datetime.now():
        return jsonify({"error": "Invalid or expired OTP."}), 401
    if len(new_pw) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    user.password_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
    user.otp_code      = None
    db.session.commit()
    log_activity(user.id, "password_reset")
    return jsonify({"message": "Password reset successful."})


@app.route("/auth/resend-otp", methods=["POST"])
def resend_otp():
    """Resend OTP to user (Resend button on OTP screen)."""
    user_id = (request.json or {}).get("user_id")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user ID."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    otp    = generate_otp()
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
    user.otp_code   = otp
    user.otp_expiry = expiry
    db.session.commit()
    send_otp(user, otp)
    log_activity(user.id, "otp_resent")
    return jsonify({"message": "OTP resent."})


@app.route("/auth/logout")
@login_required
def logout():
    """Log out current user session."""
    log_activity(current_user.id, "logout")
    logout_user()
    return jsonify({"message": "Logged out."})


@app.route("/auth/me")
def me():
    """Return currently authenticated user info (or null if anonymous)."""
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user": {"id": current_user.id, "name": current_user.name, "email": current_user.email}})
    return jsonify({"authenticated": False, "user": None})


# ════════════════════════════════════════════════════════════════════
#  3. PREDICTION ROUTES
# ════════════════════════════════════════════════════════════════════

@app.route("/predict/image", methods=["POST"])
def route_api_predict_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    file_bytes = file.read()

    job_id = str(uuid.uuid4())

    JOBS_STORE[job_id] = {
        "status": "processing",
        "result": None
    }

    import threading
    threading.Thread(
        target=run_inference,
        args=(job_id, file_bytes, "image"),
        daemon=True
    ).start()

    return jsonify({
        "job_id": job_id,
        "status": "processing"
    })


@app.route("/predict/video", methods=["POST"])
def route_api_predict_video():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    file_bytes = file.read()

    job_id = str(uuid.uuid4())

    JOBS_STORE[job_id] = {
        "status": "processing",
        "result": None
    }

    import threading
    threading.Thread(
        target=run_inference,
        args=(job_id, file_bytes, "video"),
        daemon=True
    ).start()

    return jsonify({
        "job_id": job_id,
        "status": "processing"
    })

@app.route("/predict/status/<job_id>")
def route_check_status(job_id):
    job = JOBS_STORE.get(job_id)

    if not job:
        return jsonify({"error": "Invalid job ID"}), 404

    return jsonify(job)


@app.route("/predict/frame", methods=["POST"])
def api_predict_frame():
    """Lightweight prediction from a single base64 webcam frame."""
    data = request.json or {}
    if "frame" not in data:
        return jsonify({"error": "No frame data provided."}), 400

    result = predict_frame(data["frame"])
    return jsonify(result), 200


# ════════════════════════════════════════════════════════════════════
#  4. DATA / ANALYTICS ROUTES
# ════════════════════════════════════════════════════════════════════

@app.route("/stats")
def public_stats():
    """Public platform statistics: totals, top shots, user count."""
    from sqlalchemy import func
    total  = Prediction.query.count()
    users  = User.query.filter_by(is_verified=True).count()
    anon   = Prediction.query.filter_by(user_id=None).count()
    top5   = (db.session.query(Prediction.shot_name, func.count(Prediction.id).label("n"))
              .group_by(Prediction.shot_name).order_by(func.count(Prediction.id).desc()).limit(5).all())

    return jsonify({
        "total_predictions":          total,
        "registered_users":           users,
        "anonymous_predictions":      anon,
        "authenticated_predictions":  total - anon,
        "top_shots": [{"shot": s, "count": c} for s, c in top5],
    })


@app.route("/user/history")
@login_required
def user_history():
    """Return the logged-in user's last 50 predictions."""
    preds = (Prediction.query
             .filter_by(user_id=current_user.id)
             .order_by(Prediction.created_at.desc())
             .limit(50).all())
    return jsonify({"predictions": [p.to_dict() for p in preds], "total": len(preds)})


@app.route("/user/activity")
@login_required
def user_activity():
    """Return recent auth/action activity log for the current user."""
    logs = (ActivityLog.query
            .filter_by(user_id=current_user.id)
            .order_by(ActivityLog.created_at.desc())
            .limit(20).all())
    return jsonify({"activity": [l.to_dict() for l in logs]})


@app.route("/shots-ref")
def shot_types():
    """Return reference data for all 18 recognised cricket shot types."""
    shots = ShotType.query.order_by(ShotType.name).all()
    return jsonify({"shots": [s.to_dict() for s in shots]})


# ════════════════════════════════════════════════════════════════════
#  5. UTILITY ROUTES
# ════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    """Lightweight health-check ping used by Render and monitoring."""
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }), 200 if db_ok else 503


@app.after_request
def security_headers(response):
    """Attach security headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]        = "SAMEORIGIN"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    return response


# ════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = not bool(os.environ.get("RENDER"))
    app.run(host="0.0.0.0", port=port, debug=debug)
