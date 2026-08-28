import os
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None

def get_pool():
    global _pool
    if _pool is None and DATABASE_URL:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL,
            cursor_factory=RealDictCursor
        )
    return _pool

@contextmanager
def get_db_cursor(commit: bool = False):
    pool_obj = get_pool()
    if not pool_obj:
        raise ValueError("DATABASE_URL ortam değişkeni bulunamadı veya bağlantı havuzu oluşturulamadı!")
    
    conn = pool_obj.getconn()
    try:
        with conn.cursor() as cursor:
            yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool_obj.putconn(conn)

def init_db():
    if not DATABASE_URL:
        return
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registers (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                username TEXT,
                new_nick TEXT,
                parti_name TEXT,
                parti_code TEXT,
                rp_name TEXT,
                rp_code TEXT,
                roles_given TEXT,
                staff_id BIGINT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                poll_id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                channel_id BIGINT NOT NULL,
                message_id BIGINT DEFAULT 0,
                status TEXT DEFAULT 'active'
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poll_candidates (
                candidate_id SERIAL PRIMARY KEY,
                poll_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                votes INTEGER DEFAULT 0
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poll_votes (
                poll_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                PRIMARY KEY (poll_id, user_id)
            );
        ''')

def add_register(user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            INSERT INTO registers (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id))

def get_top_staff():
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('''
            SELECT staff_id, COUNT(*) as count 
            FROM registers 
            WHERE staff_id IS NOT NULL 
            GROUP BY staff_id 
            ORDER BY count DESC
        ''')
        return cursor.fetchall()

# --- OYLAMA SİSTEMİ VERİTABANI İŞLEMLERİ ---

def add_poll(title, channel_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO polls (title, channel_id) VALUES (%s, %s) RETURNING poll_id", (title, channel_id))
        return cursor.fetchone()["poll_id"]

def set_poll_message_id(poll_id, message_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE polls SET message_id = %s WHERE poll_id = %s", (message_id, poll_id))

def get_active_polls():
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT poll_id, title, channel_id, message_id FROM polls WHERE status = 'active'")
        return cursor.fetchall()

def get_poll_by_id(poll_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT poll_id, title, channel_id, message_id, status FROM polls WHERE poll_id = %s", (poll_id,))
        return cursor.fetchone()

def add_candidate(poll_id, name):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO poll_candidates (poll_id, name) VALUES (%s, %s)", (poll_id, name))

def get_candidates(poll_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT candidate_id, name, votes FROM poll_candidates WHERE poll_id = %s", (poll_id,))
        return cursor.fetchall()

def has_voted(poll_id, user_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT 1 FROM poll_votes WHERE poll_id = %s AND user_id = %s", (poll_id, user_id))
        return cursor.fetchone() is not None

def cast_vote(poll_id, user_id, candidate_id):
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT INTO poll_votes (poll_id, user_id) VALUES (%s, %s)", (poll_id, user_id))
            cursor.execute("UPDATE poll_candidates SET votes = votes + 1 WHERE candidate_id = %s", (candidate_id,))
            return True
    except Exception:
        return False

def close_poll(poll_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE polls SET status = 'ended' WHERE poll_id = %s", (poll_id,))

def delete_poll(poll_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM polls WHERE poll_id = %s", (poll_id,))
        cursor.execute("DELETE FROM poll_candidates WHERE poll_id = %s", (poll_id,))
        cursor.execute("DELETE FROM poll_votes WHERE poll_id = %s", (poll_id,))

try:
    init_db()
except Exception as e:
    print(f"[DB INIT ERROR] {e}")
