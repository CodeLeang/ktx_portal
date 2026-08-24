"""
Tạo hoặc đổi mật khẩu tài khoản admin một cách an toàn.

Thay cho cơ chế cũ (mật khẩu admin hardcode ngay trong route /login),
script này chạy MỘT LẦN từ terminal để tạo tài khoản admin đầu tiên,
hoặc đổi mật khẩu cho admin đã có. Mật khẩu KHÔNG được lưu trong code.

Cách dùng:
    cd backend
    python scripts/create_admin.py

Script sẽ hỏi username và mật khẩu trực tiếp trên terminal (mật khẩu
không hiện ra màn hình khi nhập, dùng getpass).
"""
from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Lỗi: chưa thiết lập DATABASE_URL trong file .env")
        sys.exit(1)

    username = input("Tên tài khoản admin (mặc định 'admin'): ").strip() or "admin"
    password = getpass.getpass("Mật khẩu admin: ")
    confirm = getpass.getpass("Nhập lại mật khẩu: ")

    if not password:
        print("Lỗi: mật khẩu không được để trống.")
        sys.exit(1)
    if password != confirm:
        print("Lỗi: hai lần nhập mật khẩu không khớp.")
        sys.exit(1)
    if len(password) < 8:
        print("Lỗi: mật khẩu nên có ít nhất 8 ký tự.")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    password_hash = generate_password_hash(password)

    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    existing = cur.fetchone()

    if existing:
        cur.execute(
            "UPDATE users SET password_hash = %s, role = 'admin' WHERE id = %s",
            (password_hash, existing["id"]),
        )
        print(f"Đã đổi mật khẩu cho tài khoản admin '{username}'.")
    else:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'admin')",
            (username, password_hash),
        )
        print(f"Đã tạo tài khoản admin mới: '{username}'.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
