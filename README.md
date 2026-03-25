# Journal App (Flask + SQLite/MySQL + Vercel-ready)

Stack:

- Frontend: HTML/CSS/JS
- Backend: Python Flask
- Database: SQLite (default) or MySQL

## Important Deployment Note

If you deploy to Vercel, you cannot use your own local MySQL running on your laptop as the production DB.

- Local MySQL works for local development.
- Vercel production must connect to a hosted MySQL database using environment variables.
- If MySQL is not configured on Vercel, the app now falls back to SQLite at `/tmp/journal.db` (ephemeral).

## Files Added for Deployment

- `api/index.py`: Vercel Python function entrypoint
- `vercel.json`: routes all traffic to Flask app
- `.env.example`: environment template

## Local Development (SQLite default)

1. Create `.env` from `.env.example` and set values:

```env
DB_ENGINE=sqlite
SQLITE_DB_PATH=journal.db
HOST=0.0.0.0
PORT=5000
FLASK_DEBUG=false
SECRET_KEY=change-this
```

2. Install and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\journal_app\run_waitress.py
```

## Local Development (MySQL)

1. Create local MySQL database:

```sql
CREATE DATABASE journal;
```

2. Create `.env` from `.env.example` and update values:

```env
DB_ENGINE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_local_mysql_password
MYSQL_DATABASE=journal
HOST=0.0.0.0
PORT=5000
FLASK_DEBUG=false
SECRET_KEY=change-this
```

3. Install and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\journal_app\run_waitress.py
```

## GitHub + Vercel Deployment

1. Push project to GitHub.
2. Import repo in Vercel.
3. In Vercel Project Settings -> Environment Variables, choose one of these:
   - SQLite (quick/demo):
     - `DB_ENGINE=sqlite`
     - `SQLITE_DB_PATH=/tmp/journal.db`
     - `SECRET_KEY=<strong random secret>`
   - MySQL (persistent):
     - `DB_ENGINE=mysql`
     - `MYSQL_URL=<optional single connection url from provider>`
     - `DATABASE_URL=<Aiven-style URL also supported>`
     - `MYSQL_HOST=<your hosted mysql host>`
     - `MYSQL_PORT=3306`
     - `MYSQL_USER=<your hosted mysql user>`
     - `MYSQL_PASSWORD=<your hosted mysql password>`
     - `MYSQL_DATABASE=<your hosted mysql database>`
     - `MYSQL_SSL_MODE=require` (if provider requires SSL)
     - `SECRET_KEY=<strong random secret>`
   - Optional for both:
     - `FLASK_DEBUG=false`
4. Deploy.

The app will auto-create required tables on startup.
