from __future__ import annotations

import random
import string
from functools import wraps

import psycopg2.extras
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import DEFAULT_STUDENT_PASSWORD, get_db


bp = Blueprint("auth", __name__)


def _cursor():
    return get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _new_captcha() -> str:
    return "".join(random.choices(string.digits, k=5))


def _render_login(category: str | None = None, message: str | None = None):
    captcha_code = _new_captcha()
    session["captcha_code"] = captcha_code
    if message:
        flash(message, category or "warning")
    return render_template("login.html", captcha_code=captcha_code)


def _ensure_user(username: str, password: str, role: str, student_id: int | None = None):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    password_hash = generate_password_hash(password)

    if user:
        if not check_password_hash(user["password_hash"], password):
            cur.execute("UPDATE users SET password_hash=%s, role=%s WHERE id=%s", (password_hash, role, user["id"]))
            conn.commit()
        return user["id"]

    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s) RETURNING id",
        (username, password_hash, role),
    )
    user_id = cur.fetchone()["id"]
    if role == "student" and student_id is not None:
        cur.execute("UPDATE students SET user_id=%s WHERE id=%s", (user_id, student_id))
    conn.commit()
    return user_id


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Bạn không có quyền truy cập trang này.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return _render_login()

    captcha = request.form.get("captcha", "").strip()
    if captcha != session.get("captcha_code"):
        return _render_login("danger", "Mã xác nhận không đúng.")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    is_admin = request.form.get("is_admin") == "on" or username.lower() == "admin"

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if is_admin:
        cur.execute("SELECT * FROM users WHERE username=%s AND role='admin'", (username or "admin",))
        user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update({"user_id": user["id"], "username": user["username"], "full_name": user["username"], "role": "admin"})
            return redirect(url_for("admin.dashboard"))

        return _render_login("danger", "Tài khoản quản trị hoặc mật khẩu không đúng.")

    cur.execute(
        "SELECT s.*, u.id AS linked_user_id, u.password_hash AS linked_password_hash "
        "FROM students s LEFT JOIN users u ON u.id = s.user_id "
        "WHERE s.passport_number = %s OR u.username = %s",
        (username, username),
    )
    student = cur.fetchone()
    if not student:
        return _render_login("danger", "Không tìm thấy tài khoản sinh viên.")

    linked_user_id   = student.get("linked_user_id")
    linked_pw_hash   = student.get("linked_password_hash")

    # Block old generic shared defaults — never accepted
    OLD_SHARED = {"123@ktxquanly123", "123456", DEFAULT_STUDENT_PASSWORD}
    if password in OLD_SHARED:
        return _render_login("danger", "Mật khẩu sinh viên không đúng.")

    if linked_user_id and linked_pw_hash:
        # Accept only if password matches what is stored in DB
        # This covers: initial passport-number password, admin temp password, student's own password
        if check_password_hash(linked_pw_hash, password):
            user_id = linked_user_id
        else:
            return _render_login("danger", "Mật khẩu sinh viên không đúng.")
    else:
        # No account yet — must contact admin
        return _render_login("danger", "Tài khoản chưa được kích hoạt. Liên hệ quản lý.")

    session.clear()
    session.update({
        "user_id": user_id,
        "username": student["passport_number"],
        "full_name": student["full_name"],
        "role": "student",
    })
    return redirect(url_for("main.dashboard"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))