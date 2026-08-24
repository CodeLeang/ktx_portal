-- KTX Portal — full schema + demo data
-- Run: psql -U postgres -d ktx_portal -f backend/migrations/schema.sql

DROP TABLE IF EXISTS messages, reports, bills, roommates, room_assignments, rooms, students, users CASCADE;

-- ─── USERS (login — admin only) ─────────────────────────────────
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('student','admin')),
    created_at    TIMESTAMP DEFAULT NOW()
);

-- ─── STUDENTS ───────────────────────────────────────────────────
CREATE TABLE students (
    id                SERIAL PRIMARY KEY,
    user_id           INT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    student_code      VARCHAR(20) UNIQUE NOT NULL,
    passport_number   VARCHAR(30) UNIQUE,            -- login username for students
    full_name         VARCHAR(120) NOT NULL,
    email             VARCHAR(120),
    phone             VARCHAR(20),
    avatar_url        TEXT,
    is_scholarship    BOOLEAN DEFAULT TRUE,
    semester          VARCHAR(30),
    scholarship_amt   INT DEFAULT 0,
    study_year        INT DEFAULT 1,
    is_active         BOOLEAN DEFAULT TRUE,
    date_of_birth     DATE,
    gender            VARCHAR(10),
    nationality       VARCHAR(60),
    passport_expiry   DATE,
    visa_type         VARCHAR(30),
    visa_expiry       DATE,
    home_address      TEXT,
    emergency_contact TEXT,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- ─── ROOMS ──────────────────────────────────────────────────────
CREATE TABLE rooms (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20) UNIQUE NOT NULL,
    building    VARCHAR(10) NOT NULL,
    floor       INT NOT NULL,
    room_type   VARCHAR(30) NOT NULL,
    capacity    INT DEFAULT 4,
    elec_quota  INT DEFAULT 60,
    water_quota INT DEFAULT 10
);

-- ─── ROOM ASSIGNMENT ────────────────────────────────────────────
CREATE TABLE room_assignments (
    id          SERIAL PRIMARY KEY,
    student_id  INT REFERENCES students(id) ON DELETE CASCADE,
    room_id     INT REFERENCES rooms(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);

-- ─── BILLS ──────────────────────────────────────────────────────
CREATE TABLE bills (
    id          SERIAL PRIMARY KEY,
    room_id     INT REFERENCES rooms(id),
    bill_type   VARCHAR(10) NOT NULL CHECK (bill_type IN ('electric','water')),
    period      VARCHAR(7) NOT NULL,
    usage_value NUMERIC(10,2) NOT NULL,
    quota       NUMERIC(10,2) NOT NULL,
    unit_rate   INT,
    amount_due  INT NOT NULL DEFAULT 0,
    is_paid     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (room_id, bill_type, period)
);

-- ─── REPORTS ────────────────────────────────────────────────────
CREATE TABLE reports (
    id          SERIAL PRIMARY KEY,
    student_id  INT REFERENCES students(id),
    room_id     INT REFERENCES rooms(id),
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','in_progress','resolved')),
    admin_reply TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- ─── MESSAGES ───────────────────────────────────────────────────
CREATE TABLE messages (
    id          SERIAL PRIMARY KEY,
    student_id  INT REFERENCES students(id),
    subject     VARCHAR(200) NOT NULL,
    body        TEXT NOT NULL,
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════════
-- DEMO DATA
-- Mật khẩu sinh viên ban đầu = chính số hộ chiếu của sinh viên đó.
-- Tài khoản admin: chạy `python scripts/create_admin.py` để tạo mật khẩu
-- admin đầu tiên một cách an toàn — KHÔNG hardcode mật khẩu trong file này.
-- ════════════════════════════════════════════════════════════════

INSERT INTO students (user_id, student_code, passport_number, full_name, email, phone, is_scholarship, semester, scholarship_amt) VALUES
(NULL, 'SV0001', 'A1234567', 'Samkol Meng Leang', 'mengleang@example.com', '0900000001', TRUE, '2026 - Học kỳ 1', 300000),
(NULL, 'SV0018', 'B2345678', 'Nguyen Van An',     'an.nv@example.com',     '0900000018', TRUE, '2026 - Học kỳ 1', 300000),
(NULL, 'SV0022', 'C3456789', 'Ly Heng Piseth',    'piseth.lh@example.com', '0900000022', TRUE, '2026 - Học kỳ 1', 300000);

-- TO ADD MORE STUDENTS: just INSERT into students with their passport_number.
-- No users row needed. They login immediately with passport + shared password.
-- Example:
-- INSERT INTO students (student_code, passport_number, full_name, email, phone, is_scholarship, semester, scholarship_amt)
-- VALUES ('SV0050', 'D4567890', 'Nguyen Thi Lan', 'lan@example.com', '0911222333', TRUE, '2026 - Học kỳ 1', 300000);

INSERT INTO rooms (code, building, floor, room_type, capacity, elec_quota, water_quota) VALUES
('A2-407', 'A2', 4, 'Học bổng', 4, 60, 10),
('A2-408', 'A2', 4, 'Học bổng', 4, 60, 10),
('B1-201', 'B1', 2, 'Thường',   4, 50,  8);

INSERT INTO room_assignments (student_id, room_id) VALUES (1, 1), (2, 1), (3, 1);

INSERT INTO bills (room_id, bill_type, period, usage_value, quota, amount_due) VALUES
(1, 'electric', '2026-03', 48, 60, 0),
(1, 'water',    '2026-03',  8, 10, 0),
(1, 'electric', '2026-02', 55, 60, 0),
(1, 'water',    '2026-02',  9, 10, 0),
(1, 'electric', '2026-01', 62, 60, 8400),
(1, 'water',    '2026-01',  7, 10, 0);

INSERT INTO reports (student_id, room_id, title, description, status, admin_reply) VALUES
(1, 1, 'Quạt trần kêu to', 'Quạt trong phòng phát ra tiếng ồn lớn khi bật số 3.', 'in_progress', 'Đã ghi nhận, kỹ thuật sẽ kiểm tra trong 2 ngày.'),
(1, 1, 'Bóng đèn nhà tắm cháy', 'Bóng đèn LED nhà tắm bị cháy hôm qua.', 'resolved', 'Đã thay bóng mới ngày 05/03.');

INSERT INTO messages (student_id, subject, body) VALUES
(1, 'Chào mừng đến với KTX', 'Chúc bạn một học kỳ mới thành công! Mọi thắc mắc liên hệ phòng quản lý tầng 1.'),
(1, 'Lịch tổng vệ sinh', 'Chủ nhật tuần này (10/03) sẽ tổng vệ sinh toàn bộ tòa A2 từ 8h sáng.');
