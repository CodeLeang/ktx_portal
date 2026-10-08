# KTX Portal — Dormitory Management for Scholarship Students

Final-year IT graduation project.

**Stack:** Python (Flask) · PostgreSQL · Bootstrap 5 · HTML/CSS/JavaScript

---

## 1. Folder structure

```
ktx_portal/
├── README.md
├── .env.example
├── run.py                     ← entry point (python run.py)
├── frontend/
│   ├── templates/             ← all Jinja templates
│   └── static/                ← css/js assets
└── backend/
    ├── requirements.txt
    ├── migrations/
    │   └── schema.sql
    ├── scripts/
    │   └── start_web.sh
    └── app/
        ├── __init__.py        ← Flask app factory + DB connection
        ├── auth.py            ← login / logout / session helpers
        ├── models.py          ← all SQL queries
        └── routes/
            ├── main.py
            ├── rooms.py
            ├── bills.py
            ├── reports.py
            ├── scholarship.py
            └── admin.py
```

---

## 2. How to run it (step by step)

### Prerequisites
- Python 3.10 or newer
- PostgreSQL 14 or newer (running locally)
- VS Code

### Steps

1. **Open the folder in VS Code**
   `File → Open Folder → ktx_portal`

2. **Create a virtual environment** (in VS Code terminal):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac / Linux
   source venv/bin/activate
   ```

3. **Install Python packages**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Create the database**
   Open pgAdmin (or `psql`) and run:
   ```sql
   CREATE DATABASE ktx_portal;
   ```
   Then run the schema file:
   ```bash
   psql -U postgres -d ktx_portal -f backend/migrations/schema.sql
   ```
   This creates all tables and inserts demo data (students, rooms, bills).

5. **Configure environment**
   Copy `.env.example` to `.env` and edit your PostgreSQL password:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ktx_portal
   SECRET_KEY=change-me-to-anything-random
   ```

6. **Start the app**
   ```bash
   python run.py
   ```
   Open http://localhost:5002

### Optional: keep it running in the background on macOS

If you want the web app to stay up after closing the terminal, use the LaunchAgent setup in `backend/scripts/start_web.sh` with a plist in `~/Library/LaunchAgents`. That makes the site start automatically when you log in again.

To control it manually later:

```bash
launchctl kickstart -k gui/$(id -u)/com.mengleang.ktxportal.web
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.mengleang.ktxportal.web.plist
```

### Demo accounts

| Role | Username | Password |
|------|----------|----------|
| Student (scholarship) | Passport number (e.g. A1234567) | Same as passport number (initial) |
| Admin (dorm manager)  | admin (or your chosen username)  | Set via backend/scripts/create_admin.py |

---

## 3. What's inside (features)

**Student side** (matches your screenshot):
- Dashboard: welcome card, monthly scholarship amount, assigned room
- Room info (building, floor, type) + roommates list
- Electricity bill + water bill with usage bars and free-quota status
- Bill history (previous months)
- Maintenance reports (báo hỏng) — submit + track status
- Scholarship details
- Mailbox (messages from manager)
- Dorm rules (nội quy)
- Profile

**Admin side**:
- Manage students, assign rooms
- Post monthly electricity / water bills
- Reply to maintenance reports
- Send mailbox messages

---

## 4. How to demo to your professor

1. Run the app, log in as **SV0001** → show dashboard, room, bills, submit a report.
2. Log out, log in as **admin** → show how admin assigns rooms, posts bills, replies to a report.
3. Log back in as **SV0001** → the changes appear.
4. Open `backend/migrations/schema.sql` to show the database design (8 tables, foreign keys, constraints).
5. Open `backend/app/models.py` — every SQL query is here, easy to explain.
6. Open `backend/app/routes/bills.py` — show how a request flows: route → model → template.

---

## 5. How to share the link (so others can try it)

Easiest free options:
- **Render.com** — free PostgreSQL + free web service. Push the code to GitHub, connect Render, set the same env vars. Takes 10 minutes.
- **Railway.app** — same idea.
- **Localhost demo only**: `python run.py` and use `ngrok http 5002` to get a public URL for the demo session.

---

- *"How do you handle login?"* → password hashing with `werkzeug.security`, session cookies, `@login_required` decorator (see `backend/app/auth.py`).
- *"How do you prevent SQL injection?"* → all queries use parameterized `%s` placeholders (psycopg2), never string concatenation.
- *"How would you scale it?"* → add caching, switch sessions to Redis, deploy behind gunicorn + nginx.

