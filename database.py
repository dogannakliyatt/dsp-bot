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
                status TEXT DEFAULT 'active',
                target_role_id BIGINT DEFAULT NULL
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
                candidate_id INTEGER,
                PRIMARY KEY (poll_id, user_id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS giveaways (
                giveaway_id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                message_id BIGINT DEFAULT 0,
                prize TEXT NOT NULL,
                winners_count INTEGER DEFAULT 1,
                end_time TIMESTAMP NOT NULL,
                host_id BIGINT NOT NULL,
                requirements TEXT,
                status TEXT DEFAULT 'active'
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS giveaway_participants (
                giveaway_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                PRIMARY KEY (giveaway_id, user_id)
            );
        ''')

        cursor.execute('''
            ALTER TABLE polls ADD COLUMN IF NOT EXISTS target_role_id BIGINT DEFAULT NULL;
            ALTER TABLE poll_votes ADD COLUMN IF NOT EXISTS candidate_id INTEGER DEFAULT NULL;
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_stats_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        ''')
        cursor.execute('''
            INSERT INTO server_stats_settings (key, value)
            VALUES ('ideology', 'Sosyal Demokrasi'), ('compass', 'Merkez Sol')
            ON CONFLICT (key) DO NOTHING;
        ''')

def add_register(user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            INSERT INTO registers (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id))

def add_migrated_register(user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id, timestamp):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            SELECT id FROM registers 
            WHERE user_id = %s AND timestamp = %s
        ''', (user_id, timestamp))
        existing = cursor.fetchone()
        
        if existing:
            if staff_id is not None:
                cursor.execute('''
                    UPDATE registers 
                    SET staff_id = %s, parti_name = %s, parti_code = %s, rp_name = %s, rp_code = %s, roles_given = %s
                    WHERE id = %s
                ''', (staff_id, parti_name, parti_code, rp_name, rp_code, roles_given, existing["id"]))
            return False

        cursor.execute('''
            INSERT INTO registers (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, username, new_nick, parti_name, parti_code, rp_name, rp_code, roles_given, staff_id, timestamp))
        return True

def clear_empty_migrated_registers():
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            DELETE FROM registers 
            WHERE staff_id IS NULL AND parti_name LIKE '%Eski Kayıt%'
        ''')

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

def get_weekly_staff_stats():
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('''
            SELECT staff_id, COUNT(*) as count 
            FROM registers 
            WHERE staff_id IS NOT NULL AND timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY staff_id 
            ORDER BY count DESC
        ''')
        return cursor.fetchall()

def get_user_history(user_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT * FROM registers WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
        return cursor.fetchall()

def export_all_registers():
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT id, user_id, username, new_nick, parti_name, rp_name, roles_given, staff_id, timestamp FROM registers ORDER BY id ASC")
        return cursor.fetchall()

# --- OYLAMA SİSTEMİ VERİTABANI İŞLEMLERİ ---

def add_poll(title, channel_id, target_role_id=None):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO polls (title, channel_id, target_role_id) VALUES (%s, %s, %s) RETURNING poll_id", (title, channel_id, target_role_id))
        return cursor.fetchone()["poll_id"]

def set_poll_message_id(poll_id, message_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE polls SET message_id = %s WHERE poll_id = %s", (message_id, poll_id))

def get_active_polls():
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT poll_id, title, channel_id, message_id, target_role_id FROM polls WHERE status = 'active'")
        return cursor.fetchall()

def get_poll_by_id(poll_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT poll_id, title, channel_id, message_id, status, target_role_id FROM polls WHERE poll_id = %s", (poll_id,))
        return cursor.fetchone()

def add_candidate(poll_id, name):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO poll_candidates (poll_id, name) VALUES (%s, %s)", (poll_id, name))

def remove_candidate(poll_id, candidate_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM poll_candidates WHERE poll_id = %s AND candidate_id = %s", (poll_id, candidate_id))
        cursor.execute("DELETE FROM poll_votes WHERE poll_id = %s AND candidate_id = %s", (poll_id, candidate_id))

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
            cursor.execute("INSERT INTO poll_votes (poll_id, user_id, candidate_id) VALUES (%s, %s, %s)", (poll_id, user_id, candidate_id))
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

# --- ÇEKİLİŞ SİSTEMİ VERİTABANI İŞLEMLERİ ---

def create_db_giveaway(guild_id, channel_id, prize, winners_count, end_time, host_id, requirements):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            INSERT INTO giveaways (guild_id, channel_id, prize, winners_count, end_time, host_id, requirements)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING giveaway_id
        ''', (guild_id, channel_id, prize, winners_count, end_time, host_id, requirements))
        return cursor.fetchone()["giveaway_id"]

def set_giveaway_message_id(giveaway_id, message_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE giveaways SET message_id = %s WHERE giveaway_id = %s", (message_id, giveaway_id))

def get_active_giveaway(guild_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT * FROM giveaways WHERE guild_id = %s AND status = 'active'", (guild_id,))
        return cursor.fetchone()

def update_giveaway_data(giveaway_id, prize, winners_count, end_time, requirements):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            UPDATE giveaways 
            SET prize = %s, winners_count = %s, end_time = %s, requirements = %s
            WHERE giveaway_id = %s
        ''', (prize, winners_count, end_time, requirements, giveaway_id))

def end_db_giveaway(giveaway_id, status='ended'):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE giveaways SET status = %s WHERE giveaway_id = %s", (status, giveaway_id))

def add_giveaway_participant(giveaway_id, user_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO giveaway_participants (giveaway_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (giveaway_id, user_id))

def remove_giveaway_participant(giveaway_id, user_id):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM giveaway_participants WHERE giveaway_id = %s AND user_id = %s", (giveaway_id, user_id))

def get_giveaway_participants(giveaway_id):
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT user_id FROM giveaway_participants WHERE giveaway_id = %s", (giveaway_id,))
        return [row["user_id"] for row in cursor.fetchall()]

# --- İSTATİSTİK VE BİLGİ KANALLARI AYARLARI ---

def get_stat_setting(key: str, default: str = "") -> str:
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT value FROM server_stats_settings WHERE key = %s", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_stat_setting(key: str, value: str):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute('''
            INSERT INTO server_stats_settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        ''', (key, value))

try:
    init_db()
except Exception as e:
    print(f"[DB INIT ERROR] {e}")
