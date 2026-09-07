import aiosqlite
from typing import Optional, Dict, Any, List
from config import DATABASE_PATH

async def init_db():
    """Initialize SQLite tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                string_session TEXT,
                self_user_id INTEGER,
                self_first_name TEXT,
                self_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS login_states (
                user_id INTEGER PRIMARY KEY,
                phone_number TEXT,
                phone_code_hash TEXT,
                step TEXT,
                session_string TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_tagging (
                chat_id INTEGER PRIMARY KEY,
                started_by INTEGER,
                tagger_user_id INTEGER,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorite_users (
                owner_id INTEGER,
                fav_user_id INTEGER,
                fav_first_name TEXT,
                fav_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (owner_id, fav_user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS saveit_settings (
                user_id INTEGER PRIMARY KEY,
                auto_save_timed INTEGER DEFAULT 1
            )
        """)

        await db.commit()



async def add_or_update_user(user_id: int, first_name: str, username: Optional[str]):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, first_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username
        """, (user_id, first_name, username))
        await db.commit()

async def set_user_session(user_id: int, string_session: str, self_user_id: int, self_first_name: str, self_username: Optional[str]):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, string_session, self_user_id, self_first_name, self_username)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                string_session = excluded.string_session,
                self_user_id = excluded.self_user_id,
                self_first_name = excluded.self_first_name,
                self_username = excluded.self_username
        """, (user_id, string_session, self_user_id, self_first_name, self_username))
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def remove_user_session(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET
                string_session = NULL,
                self_user_id = NULL,
                self_first_name = NULL,
                self_username = NULL
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()

async def get_all_users_with_sessions() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE string_session IS NOT NULL AND string_session != ''") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_total_users() -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 0

# --- Login flow states ---

async def save_login_state(user_id: int, phone_number: str, phone_code_hash: str, step: str, session_string: str = ""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO login_states (user_id, phone_number, phone_code_hash, step, session_string)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                phone_number = excluded.phone_number,
                phone_code_hash = excluded.phone_code_hash,
                step = excluded.step,
                session_string = excluded.session_string
        """, (user_id, phone_number, phone_code_hash, step, session_string))
        await db.commit()

async def get_login_state(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM login_states WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def clear_login_state(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM login_states WHERE user_id = ?", (user_id,))
        await db.commit()

# --- Active Tagging State ---

async def start_tagging_db(chat_id: int, started_by: int, tagger_user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO active_tagging (chat_id, started_by, tagger_user_id, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(chat_id) DO UPDATE SET
                started_by = excluded.started_by,
                tagger_user_id = excluded.tagger_user_id,
                is_active = 1
        """, (chat_id, started_by, tagger_user_id))
        await db.commit()

async def is_tagging_active_db(chat_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT is_active FROM active_tagging WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

async def stop_tagging_db(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE active_tagging SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        await db.commit()

# --- Favorite Users ---

async def add_favorite_user(owner_id: int, fav_user_id: int, fav_first_name: str, fav_username: Optional[str]):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO favorite_users (owner_id, fav_user_id, fav_first_name, fav_username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(owner_id, fav_user_id) DO UPDATE SET
                fav_first_name = excluded.fav_first_name,
                fav_username = excluded.fav_username
        """, (owner_id, fav_user_id, fav_first_name, fav_username))
        await db.commit()

async def remove_favorite_user(owner_id: int, fav_user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM favorite_users WHERE owner_id = ? AND fav_user_id = ?",
            (owner_id, fav_user_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def get_favorite_users(owner_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM favorite_users WHERE owner_id = ? ORDER BY created_at ASC",
            (owner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def clear_favorite_users(owner_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM favorite_users WHERE owner_id = ?", (owner_id,))
        await db.commit()

# --- Saveit Settings ---

async def get_saveit_setting(user_id: int) -> bool:
    """Check if auto-save timed media is enabled (default True)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT auto_save_timed FROM saveit_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

async def set_saveit_setting(user_id: int, auto_save: bool):
    """Set auto-save timed media enabled/disabled."""
    val = 1 if auto_save else 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO saveit_settings (user_id, auto_save_timed)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET auto_save_timed = excluded.auto_save_timed
        """, (user_id, val))
        await db.commit()


