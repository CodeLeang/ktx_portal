#!/usr/bin/env python3
"""
Simple migration: set SV0001 username to passport N01418798 and reset its password.
Run from project root with the virtualenv active, or with .venv/bin/python3.
"""
import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()

DEFAULT_STUDENT_PASSWORD = "123@ktxquanly123"
TARGET_MAPPING = {"SV0001": "N01418798"}


def migrate_one():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment (.env). Aborting.")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for old_code, passport in TARGET_MAPPING.items():
            # Find the user linked to this student code
            cur.execute(
                "SELECT u.id AS user_id, u.username, s.id AS student_id, s.student_code"
                " FROM users u JOIN students s ON u.id=s.user_id WHERE s.student_code=%s",
                (old_code,)
            )
            row = cur.fetchone()
            if not row:
                print(f"No student found with code {old_code}; skipping.")
                continue

            user_id = row["user_id"]
            old_username = row["username"]
            print(f"Updating user_id={user_id}: {old_username} -> {passport}")

            # Update username and reset password
            pw_hash = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
            cur.execute(
                "UPDATE users SET username=%s, password_hash=%s WHERE id=%s",
                (passport, pw_hash, user_id),
            )
            conn.commit()
            print(f"  ✓ Updated. New password: {DEFAULT_STUDENT_PASSWORD}\n")

        print("Migration finished.")
    except Exception as e:
        conn.rollback()
        print("Migration failed:", e)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    migrate_one()
