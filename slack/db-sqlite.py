import os
import sqlite3
import time
from typing import Optional
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()
db_path = "api_keys.db"

FERNET = Fernet(os.getenv("enc_key").encode())

def encrypt_api_key(api_key: str) -> str:
    return FERNET.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    return FERNET.decrypt(encrypted_key.encode()).decode()
def get_connection():
    return sqlite3.connect(db_path,check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_api_keys (
                user_id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                flavor_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        conn.commit()

def store_key(user_id: int,flavor_id:int, api_key: str):
    created_at = int(time.time())
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_api_keys (user_id, api_key,flavor_id, created_at)
            VALUES(?,?,?,?)
            ON CONFLICT(user_id)
            DO UPDATE SET api_key = excluded.api_key,
                          created_at = excluded.created_at        
        """,(user_id,encrypt_api_key(api_key),flavor_id,created_at))
        conn.commit()

def get_api_key(user_id:int) -> Optional[str]:
    with get_connection() as conn:
        cur = conn.execute("SELECT api_key, flavor_id FROM user_api_keys WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return [row[1],decrypt_api_key(row[0])] if row else None

def del_api_key(user_id:int):
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM user_api_keys WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()