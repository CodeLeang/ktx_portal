# KTX Portal

A web app for managing an international student dormitory. Scholarship students can check their room, utility bills, scholarship details and maintenance reports online, and dorm administrators manage rooms, billing and requests from one place.

Built as my final-year graduation project at Hanoi University of Science and Technology (HUST).

**Stack:** Python (Flask) · PostgreSQL · Jinja2 · Bootstrap 5 · JavaScript

## Features

**Students**
- Dashboard with monthly scholarship amount and assigned room
- Room details (building, floor, type) and roommates
- Electricity and water bills with usage bars and free-quota status, plus bill history
- Submit maintenance reports and track their status
- Scholarship details, mailbox (messages from the manager), dorm rules, profile

**Administrators**
- Manage students and assign rooms
- Post monthly electricity and water bills
- Reply to maintenance reports
- Send mailbox messages to students

## Technical highlights

- **Authentication:** passwords hashed with `werkzeug.security`, session-based login, `@login_required` decorator and role checks for student vs. admin (`backend/app/auth.py`)
- **SQL injection protection:** all queries use parameterized placeholders, never string concatenation
- **Structure:** routes are split by feature using Flask blueprints (`backend/app/routes/`), database access is kept in `models.py`, and pages are rendered with Jinja2 templates
- **Database:** relational PostgreSQL schema with foreign keys and constraints, plus demo data (`backend/migrations/schema.sql`)

## Project structure

```
ktx_portal/
├── run.py                  # entry point
├── .env.example
├── frontend/
│   ├── templates/          # Jinja2 templates
│   └── static/             # CSS / JS assets
└── backend/
    ├── requirements.txt
    ├── migrations/
    │   └── schema.sql      # tables + demo data
    ├── scripts/            # helper scripts (e.g. create_admin.py)
    └── app/
        ├── __init__.py     # app factory + DB connection
        ├── auth.py         # login / logout / session helpers
        ├── models.py       # database queries
        └── routes/         # main, rooms, bills, reports, scholarship, admin
```

## Getting started

**Requirements:** Python 3.10+, PostgreSQL 14+

```bash
# 1. Clone and enter the project
git clone https://github.com/CodeLeang/ktx_portal.git
cd ktx_portal

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Create the database and load the schema
createdb ktx_portal
psql -U postgres -d ktx_portal -f backend/migrations/schema.sql

# 5. Configure environment variables
cp .env.example .env
# then edit .env:
#   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ktx_portal
#   SECRET_KEY=a-long-random-string

# 6. Create an admin account
python backend/scripts/create_admin.py

# 7. Run the app
python run.py
```

Open http://localhost:5002

### Demo accounts (local demo data only)

| Role | Username | Password |
|------|----------|----------|
| Student | Passport number from the demo data | Initial password = passport number |
| Admin | Created with `create_admin.py` | Chosen when you run the script |

The student default passwords exist only for demo data. Change them before any real deployment.

## Possible improvements

- Deploy a public demo (Render or Railway)
- Force a password change on first login
- Automated tests and CI
- Pagination and search in the admin pages

## Author

**Samkol Meng Leang** · Computer Science, HUST · [GitHub](https://github.com/CodeLeang)

## License

MIT