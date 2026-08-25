import sqlite3
import os

DB_NAME = "dsp_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            nickname TEXT NOT NULL,
            parti_makam TEXT NOT NULL,
            parti_kisaltma TEXT NOT NULL,
            rp_makam TEXT NOT NULL,
            rp_kisaltma TEXT NOT NULL,
            given_roles TEXT NOT NULL,
            staff_id INTEGER NOT NULL,
            register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_register(user_id, username, nickname, parti_makam, parti_kisaltma, rp_makam, rp_kisaltma, given_roles, staff_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO registers (user_id, username, nickname, parti_makam, parti_kisaltma, rp_makam, rp_kisaltma, given_roles, staff_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, nickname, parti_makam, parti_kisaltma, rp_makam, rp_kisaltma, given_roles, staff_id))
    conn.commit()
    conn.close()

def get_top_staff():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT staff_id, COUNT(id) as total FROM registers
        GROUP BY staff_id ORDER BY total DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows
# --- OYLAMA SİSTEMİ VERİTABANI İŞLEMLERİ ---

def init_poll_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Oylamalar Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Adaylar Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poll_candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    ''')
    
    # Kullanılan Oylar Tablosu (Tek oy kontrolü için)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poll_votes (
            poll_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (poll_id, user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_poll(title, channel_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO polls (title, channel_id) VALUES (?, ?)", (title, channel_id))
    poll_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return poll_id

def set_poll_message_id(poll_id, message_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE polls SET message_id = ? WHERE poll_id = ?", (message_id, poll_id))
    conn.commit()
    conn.close()

def get_active_polls():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT poll_id, title, channel_id, message_id FROM polls WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_poll_by_id(poll_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT poll_id, title, channel_id, message_id, status FROM polls WHERE poll_id = ?", (poll_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def add_candidate(poll_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO poll_candidates (poll_id, name) VALUES (?, ?)", (poll_id, name))
    conn.commit()
    conn.close()

def get_candidates(poll_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT candidate_id, name, votes FROM poll_candidates WHERE poll_id = ?", (poll_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def remove_candidate(candidate_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM poll_candidates WHERE candidate_id = ?", (candidate_id,))
    conn.commit()
    conn.close()

def has_voted(poll_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def cast_vote(poll_id, user_id, candidate_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO poll_votes (poll_id, user_id) VALUES (?, ?)", (poll_id, user_id))
        cursor.execute("UPDATE poll_candidates SET votes = votes + 1 WHERE candidate_id = ?", (candidate_id,))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def close_poll(poll_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE polls SET status = 'ended' WHERE poll_id = ?", (poll_id,))
    conn.commit()
    conn.close()

def delete_poll(poll_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM polls WHERE poll_id = ?", (poll_id,))
    cursor.execute("DELETE FROM poll_candidates WHERE poll_id = ?", (poll_id,))
    cursor.execute("DELETE FROM poll_votes WHERE poll_id = ?", (poll_id,))
    conn.commit()
    conn.close()
