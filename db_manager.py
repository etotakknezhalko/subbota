import sqlite3
import os

PATH_DB = 'database/db.db'

def init_db():
    if not os.path.exists('database'):
        os.makedirs('database')
    # Добавляем timeout для стабильной работы в потоках
    with sqlite3.connect(PATH_DB, timeout=20) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS game_session (
            session_id TEXT PRIMARY KEY,
            p1_choice TEXT,
            p2_choice TEXT,
            attacker_side TEXT,
            p1_id INTEGER,
            p2_id INTEGER
        )''')

def create_session(session_id, attacker_side):
    with sqlite3.connect(PATH_DB, timeout=20) as conn:
        conn.execute("INSERT OR REPLACE INTO game_session (session_id, attacker_side) VALUES (?, ?)", 
                     (session_id, attacker_side))

def set_choice(session_id, player_num, choice):
    field = "p1_choice" if player_num == 1 else "p2_choice"
    with sqlite3.connect(PATH_DB, timeout=20) as conn:
        res = conn.execute(f"SELECT {field} FROM game_session WHERE session_id = ?", (session_id,)).fetchone()
        if res and res[0] is None:
            conn.execute(f"UPDATE game_session SET {field} = ? WHERE session_id = ?", (choice, session_id))
            return True
    return False

def get_session_data(session_id):
    with sqlite3.connect(PATH_DB, timeout=20) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM game_session WHERE session_id = ?", (session_id,)).fetchone()

def clear_choices(session_id, next_attacker_side):
    with sqlite3.connect(PATH_DB, timeout=20) as conn:
        conn.execute("UPDATE game_session SET p1_choice = NULL, p2_choice = NULL, attacker_side = ? WHERE session_id = ?", 
                     (next_attacker_side, session_id))