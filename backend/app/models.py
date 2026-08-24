"""All SQL queries live here."""
from app import get_db
from app import DEFAULT_STUDENT_PASSWORD
from werkzeug.security import generate_password_hash


# ── Students ─────────────────────────────────────────────────────
def _cursor():
    """Always returns a RealDictCursor regardless of connection state."""
    import psycopg2.extras
    return get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def get_student_by_id(student_id):
    cur = _cursor()
    cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
    return cur.fetchone()


def get_student_by_user_id(user_id):
    cur = _cursor()
    cur.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
    return cur.fetchone()


def get_student_by_passport(passport_number):
    cur = _cursor()
    cur.execute("SELECT * FROM students WHERE passport_number=%s", (passport_number,))
    return cur.fetchone()


def get_all_students():
    cur = _cursor()
    cur.execute("""
        SELECT
            s.id, s.user_id, s.student_code, s.full_name,
            s.email, s.phone, s.is_scholarship, s.semester,
            s.scholarship_amt, s.passport_number,
            s.date_of_birth, s.passport_expiry, s.visa_expiry,
            s.gender, s.nationality,
            s.created_at, s.avatar_url,
            COALESCE(s.study_year, 1)    AS study_year,
            COALESCE(s.is_active, TRUE)  AS is_active,
            r.code AS room_code
        FROM students s
        LEFT JOIN room_assignments ra ON ra.student_id = s.id AND ra.is_active
        LEFT JOIN rooms r ON r.id = ra.room_id
        ORDER BY s.student_code
    """)
    return cur.fetchall()


def add_student(student_code, passport_number, full_name,
                email=None, phone=None, semester=None, scholarship_amt=0,
                room_id=None, avatar_url=None, **kwargs):
    """Create login account + student profile in one transaction.
    Initial password = passport number (student must change after first login).
    """
    conn = get_db()
    cur  = _cursor()   # RealDictCursor so fetchone()["id"] works
    try:
        # 1. Login account — initial password is passport number
        cur.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, 'student') RETURNING id
        """, (passport_number, generate_password_hash(passport_number)))
        user_id = cur.fetchone()["id"]

        # 2. Student profile — now includes avatar_url
        study_year = int(kwargs.get('study_year', 1) or 1)
        cur.execute("""
            INSERT INTO students (
                user_id, student_code, passport_number, full_name,
                email, phone, is_scholarship, semester, scholarship_amt,
                study_year, is_active, avatar_url,
                date_of_birth, gender, nationality,
                passport_expiry, visa_expiry, home_address, emergency_contact
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, TRUE, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            ) RETURNING id
        """, (
            user_id, student_code, passport_number, full_name,
            email or None, phone or None,
            bool(int(scholarship_amt or 0) > 0),
            semester or None, int(scholarship_amt or 0),
            study_year,
            avatar_url,
            kwargs.get('date_of_birth') or None,
            kwargs.get('gender') or None,
            kwargs.get('nationality') or None,
            kwargs.get('passport_expiry') or None,
            kwargs.get('visa_expiry') or None,
            kwargs.get('home_address') or None,
            kwargs.get('emergency_contact') or None,
        ))
        student_id = cur.fetchone()["id"]

        # 3. Room assignment
        if room_id:
            cur.execute(
                "INSERT INTO room_assignments (student_id, room_id) VALUES (%s,%s)",
                (student_id, int(room_id))
            )

        conn.commit()
        return student_id

    except Exception:
        conn.rollback()
        raise


def update_student(student_id, full_name, email, phone, semester,
                   scholarship_amt, study_year=1, is_active=True, **kwargs):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE students SET
            full_name       = %s,
            email           = %s,
            phone           = %s,
            semester        = %s,
            scholarship_amt = %s,
            is_scholarship  = %s,
            study_year      = %s,
            is_active       = %s,
            date_of_birth   = %s,
            gender          = %s,
            nationality     = %s,
            passport_expiry = %s,
            visa_expiry     = %s,
            home_address    = %s,
            emergency_contact = %s
        WHERE id = %s
    """, (
        full_name,
        email or None,
        phone or None,
        semester or None,
        int(scholarship_amt or 0),
        bool(int(scholarship_amt or 0) > 0),
        int(study_year or 1),
        bool(is_active),
        kwargs.get('date_of_birth') or None,
        kwargs.get('gender') or None,
        kwargs.get('nationality') or None,
        kwargs.get('passport_expiry') or None,
        kwargs.get('visa_expiry') or None,
        kwargs.get('home_address') or None,
        kwargs.get('emergency_contact') or None,
        student_id,
    ))
    conn.commit()


# ── FIXED: uses RealDictCursor to avoid tuple-index error ──
def update_student_identifiers(student_id, student_code, passport_number):
    """Update MSSV and passport. If passport changes, update login username too."""
    conn = get_db()
    cur = _cursor()  # dùng RealDictCursor để truy cập theo tên cột
    cur.execute("SELECT passport_number, user_id FROM students WHERE id = %s", (student_id,))
    row = cur.fetchone()
    if not row:
        return
    # Use a separate cursor for updates (regular is fine)
    wc = conn.cursor()
    wc.execute("UPDATE students SET student_code = %s WHERE id = %s",
               (student_code.strip(), student_id))
    if passport_number.strip() and passport_number.strip() != row["passport_number"]:
        new_pp = passport_number.strip()
        wc.execute("UPDATE students SET passport_number = %s WHERE id = %s",
                   (new_pp, student_id))
        if row["user_id"]:
            wc.execute("UPDATE users SET username = %s WHERE id = %s",
                       (new_pp, row["user_id"]))
    conn.commit()


def remove_student_from_room(student_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE room_assignments SET is_active=FALSE WHERE student_id=%s",
                (student_id,))
    conn.commit()


# ── FIXED: uses RealDictCursor ──
def delete_student(student_id):
    """Delete student and ALL linked records (reports, messages, room assignments, login)."""
    conn = get_db()
    cur = _cursor()
    cur.execute("SELECT user_id FROM students WHERE id = %s", (student_id,))
    row = cur.fetchone()
    # Delete foreign key dependencies
    wc = conn.cursor()
    wc.execute("DELETE FROM reports          WHERE student_id = %s", (student_id,))
    wc.execute("DELETE FROM messages         WHERE student_id = %s", (student_id,))
    wc.execute("DELETE FROM room_assignments WHERE student_id = %s", (student_id,))
    wc.execute("DELETE FROM students WHERE id = %s", (student_id,))
    if row and row["user_id"]:
        wc.execute("DELETE FROM users WHERE id = %s", (row["user_id"],))
    conn.commit()


# ── Rooms ─────────────────────────────────────────────────────────
def get_room_for_student(student_id):
    cur = _cursor()
    cur.execute("""
        SELECT r.* FROM rooms r
        JOIN room_assignments ra ON ra.room_id=r.id
        WHERE ra.student_id=%s AND ra.is_active
    """, (student_id,))
    return cur.fetchone()


def get_roommates(student_id, room_id):
    cur = _cursor()
    cur.execute("""
        SELECT s.* FROM students s
        JOIN room_assignments ra ON ra.student_id=s.id
        WHERE ra.room_id=%s AND ra.is_active
        ORDER BY (s.id=%s) DESC, s.student_code
    """, (room_id, student_id))
    return cur.fetchall()


def get_all_rooms():
    cur = _cursor()
    cur.execute("""
        SELECT r.*, COUNT(ra.id) AS occupants
        FROM rooms r
        LEFT JOIN room_assignments ra ON ra.room_id=r.id AND ra.is_active
        GROUP BY r.id ORDER BY r.code
    """)
    return cur.fetchall()


def get_all_rooms_with_students():
    """Returns all rooms with full student details (nationality, gender, DOB, etc.)."""
    cur = _cursor()
    cur.execute("""
        SELECT r.*, COUNT(ra.id) AS occupants
        FROM rooms r
        LEFT JOIN room_assignments ra ON ra.room_id=r.id AND ra.is_active
        GROUP BY r.id ORDER BY r.building, r.floor, r.code
    """)
    rooms = cur.fetchall()
    result = []
    for room in rooms:
        room_dict = dict(room)
        cur.execute("""
            SELECT s.id, s.student_code, s.full_name, s.email, s.phone,
                   s.passport_number, s.avatar_url,
                   COALESCE(s.study_year, 1)   AS study_year,
                   COALESCE(s.is_active, TRUE)  AS is_active,
                   s.date_of_birth, s.gender, s.nationality,
                   s.semester, s.scholarship_amt,
                   s.passport_expiry, s.visa_expiry,
                   s.home_address, s.emergency_contact,
                   s.is_scholarship
            FROM students s
            JOIN room_assignments ra ON ra.student_id=s.id
            WHERE ra.room_id=%s AND ra.is_active
            ORDER BY s.student_code
        """, (room["id"],))
        room_dict["students"] = cur.fetchall()
        result.append(room_dict)
    return result


def get_room_occupancy(room_id):
    """Return the number of active students currently assigned to this room."""
    cur = _cursor()
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM room_assignments
        WHERE room_id = %s AND is_active = TRUE
    """, (room_id,))
    return cur.fetchone()["cnt"]


# ── NEW: Get student's assignment date ─────────────────────────
def get_student_assignment_date(student_id):
    cur = _cursor()
    cur.execute("""
        SELECT assigned_at FROM room_assignments
        WHERE student_id = %s AND is_active = TRUE
        ORDER BY assigned_at DESC LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    return row["assigned_at"] if row else None


# ── FIXED assign_room with capacity check ──────────────────────
def assign_room(student_id, room_id):
    """
    Assign a student to a room, deactivating any previous assignment.
    Raises ValueError if room is full, student already in the room, or room not found.
    """
    conn = get_db()
    cur  = _cursor()

    # 1. Check room exists
    cur.execute("SELECT id, capacity FROM rooms WHERE id = %s", (room_id,))
    room = cur.fetchone()
    if not room:
        raise ValueError("Phòng không tồn tại.")

    # 2. Check if student already has active assignment to this room
    cur.execute("""
        SELECT id FROM room_assignments
        WHERE student_id = %s AND room_id = %s AND is_active = TRUE
    """, (student_id, room_id))
    if cur.fetchone():
        raise ValueError("Sinh viên đã ở trong phòng này rồi.")

    # 3. Check current occupancy
    occupancy = get_room_occupancy(room_id)
    if occupancy >= room["capacity"]:
        raise ValueError(f"Phòng đã đầy (sức chứa {room['capacity']}).")

    # 4. Deactivate any other active assignment for this student
    cur.execute("UPDATE room_assignments SET is_active = FALSE WHERE student_id = %s", (student_id,))

    # 5. Create new assignment
    cur.execute(
        "INSERT INTO room_assignments (student_id, room_id) VALUES (%s, %s)",
        (student_id, room_id)
    )
    conn.commit()


def add_room(code, building, floor, room_type, capacity=3, elec_quota=60, water_quota=60):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO rooms (code, building, floor, room_type, capacity, elec_quota, water_quota)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (code, building, int(floor), room_type,
              int(capacity), int(elec_quota), int(water_quota)))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def update_room(room_id, code, building, floor, room_type,
                capacity, elec_quota, water_quota):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE rooms SET
            code        = %s,
            building    = %s,
            floor       = %s,
            room_type   = %s,
            capacity    = %s,
            elec_quota  = %s,
            water_quota = %s
        WHERE id = %s
    """, (code, building, int(floor), room_type,
          int(capacity), int(elec_quota), int(water_quota), room_id))
    conn.commit()


# ── FIXED: uses RealDictCursor to avoid tuple-index error ──
def delete_room(room_id):
    """Only deletes room if no active students."""
    conn = get_db()
    cur = _cursor()
    cur.execute("""
        SELECT COUNT(*) AS n FROM room_assignments
        WHERE room_id = %s AND is_active = TRUE
    """, (room_id,))
    if cur.fetchone()["n"] > 0:
        raise ValueError("Phòng còn sinh viên đang ở — không thể xóa")
    wc = conn.cursor()
    wc.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
    conn.commit()


# ── Bills ─────────────────────────────────────────────────────────
def get_bill_periods():
    """Return distinct periods that have bills, newest first."""
    cur = _cursor()
    cur.execute("SELECT DISTINCT period FROM bills ORDER BY period DESC")
    return [r["period"] for r in cur.fetchall()]


def get_current_bills(room_id, period):
    cur = _cursor()
    cur.execute("SELECT * FROM bills WHERE room_id=%s AND period=%s", (room_id, period))
    return {b["bill_type"]: b for b in cur.fetchall()}


def get_bill_history(room_id, bill_type=None):
    cur = _cursor()
    if bill_type:
        cur.execute("SELECT * FROM bills WHERE room_id=%s AND bill_type=%s ORDER BY period DESC",
                    (room_id, bill_type))
    else:
        cur.execute("SELECT * FROM bills WHERE room_id=%s ORDER BY period DESC, bill_type",
                    (room_id,))
    return cur.fetchall()


def upsert_bill(room_id, bill_type, period, usage, quota, unit_rate=None):
    """Insert or update a bill. unit_rate overrides default price."""
    if unit_rate and int(unit_rate) > 0:
        rate = int(unit_rate)
    else:
        rate = 2700 if bill_type == "electric" else 1500
    over   = max(0, float(usage) - float(quota))
    amount = int(over * rate)
    conn   = get_db()
    cur    = conn.cursor()
    cur.execute("""
        INSERT INTO bills (room_id, bill_type, period, usage_value, quota, unit_rate, amount_due)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (room_id, bill_type, period)
        DO UPDATE SET
            usage_value = EXCLUDED.usage_value,
            quota       = EXCLUDED.quota,
            unit_rate   = EXCLUDED.unit_rate,
            amount_due  = EXCLUDED.amount_due
    """, (room_id, bill_type, period, usage, quota, rate, amount))
    conn.commit()


def delete_bill(bill_id):
    """Delete a bill record by id."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM bills WHERE id = %s", (bill_id,))
    conn.commit()


def get_all_bills():
    cur = _cursor()
    cur.execute("""
        SELECT b.*, r.code AS room_code, r.room_type
        FROM   bills b
        JOIN   rooms r ON r.id = b.room_id
        ORDER  BY b.period DESC, r.code, b.bill_type
    """)
    return cur.fetchall()


# ── Reports ───────────────────────────────────────────────────────
def get_reports_for_student(student_id):
    cur = _cursor()
    cur.execute("SELECT * FROM reports WHERE student_id=%s ORDER BY created_at DESC",
                (student_id,))
    return cur.fetchall()


def create_report(student_id, room_id, title, description):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("INSERT INTO reports (student_id, room_id, title, description) VALUES (%s,%s,%s,%s)",
                (student_id, room_id, title, description))
    conn.commit()


def get_all_reports():
    cur = _cursor()
    cur.execute("""
        SELECT r.*, s.full_name, s.student_code, rm.code AS room_code
        FROM   reports r
        JOIN   students s  ON s.id  = r.student_id
        JOIN   rooms    rm ON rm.id = r.room_id
        ORDER  BY r.created_at DESC
    """)
    return cur.fetchall()


def delete_report(report_id):
    """Delete a resolved report."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM reports WHERE id=%s", (report_id,))
    conn.commit()


def reply_report(report_id, status, reply):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE reports SET status=%s, admin_reply=%s, updated_at=NOW() WHERE id=%s",
                (status, reply, report_id))
    conn.commit()


# ── Messages ──────────────────────────────────────────────────────
def get_messages(student_id):
    cur = _cursor()
    cur.execute("SELECT * FROM messages WHERE student_id=%s ORDER BY created_at DESC",
                (student_id,))
    return cur.fetchall()


def send_message(student_id, subject, body):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("INSERT INTO messages (student_id, subject, body) VALUES (%s,%s,%s)",
                (student_id, subject, body))
    conn.commit()


def update_avatar(student_id, avatar_url):
    """Save avatar URL for a student (by students.id, not users.id)."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE students SET avatar_url=%s WHERE id=%s",
        (avatar_url, student_id)
    )
    conn.commit()


def reset_password(student_id):
    """Reset student password to a random temporary password.
    Returns the temporary password string so admin can tell the student.
    """
    import random, string
    conn = get_db()
    cur  = _cursor()
    cur.execute("SELECT user_id FROM students WHERE id=%s", (student_id,))
    row = cur.fetchone()
    if not row or not row["user_id"]:
        return None
    # Generate random temp password: KTX- + 6 random alphanumeric chars
    chars = string.ascii_letters + string.digits
    temp_pw = "KTX-" + "".join(random.choices(chars, k=6))
    new_hash = generate_password_hash(temp_pw)
    wc = conn.cursor()
    wc.execute(
        "UPDATE users SET password_hash=%s WHERE id=%s",
        (new_hash, row["user_id"])
    )
    conn.commit()
    return temp_pw


def reset_all_student_passwords():
    """One-time maintenance: reset every student account's password back
    to the shared default (DEFAULT_STUDENT_PASSWORD). Does not touch admin.
    Returns the list of usernames that were updated.
    """
    conn = get_db()
    cur  = conn.cursor()
    new_hash = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
    cur.execute("""
        UPDATE users
        SET password_hash = %s
        WHERE role = 'student'
        RETURNING username
    """, (new_hash,))
    updated = [row[0] for row in cur.fetchall()]
    conn.commit()
    return updated


def change_password(user_id, new_password):
    """Update the password_hash for a user."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=%s WHERE id=%s",
        (generate_password_hash(new_password), user_id)
    )
    conn.commit()
    cur.close()