import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from app.auth import login_required, admin_required
from app import models

bp = Blueprint("admin", __name__)


import unicodedata


def _strip_accents(value):
    return "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )


def _normalize_room_type(value):
    raw = _strip_accents((value or "").strip().lower())
    if "hoc" in raw and "bong" in raw:
        return "Học bổng"
    return "Thường"


def _is_scholarship_room(value):
    return _normalize_room_type(value) == "Học bổng"

# ── Avatar upload settings ──────────────────────────────────────
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_avatar(file):
    """Save uploaded avatar to static folder and return its URL."""
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    filename = secure_filename(file.filename)
    # Use Flask's static folder
    static_folder = current_app.static_folder
    upload_folder = os.path.join(static_folder, 'uploads', 'avatars')
    os.makedirs(upload_folder, exist_ok=True)
    ext = filename.rsplit('.', 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)
    # Return URL via url_for
    return url_for('static', filename=f'uploads/avatars/{new_filename}')


# ── Dashboard ─────────────────────────────────────────────────────
@bp.route("/")
@login_required
@admin_required
def dashboard():
    from datetime import date
    period = date.today().strftime("%Y-%m")
    all_reports  = models.get_all_reports()
    all_students = models.get_all_students()
    all_rooms    = models.get_all_rooms()
    pending_count = len([r for r in all_reports if r["status"] == "pending"])
    session["pending_reports"] = pending_count

    # Bills this month
    all_bills = models.get_all_bills()
    month_bills = [b for b in all_bills if b["period"] == period]

    # Bills with generated charge this month (scholarship rooms excluded)
    chargeable_bills = [
        b for b in month_bills
        if b["amount_due"] > 0 and not _is_scholarship_room(b.get("room_type"))
    ]

    # Bills not yet paid this month (scholarship rooms excluded)
    unpaid_bills = [
        b for b in chargeable_bills
        if not b.get("is_paid")
    ]

    return render_template("admin/dashboard.html",
                           students=all_students,
                           rooms=all_rooms,
                           reports=all_reports,
                           bills={},
                           period=period,
                           student=None,
                           pending_count=pending_count,
                           chargeable_count=len(chargeable_bills),
                           chargeable_bills=chargeable_bills,
                           unpaid_count=len(unpaid_bills),
                           unpaid_bills=unpaid_bills,
                           month_bills=month_bills)


# ── Students list ─────────────────────────────────────────────────
@bp.route("/students")
@login_required
@admin_required
def students():
    from datetime import date
    period = date.today().strftime("%Y-%m")
    all_rooms = models.get_all_rooms()
    # Build bills lookup by room_code for current month
    all_bills = models.get_all_bills()
    bills_by_student = {}
    for b in all_bills:
        if b["period"] == period:
            if b["room_code"] not in bills_by_student:
                bills_by_student[b["room_code"]] = {}
            bills_by_student[b["room_code"]][b["bill_type"]] = b
    return render_template("admin/students.html",
                           students=models.get_all_students(),
                           rooms=all_rooms,
                           bills_by_student=bills_by_student,
                           period=period)


# ── Add student (with avatar upload) ────────────────────────────
@bp.route("/students/add", methods=["POST"])
@login_required
@admin_required
def add_student():
    try:
        # Handle avatar upload
        avatar_url = None
        if 'avatar' in request.files:
            avatar_url = save_avatar(request.files['avatar'])

        room_id_raw = request.form.get("room_id", "").strip()
        student_type = request.form.get("student_type", "scholarship").strip().lower()
        scholarship_amt = int(request.form.get("scholarship_amt", 0) or 0)
        if student_type == "regular":
            scholarship_amt = 0

        models.add_student(
            student_code      = request.form["student_code"].strip(),
            passport_number   = request.form["passport_number"].strip(),
            full_name         = request.form["full_name"].strip(),
            email             = request.form.get("email",             "").strip() or None,
            phone             = request.form.get("phone",             "").strip() or None,
            semester          = request.form.get("semester",          "").strip() or None,
            scholarship_amt   = scholarship_amt,
            room_id           = int(room_id_raw) if room_id_raw else None,
            study_year        = int(request.form.get("study_year", 1) or 1),
            date_of_birth     = request.form.get("date_of_birth")     or None,
            gender            = request.form.get("gender")            or None,
            nationality       = request.form.get("nationality")       or None,
            passport_expiry   = request.form.get("passport_expiry")   or None,
            visa_type         = request.form.get("visa_type")         or None,
            visa_expiry       = request.form.get("visa_expiry")       or None,
            home_address      = request.form.get("home_address")      or None,
            emergency_contact = request.form.get("emergency_contact") or None,
            avatar_url        = avatar_url,
        )
        flash("Đã thêm sinh viên mới thành công.", "success")
    except Exception as e:
        flash(f"Không thể thêm sinh viên: {e}", "danger")
    return redirect(url_for("admin.students"))


# ── Edit student (with avatar upload) ────────────────────────────
@bp.route("/students/edit/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def edit_student(student_id):
    try:
        # Handle avatar upload
        avatar_url = None
        if 'avatar' in request.files:
            avatar_url = save_avatar(request.files['avatar'])

        # 1. Update student_code and passport_number (passport also updates login username)
        models.update_student_identifiers(
            student_id      = student_id,
            student_code    = request.form.get("student_code",    "").strip(),
            passport_number = request.form.get("passport_number", "").strip(),
        )

        # 2. Update all other profile fields
        models.update_student(
            student_id        = student_id,
            full_name         = request.form.get("full_name",         "").strip(),
            email             = request.form.get("email",             "").strip() or None,
            phone             = request.form.get("phone",             "").strip() or None,
            semester          = request.form.get("semester",          "").strip() or None,
            scholarship_amt   = 0 if request.form.get("student_type", "scholarship").strip().lower() == "regular" else int(request.form.get("scholarship_amt", 0) or 0),
            study_year        = int(request.form.get("study_year", 1) or 1),
            is_active         = request.form.get("is_active") == "1",
            date_of_birth     = request.form.get("date_of_birth")     or None,
            gender            = request.form.get("gender")            or None,
            nationality       = request.form.get("nationality")       or None,
            passport_expiry   = request.form.get("passport_expiry")   or None,
            visa_type         = request.form.get("visa_type")         or None,
            visa_expiry       = request.form.get("visa_expiry")       or None,
            home_address      = request.form.get("home_address")      or None,
            emergency_contact = request.form.get("emergency_contact") or None,
        )

        # 3. Update avatar if a new one was uploaded
        if avatar_url:
            models.update_avatar(student_id, avatar_url)

        # 4. Change room ONLY if it's different from current
        room_id_raw = request.form.get("room_id", "").strip()
        if room_id_raw:
            new_room_id = int(room_id_raw)
            # Get student's current room (if any)
            current_room = models.get_room_for_student(student_id)
            current_room_id = current_room["id"] if current_room else None
            if new_room_id != current_room_id:
                models.assign_room(student_id, new_room_id)

        flash("Đã cập nhật thông tin sinh viên.", "success")
    except Exception as e:
        flash(f"Không thể cập nhật: {e}", "danger")
    return redirect(url_for("admin.students"))


# ── Delete student ────────────────────────────────────────────────
@bp.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def delete_student(student_id):
    try:
        models.remove_student_from_room(student_id)
        models.delete_student(student_id)
        flash("Đã xóa sinh viên khỏi hệ thống.", "success")
    except Exception as e:
        flash(f"Không thể xóa: {e}", "danger")
    return redirect(url_for("admin.students"))


# ── Quick assign room (redirects back to referring page) ───────
@bp.route("/students/assign", methods=["POST"])
@login_required
@admin_required
def assign():
    try:
        student_id = int(request.form["student_id"])
        room_id    = int(request.form["room_id"])
        models.assign_room(student_id, room_id)
        flash("Đã phân phòng thành công.", "success")
    except Exception as e:
        flash(f"Không thể phân phòng: {e}", "danger")
    return redirect(request.referrer or url_for("admin.rooms"))


# ── Bills ─────────────────────────────────────────────────────────
@bp.route("/bills", methods=["GET", "POST"])
@login_required
@admin_required
def bills():
    if request.method == "POST":
        unit_rate = request.form.get("unit_rate", "").strip()
        saved = {
            "room_id":     request.form["room_id"],
            "bill_type":   request.form["bill_type"],
            "period":      request.form["period"],
            "usage_value": request.form["usage_value"],
            "quota":       request.form["quota"],
            "unit_rate":   unit_rate,
        }
        models.upsert_bill(
            int(saved["room_id"]),
            saved["bill_type"],
            saved["period"],
            float(saved["usage_value"]),
            float(saved["quota"]),
            unit_rate=int(unit_rate) if unit_rate else None,
        )
        flash("Đã cập nhật hóa đơn.", "success")
        return redirect(url_for("admin.bills", **saved))
    from datetime import date
    periods = models.get_bill_periods()
    selected_period = request.args.get("period") or date.today().strftime("%Y-%m")
    last_input = {
        "room_id":     request.args.get("room_id", ""),
        "bill_type":   request.args.get("bill_type", "electric"),
        "usage_value": request.args.get("usage_value", ""),
        "quota":       request.args.get("quota", ""),
        "unit_rate":   request.args.get("unit_rate", ""),
    }
    return render_template("admin/bills.html",
                           rooms=models.get_all_rooms(),
                           bills=models.get_all_bills(),
                           periods=periods,
                           now_period=date.today().strftime("%Y-%m"),
                           selected_period=selected_period,
                           last_input=last_input)


@bp.route("/bills/delete/<int:bill_id>", methods=["POST"])
@login_required
@admin_required
def delete_bill(bill_id):
    models.delete_bill(bill_id)
    flash("Đã xóa hóa đơn.", "success")
    return redirect(url_for("admin.bills"))


# ── Reports ───────────────────────────────────────────────────────
@bp.route("/reports", methods=["GET", "POST"])
@login_required
@admin_required
def reports():
    if request.method == "POST":
        models.reply_report(
            int(request.form["report_id"]),
            request.form["status"],
            request.form["reply"],
        )
        flash("Đã phản hồi báo hỏng.", "success")
        return redirect(url_for("admin.reports"))
    all_reports = models.get_all_reports()
    pending_count = len([r for r in all_reports if r["status"] == "pending"])
    session["pending_reports"] = pending_count
    return render_template("admin/reports.html",
                           reports=all_reports,
                           pending_count=pending_count)


# ── Rooms list (with students) ────────────────────────────────────
@bp.route("/rooms")
@login_required
@admin_required
def rooms():
    from datetime import date
    period = date.today().strftime("%Y-%m")
    all_rooms = models.get_all_rooms_with_students()

    # Build bills lookup: {room_id: {electric: bill, water: bill}}
    bills_by_room = {}
    for r in all_rooms:
        bills_by_room[r["id"]] = models.get_current_bills(r["id"], period)

    return render_template("admin/rooms.html",
                           rooms=all_rooms,
                           all_students=models.get_all_students(),
                           bills_by_room=bills_by_room,
                           period=period)


# ── Add room ──────────────────────────────────────────────────────
@bp.route("/rooms/add", methods=["POST"])
@login_required
@admin_required
def add_room():
    try:
        models.add_room(
            code        = request.form["code"].strip().upper(),
            building    = request.form["building"].strip().upper(),
            floor       = int(request.form["floor"]),
            room_type   = _normalize_room_type(request.form.get("room_type", "Học bổng")),
            capacity    = int(request.form.get("capacity",    3)  or 3),
            elec_quota  = int(request.form.get("elec_quota",  60) or 60),
            water_quota = int(request.form.get("water_quota", 10) or 10),
        )
        flash("Đã thêm phòng mới.", "success")
    except Exception as e:
        flash(f"Không thể thêm phòng: {e}", "danger")
    return redirect(url_for("admin.rooms"))


# ── Edit room ─────────────────────────────────────────────────────
@bp.route("/rooms/edit/<int:room_id>", methods=["POST"])
@login_required
@admin_required
def edit_room(room_id):
    try:
        models.update_room(
            room_id     = room_id,
            code        = request.form["code"].strip().upper(),
            building    = request.form["building"].strip().upper(),
            floor       = int(request.form["floor"]),
            room_type   = _normalize_room_type(request.form.get("room_type", "Học bổng")),
            capacity    = int(request.form.get("capacity",    3)  or 3),
            elec_quota  = int(request.form.get("elec_quota",  60) or 60),
            water_quota = int(request.form.get("water_quota", 10) or 10),
        )
        flash("Đã cập nhật phòng.", "success")
    except Exception as e:
        flash(f"Không thể cập nhật phòng: {e}", "danger")
    return redirect(url_for("admin.rooms"))


# ── Delete room ───────────────────────────────────────────────────
@bp.route("/rooms/delete/<int:room_id>", methods=["POST"])
@login_required
@admin_required
def delete_room(room_id):
    try:
        models.delete_room(room_id)
        flash("Đã xóa phòng.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Không thể xóa: {e}", "danger")
    return redirect(url_for("admin.rooms"))


# ── Remove student from room ──────────────────────────────────────
@bp.route("/rooms/remove-student", methods=["POST"])
@login_required
@admin_required
def remove_from_room():
    student_id = int(request.form["student_id"])
    models.remove_student_from_room(student_id)
    flash("Đã xóa sinh viên khỏi phòng.", "success")
    return redirect(url_for("admin.rooms"))


# ── Send message to student ───────────────────────────────────────
@bp.route("/messages/send", methods=["POST"])
@login_required
@admin_required
def send_message():
    try:
        student_id = int(request.form["student_id"])
        subject    = request.form.get("subject", "").strip()
        body       = request.form.get("body", "").strip()
        if not subject or not body:
            flash("Tiêu đề và nội dung không được để trống.", "danger")
        else:
            models.send_message(student_id, subject, body)
            flash("Đã gửi thông báo tới sinh viên.", "success")
    except Exception as e:
        flash(f"Không thể gửi: {e}", "danger")
    return redirect(url_for("admin.students"))


# ── Delete report ─────────────────────────────────────────────────
@bp.route("/reports/delete/<int:report_id>", methods=["POST"])
@login_required
@admin_required
def delete_report(report_id):
    try:
        models.delete_report(report_id)
        flash("Đã xóa báo hỏng.", "success")
    except Exception as e:
        flash(f"Không thể xóa: {e}", "danger")
    return redirect(url_for("admin.reports"))


# ── Reset student password to default ────────────────────────────
@bp.route("/students/reset-password/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def reset_password(student_id):
    try:
        temp_pw = models.reset_password(student_id)
        if temp_pw:
            flash(f"reset_pw::{temp_pw}", "success")
        else:
            flash("Không thể đặt lại mật khẩu: sinh viên chưa có tài khoản.", "danger")
    except Exception as e:
        flash(f"Không thể đặt lại mật khẩu: {e}", "danger")
    return redirect(url_for("admin.students"))

# ── One-time: reset ALL student passwords to the shared default ──
# Visit this URL once while logged in as admin, then you can remove this
# route again. Does not touch the admin account.
@bp.route("/students/reset-all-passwords", methods=["GET"])
@login_required
@admin_required
def reset_all_passwords():
    try:
        updated = models.reset_all_student_passwords()
        flash(f"Đã đặt lại mật khẩu về mặc định cho {len(updated)} sinh viên.", "success")
    except Exception as e:
        flash(f"Không thể đặt lại mật khẩu hàng loạt: {e}", "danger")
    return redirect(url_for("admin.students"))