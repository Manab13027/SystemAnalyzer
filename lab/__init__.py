"""
SystemAnalyzer — CTF / Vulnerability Lab Blueprint
Routes: /lab/*
"""
import hashlib
import threading
from functools import wraps

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import db
from lab import docker_manager
from lab.challenges import CHALLENGES
from lab import scorer

lab_bp = Blueprint("lab", __name__, url_prefix="/lab")


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _current_user() -> dict:
    username = session.get("lab_user")
    if not username:
        return {}
    return db.lab_get_user(username)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("lab_user"):
            return redirect(url_for("lab.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _current_user()
        if not user or user.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("lab.dashboard"))
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────────────────────────

@lab_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.lab_get_user(username)
        if user and user["password_hash"] == _hash_password(password):
            session["lab_user"] = username
            return redirect(url_for("lab.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("lab_login.html")


@lab_bp.route("/logout")
def logout():
    session.pop("lab_user", None)
    return redirect(url_for("lab.login"))


@lab_bp.route("/register", methods=["GET", "POST"])
def register():
    # Only allow registration if no users exist yet (first-run setup)
    # or if admin is logged in
    user_count = len(db.lab_list_users())
    current = _current_user()
    is_admin = current.get("role") == "admin"

    if user_count > 0 and not is_admin:
        flash("Registration is closed. Ask an admin to create your account.", "info")
        return redirect(url_for("lab.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        role     = request.form.get("role", "player") if is_admin else "player"

        if not username or not password:
            flash("Username and password are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            # First user ever is automatically admin
            if user_count == 0:
                role = "admin"
            ok = db.lab_create_user(username, _hash_password(password), role)
            if ok:
                if not is_admin:
                    session["lab_user"] = username
                flash(f"Account created: {username} ({role})", "success")
                return redirect(url_for("lab.dashboard") if not is_admin else url_for("lab.admin_users"))
            else:
                flash("Username already taken.", "error")

    return render_template("lab_register.html", is_admin=is_admin)


# ── Main lab dashboard ────────────────────────────────────────────────────────

@lab_bp.route("/")
@login_required
def dashboard():
    user = _current_user()
    statuses = docker_manager.list_all_statuses()
    progress = scorer.get_user_progress(user["username"])
    scoreboard = db.lab_get_scoreboard()
    return render_template(
        "lab_dashboard.html",
        user=user,
        challenges=CHALLENGES,
        statuses=statuses,
        progress=progress,
        scoreboard=scoreboard,
        docker_available=docker_manager.DOCKER_AVAILABLE,
    )


# ── Challenge detail page ─────────────────────────────────────────────────────

@lab_bp.route("/challenge/<challenge>")
@login_required
def challenge_detail(challenge):
    cfg = CHALLENGES.get(challenge)
    if not cfg:
        flash("Challenge not found.", "error")
        return redirect(url_for("lab.dashboard"))

    user = _current_user()
    status = docker_manager.get_status(challenge)
    progress = scorer.get_user_progress(user["username"])
    session_info = db.lab_get_session(challenge)

    return render_template(
        "lab_challenge.html",
        user=user,
        challenge=challenge,
        cfg=cfg,
        status=status,
        progress=progress,
        session_info=session_info,
    )


# ── Container lifecycle API ───────────────────────────────────────────────────

@lab_bp.route("/start/<challenge>", methods=["POST"])
@login_required
def start(challenge):
    if challenge not in CHALLENGES:
        return jsonify({"error": "Unknown challenge"}), 404

    result = docker_manager.start_challenge(challenge)

    if result.get("status") == "running":
        pixel_id = f"lab-{challenge}"
        db.lab_upsert_session(challenge, result.get("container_id", ""), "running", pixel_id)

        # Auto-register target + trigger nmap in background
        cfg = CHALLENGES[challenge]
        _auto_register_lab_target(pixel_id, cfg["network_ip"], challenge)

    return jsonify(result)


@lab_bp.route("/stop/<challenge>", methods=["POST"])
@login_required
def stop(challenge):
    if challenge not in CHALLENGES:
        return jsonify({"error": "Unknown challenge"}), 404

    result = docker_manager.stop_challenge(challenge)
    db.lab_set_session_status(challenge, "stopped")
    return jsonify(result)


@lab_bp.route("/reset/<challenge>", methods=["POST"])
@login_required
def reset(challenge):
    if challenge not in CHALLENGES:
        return jsonify({"error": "Unknown challenge"}), 404

    result = docker_manager.reset_challenge(challenge)
    if result.get("status") == "running":
        pixel_id = f"lab-{challenge}"
        db.lab_upsert_session(challenge, result.get("container_id", ""), "running", pixel_id)
        cfg = CHALLENGES[challenge]
        _auto_register_lab_target(pixel_id, cfg["network_ip"], challenge)

    return jsonify(result)


@lab_bp.route("/status/<challenge>")
@login_required
def status(challenge):
    if challenge not in CHALLENGES:
        return jsonify({"error": "Unknown challenge"}), 404
    return jsonify(docker_manager.get_status(challenge))


# ── Flag submission ───────────────────────────────────────────────────────────

@lab_bp.route("/submit/<challenge>/<flag_key>", methods=["POST"])
@login_required
def submit_flag(challenge, flag_key):
    user = _current_user()
    flag_text = request.form.get("flag", "").strip()

    if not flag_text:
        return jsonify({"correct": False, "message": "No flag provided.", "points": 0})

    result = scorer.submit_flag(user["username"], challenge, flag_key, flag_text)
    return jsonify(result)


# ── Scoreboard ────────────────────────────────────────────────────────────────

@lab_bp.route("/scoreboard")
@login_required
def scoreboard():
    user = _current_user()
    board = db.lab_get_scoreboard()
    return render_template("lab_scoreboard.html", user=user, scoreboard=board)


# ── Admin: user management ────────────────────────────────────────────────────

@lab_bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    user = _current_user()
    users = db.lab_list_users()
    return render_template("lab_admin_users.html", user=user, users=users)


@lab_bp.route("/admin/users/delete/<username>", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(username):
    current = _current_user()
    if username == current["username"]:
        flash("Cannot delete your own account.", "error")
    else:
        db.lab_delete_user(username)
        flash(f"Deleted user: {username}", "success")
    return redirect(url_for("lab.admin_users"))


# ── Helper: register lab target in SystemAnalyzer ─────────────────────────────

def _auto_register_lab_target(pixel_id: str, ip: str, challenge: str):
    """
    Insert a hit record for the lab machine so it appears in the SystemAnalyzer
    dashboard, then trigger nmap in a background thread.
    """
    import app as main_app
    import db as main_db

    try:
        cfg = CHALLENGES[challenge]
        ua = f"Lab/{cfg['name']} (SystemAnalyzer Lab)"
        main_db.insert_hit(pixel_id, ip, ua, f"lab/{challenge}", "en", {})
    except Exception:
        pass

    def _bg_nmap():
        try:
            main_app._do_nmap_scan(pixel_id, ip)
        except Exception:
            pass

    threading.Thread(target=_bg_nmap, daemon=True).start()
