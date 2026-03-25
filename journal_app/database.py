import os
import sqlite3
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from typing import Any
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").strip().lower()
IS_VERCEL = os.getenv("VERCEL") == "1"

_default_sqlite_path = "/tmp/journal.db" if IS_VERCEL else "journal.db"
_sqlite_db_path_value = os.getenv("SQLITE_DB_PATH", _default_sqlite_path)
SQLITE_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, _sqlite_db_path_value))


def _get_mysql_url() -> str:
    for key in ("MYSQL_URL", "DATABASE_URL", "AIVEN_DATABASE_URL"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


# On Vercel, localhost MySQL is unreachable; fall back to sqlite so deploys don't crash.
if IS_VERCEL and DB_ENGINE == "mysql":
    _mysql_url = _get_mysql_url()
    _mysql_host = os.getenv("MYSQL_HOST", "").strip().lower()
    if not _mysql_url and _mysql_host in {"", "127.0.0.1", "localhost"}:
        DB_ENGINE = "sqlite"

if DB_ENGINE not in {"sqlite", "mysql"}:
    raise RuntimeError("DB_ENGINE must be 'sqlite' or 'mysql'.")


def _convert_placeholders(query: str) -> str:
    if DB_ENGINE == "mysql":
        return query.replace("?", "%s")
    return query


def _execute(cursor: Any, query: str, params: tuple[Any, ...] = ()) -> None:
    cursor.execute(_convert_placeholders(query), params)


def _scalar_value(row: Any) -> int:
    if row is None:
        return 0
    if isinstance(row, dict):
        return int(next(iter(row.values())))
    return int(row[0])


def get_db():
    if DB_ENGINE == "mysql":
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError(
                "PyMySQL is required for DB_ENGINE=mysql. Install it with `pip install pymysql`."
            ) from exc

        mysql_url = _get_mysql_url()
        if mysql_url:
            parsed = urlparse(mysql_url)
            query_params = parse_qs(parsed.query)

            connect_kwargs = {
                "host": parsed.hostname or os.getenv("MYSQL_HOST", "127.0.0.1"),
                "port": parsed.port or int(os.getenv("MYSQL_PORT", "3306")),
                "user": parsed.username or os.getenv("MYSQL_USER", "root"),
                "password": parsed.password or os.getenv("MYSQL_PASSWORD", ""),
                "database": (parsed.path or "/journal").lstrip("/"),
                "cursorclass": pymysql.cursors.DictCursor,
                "autocommit": False,
            }

            ssl_mode = (
                query_params.get("ssl-mode", [""])[0]
                or query_params.get("sslmode", [""])[0]
                or os.getenv("MYSQL_SSL_MODE", "")
            ).lower()

            if ssl_mode in {"required", "require", "verify_ca", "verify_identity"}:
                connect_kwargs["ssl"] = {}

            ssl_ca_path = os.getenv("MYSQL_SSL_CA", "").strip()
            if ssl_ca_path:
                connect_kwargs["ssl"] = {"ca": ssl_ca_path}

            return pymysql.connect(**connect_kwargs)

        mysql_ssl_mode = os.getenv("MYSQL_SSL_MODE", "").strip().lower()
        mysql_ssl_ca = os.getenv("MYSQL_SSL_CA", "").strip()
        ssl_kwargs = None

        if mysql_ssl_ca:
            ssl_kwargs = {"ca": mysql_ssl_ca}
        elif mysql_ssl_mode in {"required", "require", "verify_ca", "verify_identity"}:
            ssl_kwargs = {}

        connect_kwargs = {
            "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "journal"),
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": False,
        }

        if ssl_kwargs is not None:
            connect_kwargs["ssl"] = ssl_kwargs

        return pymysql.connect(**connect_kwargs)

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    if DB_ENGINE == "mysql":
        _execute(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )

        _execute(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS journals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                mood VARCHAR(50),
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
        )
    else:
        _execute(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )

        _execute(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood TEXT,
                is_public BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """,
        )

    conn.commit()
    conn.close()

# User functions
def create_user(username, email, password):
    conn = get_db()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        _execute(
            cursor,
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except Exception as exc:
        conn.close()
        if isinstance(exc, sqlite3.IntegrityError) or exc.__class__.__name__ == "IntegrityError":
            return None
        raise

def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, 'SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, 'SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_password(user, password):
    return check_password_hash(user['password_hash'], password)

# Journal functions
def create_journal(user_id, title, content, mood, is_public):
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, '''
        INSERT INTO journals (user_id, title, content, mood, is_public)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, title, content, mood, is_public))
    conn.commit()
    journal_id = cursor.lastrowid
    conn.close()
    return journal_id

def get_journals_by_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, '''
        SELECT * FROM journals WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,))
    journals = cursor.fetchall()
    conn.close()
    return journals

def get_journal_by_id(journal_id):
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, '''
        SELECT j.*, u.username FROM journals j
        JOIN users u ON j.user_id = u.id
        WHERE j.id = ?
    ''', (journal_id,))
    journal = cursor.fetchone()
    conn.close()
    return journal

def update_journal(journal_id, title, content, mood, is_public):
    conn = get_db()
    cursor = conn.cursor()
    if DB_ENGINE == "mysql":
        _execute(
            cursor,
            '''
            UPDATE journals
            SET title = ?, content = ?, mood = ?, is_public = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (title, content, mood, is_public, journal_id),
        )
    else:
        _execute(
            cursor,
            '''
            UPDATE journals
            SET title = ?, content = ?, mood = ?, is_public = ?, updated_at = ?
            WHERE id = ?
            ''',
            (title, content, mood, is_public, datetime.now(), journal_id),
        )
    conn.commit()
    conn.close()

def delete_journal(journal_id):
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, 'DELETE FROM journals WHERE id = ?', (journal_id,))
    conn.commit()
    conn.close()

def get_public_journals():
    conn = get_db()
    cursor = conn.cursor()
    _execute(cursor, '''
        SELECT j.*, u.username FROM journals j
        JOIN users u ON j.user_id = u.id
        WHERE j.is_public = 1
        ORDER BY j.created_at DESC
    ''')
    journals = cursor.fetchall()
    conn.close()
    return journals

def get_journal_stats(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Total journals
    _execute(cursor, 'SELECT COUNT(*) AS total FROM journals WHERE user_id = ?', (user_id,))
    total = _scalar_value(cursor.fetchone())
    
    # Public journals
    _execute(
        cursor,
        'SELECT COUNT(*) AS public_count FROM journals WHERE user_id = ? AND is_public = 1',
        (user_id,),
    )
    public = _scalar_value(cursor.fetchone())
    
    # This month's journals
    if DB_ENGINE == "mysql":
        _execute(
            cursor,
            '''
            SELECT COUNT(*) AS this_month_count FROM journals
            WHERE user_id = ?
              AND YEAR(created_at) = YEAR(CURRENT_DATE)
              AND MONTH(created_at) = MONTH(CURRENT_DATE)
            ''',
            (user_id,),
        )
    else:
        _execute(
            cursor,
            '''
            SELECT COUNT(*) AS this_month_count FROM journals
            WHERE user_id = ? AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            ''',
            (user_id,),
        )
    this_month = _scalar_value(cursor.fetchone())
    
    # Mood distribution
    _execute(cursor, '''
        SELECT mood, COUNT(*) as count FROM journals 
        WHERE user_id = ? AND mood IS NOT NULL
        GROUP BY mood
    ''', (user_id,))
    moods = cursor.fetchall()
    
    conn.close()
    return {
        'total': total,
        'public': public,
        'private': total - public,
        'this_month': this_month,
        'moods': {row['mood']: row['count'] for row in moods}
    }
