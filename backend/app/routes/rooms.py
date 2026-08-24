from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.auth import login_required
from app import models
from datetime import date

bp = Blueprint("rooms", __name__)


@bp.route("/room")
@login_required
def room_info():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = models.get_student_by_user_id(session["user_id"])
    if not student:
        student = models.get_student_by_id(session["user_id"])
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"])
    roommates = models.get_roommates(student["id"], room["id"]) if room else []
    # Provide current period and bills so templates that expect them do not fail
    period = date.today().strftime("%Y-%m")
    bills = models.get_current_bills(room["id"], period) if room else {}
    return render_template("room.html", student=student, room=room, roommates=roommates,
                           period=period, bills=bills)


@bp.route("/roommates")
@login_required
def roommates():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = models.get_student_by_user_id(session["user_id"])
    if not student:
        student = models.get_student_by_id(session["user_id"])
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"])
    mates = models.get_roommates(student["id"], room["id"]) if room else []
    return render_template("roommates.html", room=room, roommates=mates, student=student)
