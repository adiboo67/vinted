import sqlite3
import os
from datetime import datetime

DB_FILE = "vinted_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    # Table pour les utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            webhook_url TEXT,
            search_url TEXT,
            max_price REAL,
            filters TEXT,
            scan_interval INTEGER,
            auto_message TEXT,
            last_scan REAL
        )
    ''')
    # Table pour l'historique personnel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_items (
            discord_id TEXT,
            item_id TEXT,
            date_seen TIMESTAMP,
            PRIMARY KEY (discord_id, item_id)
        )
    ''')
    conn.commit()
    return conn

# ----- GETTERS -----
def get_all_users(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    columns = [col[0] for col in cursor.description]
    users = []
    for row in cursor.fetchall():
        users.append(dict(zip(columns, row)))
    return users

def get_user(conn, discord_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE discord_id = ?", (str(discord_id),))
    row = cursor.fetchone()
    if row:
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))
    return None

# ----- SETTERS -----
def create_profile(conn, discord_id):
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (discord_id, max_price, scan_interval, last_scan) VALUES (?, 0, 60, 0)", (str(discord_id),))
    conn.commit()

def update_user_field(conn, discord_id, field, value):
    # Sécurisé car 'field' est contrôlé par notre code dans discord_commander
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE discord_id = ?", (value, str(discord_id)))
    conn.commit()

def update_last_scan(conn, discord_id, current_time):
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_scan = ? WHERE discord_id = ?", (current_time, str(discord_id)))
    conn.commit()

# ----- SEEN ITEMS -----
def is_item_seen(conn, discord_id, item_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_items WHERE discord_id = ? AND item_id = ?", (str(discord_id), str(item_id)))
    return cursor.fetchone() is not None

def mark_item_seen(conn, discord_id, item_id):
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO seen_items (discord_id, item_id, date_seen) VALUES (?, ?, ?)", 
                   (str(discord_id), str(item_id), datetime.now().isoformat()))
    conn.commit()
