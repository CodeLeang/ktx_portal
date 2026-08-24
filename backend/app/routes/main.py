from datetime import date
import os
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.auth import login_required
from app import models

bp = Blueprint("main", __name__)


def _get_student():
    """Helper: fetch student row from session, trying by id then by user_id."""
    student = models.get_student_by_user_id(session["user_id"])
    if not student:
        student = models.get_student_by_id(session["user_id"])
    return student


@bp.route("/")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = _get_student()
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"]) if student else None
    period = date.today().strftime("%Y-%m")
    bills = models.get_current_bills(room["id"], period) if room else {}
    roommates = models.get_roommates(student["id"], room["id"]) if room else []
    messages = models.get_messages(student["id"])
    reports  = models.get_reports_for_student(student["id"])
    new_replies = [r for r in reports if r["admin_reply"] and r["status"] != "resolved"]
    session["report_replies"] = len(new_replies)

    # ── Financial summary ──
    total_bills_due = 0
    for bill in bills.values():
        total_bills_due += bill.get('amount_due', 0)

    scholarship = student.get('scholarship_amt', 0)
    needs_payment = total_bills_due > scholarship
    extra_payment = total_bills_due - scholarship if needs_payment else 0
    net_scholarship = max(0, scholarship - total_bills_due)

    return render_template("dashboard.html",
                           student=student,
                           room=room,
                           bills=bills,
                           roommates=roommates,
                           messages=messages,
                           period=period,
                           reports=reports,
                           new_replies=new_replies,
                           total_bills_due=total_bills_due,
                           net_scholarship=net_scholarship,
                           needs_payment=needs_payment,
                           extra_payment=extra_payment)


@bp.route("/profile")
@login_required
def profile():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = _get_student()
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    return render_template("profile.html", student=student)


@bp.route("/rules")
@login_required
def rules():
    return render_template("rules.html")


@bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    from werkzeug.security import check_password_hash
    from app import DEFAULT_STUDENT_PASSWORD
    from app.models import _cursor

    current = request.form.get("current_password", "").strip()
    new_pw  = request.form.get("new_password",  "").strip()
    confirm = request.form.get("confirm_password", "").strip()

    if len(new_pw) < 6:
        flash("Mật khẩu mới phải có ít nhất 6 ký tự.", "danger")
        return redirect(url_for("main.profile"))

    if new_pw != confirm:
        flash("Xác nhận mật khẩu không khớp.", "danger")
        return redirect(url_for("main.profile"))

    student = _get_student()
    if not student or not student.get("user_id"):
        flash("Không tìm thấy tài khoản.", "danger")
        return redirect(url_for("main.profile"))

    linked_user_id = student["user_id"]

    cur = _cursor()
    cur.execute("SELECT password_hash FROM users WHERE id=%s", (linked_user_id,))
    user_row = cur.fetchone()

    if not user_row:
        flash("Không tìm thấy tài khoản.", "danger")
        return redirect(url_for("main.profile"))

    if current != DEFAULT_STUDENT_PASSWORD and not check_password_hash(user_row["password_hash"], current):
        flash("Mật khẩu hiện tại không đúng.", "danger")
        return redirect(url_for("main.profile"))

    models.change_password(linked_user_id, new_pw)
    flash("Đã đổi mật khẩu thành công! Vui lòng đăng nhập lại.", "success")
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/upload-avatar", methods=["POST"])
@login_required
def upload_avatar():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    file = request.files.get("avatar")
    if not file or file.filename == "":
        flash("Vui lòng chọn ảnh.", "danger")
        return redirect(url_for("main.profile"))

    # Validate file type
    allowed = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        flash("Chỉ chấp nhận ảnh PNG, JPG, GIF, WEBP.", "danger")
        return redirect(url_for("main.profile"))

    # Validate file size (max 5 MB)
    MAX_AVATAR_BYTES = 5 * 1024 * 1024
    file.stream.seek(0, 2)  # seek to end
    file_size = file.stream.tell()
    file.stream.seek(0)  # reset for the later .save() call
    if file_size > MAX_AVATAR_BYTES:
        flash("Kích thước ảnh vượt quá 5 MB. Vui lòng chọn ảnh nhỏ hơn.", "danger")
        return redirect(url_for("main.profile"))

    # Get correct student row (students.id, NOT users.id)
    student = _get_student()
    if not student:
        flash("Không tìm thấy tài khoản.", "danger")
        return redirect(url_for("main.profile"))

    student_id = student["id"]

    # Save file to frontend/static/uploads/avatars/
    from pathlib import Path
    upload_dir = Path(__file__).resolve().parents[3] / "frontend" / "static" / "uploads" / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"avatar_{student_id}.{ext}"
    file.save(upload_dir / filename)

    # URL Flask serves from /static/...
    avatar_url = f"/static/uploads/avatars/{filename}"
    models.update_avatar(student_id, avatar_url)

    flash("Đã cập nhật ảnh đại diện.", "success")
    return redirect(url_for("main.profile"))