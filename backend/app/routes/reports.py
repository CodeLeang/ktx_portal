from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.auth import login_required
from app import models

bp = Blueprint("reports", __name__)


@bp.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    if session.get("role") == "admin":
        return redirect(url_for("admin.reports"))

    student = models.get_student_by_user_id(session["user_id"])
    if not student:
        student = models.get_student_by_id(session["user_id"])
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    room = models.get_room_for_student(student["id"])
    if request.method == "POST":
        title = request.form["title"].strip()
        desc  = request.form["description"].strip()
        if title and room:
            models.create_report(student["id"], room["id"], title, desc)
            flash("Đã gửi báo hỏng. Quản lý sẽ phản hồi sớm.", "success")
            return redirect(url_for("reports.reports"))
    items = models.get_reports_for_student(student["id"])
    new_replies = [r for r in items if r["admin_reply"] and r["status"] != "resolved"]
    session["report_replies"] = len(new_replies)
    return render_template("reports.html", reports=items, room=room, new_replies=new_replies)