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
