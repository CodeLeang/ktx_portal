from datetime import date
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.auth import login_required
from app import models

bp = Blueprint("bills", __name__)


def _get_student():
    """Helper to fetch the current student from session."""
    student = models.get_student_by_user_id(session.get("user_id"))
    if not student:
        student = models.get_student_by_id(session.get("user_id"))
    return student


@bp.route("/electric")
@login_required
def electric():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = _get_student()
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"])
    history = models.get_bill_history(room["id"], "electric") if room else []
    study_year = int(student.get("study_year") or 1)
    current_year = date.today().year
    start_year = current_year - study_year
    years = [str(y) for y in range(start_year, start_year + 5)]
    return render_template("bills_electric.html", room=room, history=history, years=years)


@bp.route("/water")
@login_required
def water():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = _get_student()
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"])
    history = models.get_bill_history(room["id"], "water") if room else []
    study_year = int(student.get("study_year") or 1)
    current_year = date.today().year
    start_year = current_year - study_year
    years = [str(y) for y in range(start_year, start_year + 5)]
    return render_template("bills_water.html", room=room, history=history, years=years)


@bp.route("/history")
@login_required
def history():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = _get_student()
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"])
    if not room:
        flash("Bạn chưa được phân phòng.", "warning")
        return redirect(url_for("main.dashboard"))

    # Get all bills for this room (newest first)
    all_bills = models.get_bill_history(room["id"])  # returns list of dicts

    # Filter parameters
    selected_month = request.args.get("month", type=int)
    selected_year = request.args.get("year", type=int)

    # Apply filter if both month and year are provided
    filtered_bills = all_bills
    if selected_month and selected_year:
        filtered_bills = [
            b for b in all_bills
            if b["period"] == f"{selected_year:04d}-{selected_month:02d}"
        ]

    # Build dropdown options from all bills (not filtered)
    available_periods = sorted({b["period"] for b in all_bills}, reverse=True)
    available_years = sorted({p[:4] for p in available_periods}, reverse=True)
    available_months = sorted({p[5:7] for p in available_periods}, reverse=True)

    return render_template(
        "bills_history.html",
        bills=filtered_bills,
        room=room,
        available_years=available_years,
        available_months=available_months,
        selected_month=selected_month,
        selected_year=selected_year,
    )