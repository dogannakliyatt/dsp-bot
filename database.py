import sqlite3
import os

DB_NAME = "database.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                new_nick TEXT,
                parti_name TEXT,
                parti_code TEXT,
                rp_name TEXT,
                rp_code TEXT,
                roles_given TEXT,
                staff_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poll_candidates (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                votes INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poll_votes (
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (poll_id, user_id)
            )
        ''')
        conn.commit()

def add_register(user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registers (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id))
        conn.commit()

def get_top_staff():
    with get_connection() as conn:
        cursor = conn.cursor()
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO polls (title, channel_id) VALUES (?, ?)", (title, channel_id))
        poll_id = cursor.lastrowid
        conn.commit()
        return poll_id

def set_poll_message_id(poll_id, message_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE polls SET message_id = ? WHERE poll_id = ?", (message_id, poll_id))
        conn.commit()

def get_active_polls():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT poll_id, title, channel_id, message_id FROM polls WHERE status = 'active'")
        return cursor.fetchall()

def get_poll_by_id(poll_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT poll_id, title, channel_id, message_id, status FROM polls WHERE poll_id = ?", (poll_id,))
        return cursor.fetchone()

def add_candidate(poll_id, name):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO poll_candidates (poll_id, name) VALUES (?, ?)", (poll_id, name))
        conn.commit()

def get_candidates(poll_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT candidate_id, name, votes FROM poll_candidates WHERE poll_id = ?", (poll_id,))
        return cursor.fetchall()

def has_voted(poll_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
        return cursor.fetchone() is not None

def cast_vote(poll_id, user_id, candidate_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO poll_votes (poll_id, user_id) VALUES (?, ?)", (poll_id, user_id))
            cursor.execute("UPDATE poll_candidates SET votes = votes + 1 WHERE candidate_id = ?", (candidate_id,))
            conn.commit()
            return True
    except sqlite3.Error:
        return False

def close_poll(poll_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE polls SET status = 'ended' WHERE poll_id = ?", (poll_id,))
        conn.commit()

def delete_poll(poll_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM polls WHERE poll_id = ?", (poll_id,))
        cursor.execute("DELETE FROM poll_candidates WHERE poll_id = ?", (poll_id,))
        cursor.execute("DELETE FROM poll_votes WHERE poll_id = ?", (poll_id,))
        conn.commit()

# Otomatik Başlatma
init_db()
