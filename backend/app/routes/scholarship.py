from datetime import date
from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.auth import login_required
from app import models

bp = Blueprint("scholarship", __name__)


@bp.route("/scholarship")
@login_required
def scholarship():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = models.get_student_by_user_id(session["user_id"])
    if not student:
        student = models.get_student_by_id(session["user_id"])
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    # Get current month bills
    period = date.today().strftime("%Y-%m")
    room   = models.get_room_for_student(student["id"])
    bills  = models.get_current_bills(room["id"], period) if room else {}

    elec_bill  = bills.get("electric", {})
    water_bill = bills.get("water", {})

    elec_due   = int(elec_bill.get("amount_due", 0)  or 0)
    water_due  = int(water_bill.get("amount_due", 0) or 0)
    total_due  = elec_due + water_due
    net_payout = max(0, int(student["scholarship_amt"]) - total_due)

    # Last 6 months bill history for the chart
    history = models.get_bill_history(room["id"]) if room else []

    return render_template("scholarship.html",
                           student=student,
                           period=period,
                           room=room,
                           elec_bill=elec_bill,
                           water_bill=water_bill,
                           elec_due=elec_due,
                           water_due=water_due,
                           total_due=total_due,
                           net_payout=net_payout,
                           history=history)


@bp.route("/mailbox")
@login_required
def mailbox():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    student = models.get_student_by_user_id(session["user_id"])
    if not student:
        student = models.get_student_by_id(session["user_id"])
    if not student:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    msgs = models.get_messages(student["id"])
    return render_template("mailbox.html", messages=msgs)