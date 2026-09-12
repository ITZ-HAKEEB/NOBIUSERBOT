import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from config import DATABASE_PATH, MONGO_URL, DB_NAME

logger = logging.getLogger(__name__)

# State for MongoDB
_mongo_client = None
_mongo_db = None
_is_mongo = False


def is_mongo_active() -> bool:
    return bool(_is_mongo and _mongo_db is not None)


async def init_db():
    """Initialize MongoDB Atlas or fallback to SQLite."""
    global _mongo_client, _mongo_db, _is_mongo

    if MONGO_URL and "<" not in MONGO_URL and ">" not in MONGO_URL:
        try:
            import motor.motor_asyncio
            _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGO_URL,
                serverSelectionTimeoutMS=5000
            )
            _mongo_db = _mongo_client[DB_NAME]
            # Ping to confirm connection
            await _mongo_db.command("ping")
            _is_mongo = True
            logger.info("Successfully connected to MongoDB Atlas (DB: %s)", DB_NAME)

            # Ensure indexes
            await _mongo_db.users.create_index("user_id", unique=True)
            await _mongo_db.login_states.create_index("user_id", unique=True)
            await _mongo_db.active_tagging.create_index("chat_id", unique=True)
            await _mongo_db.favorite_users.create_index([("owner_id", 1), ("fav_user_id", 1)], unique=True)
            await _mongo_db.saveit_settings.create_index("user_id", unique=True)
            await _mongo_db.auto_message_settings.create_index("user_id", unique=True)
            await _mongo_db.auto_message_history.create_index([("assistant_id", 1), ("peer_id", 1)], unique=True)
            return
        except Exception as e:
            logger.warning("MongoDB connection failed (%s), falling back to SQLite", e)
            _is_mongo = False
            _mongo_client = None
            _mongo_db = None

    # SQLite fallback
    import aiosqlite
    logger.info("Using SQLite database at %s", DATABASE_PATH)
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS auto_message_settings (
                user_id INTEGER PRIMARY KEY,
                message TEXT,
                is_enabled INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS auto_message_history (
                assistant_id INTEGER,
                peer_id INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (assistant_id, peer_id)
            )
        """)

        await db.commit()


# --- Users ---

async def add_or_update_user(user_id: int, first_name: str, username: Optional[str]):
    if is_mongo_active():
        await _mongo_db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "first_name": first_name,
                    "username": username,
                },
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        return

    import aiosqlite
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
    if is_mongo_active():
        await _mongo_db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "string_session": string_session,
                    "self_user_id": self_user_id,
                    "self_first_name": self_first_name,
                    "self_username": self_username
                }
            },
            upsert=True
        )
        return

    import aiosqlite
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
    if is_mongo_active():
        doc = await _mongo_db.users.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
        return doc

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def remove_user_session(user_id: int):
    if is_mongo_active():
        await _mongo_db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "string_session": None,
                    "self_user_id": None,
                    "self_first_name": None,
                    "self_username": None
                }
            }
        )
        return

    import aiosqlite
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
    if is_mongo_active():
        cursor = _mongo_db.users.find({
            "string_session": {"$exists": True, "$ne": None, "$nin": ["", None]}
        })
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE string_session IS NOT NULL AND string_session != ''") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_total_users() -> int:
    if is_mongo_active():
        return await _mongo_db.users.count_documents({})

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 0


# --- Login flow states ---

async def save_login_state(user_id: int, phone_number: str, phone_code_hash: str, step: str, session_string: str = ""):
    if is_mongo_active():
        await _mongo_db.login_states.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "phone_number": phone_number,
                    "phone_code_hash": phone_code_hash,
                    "step": step,
                    "session_string": session_string
                }
            },
            upsert=True
        )
        return

    import aiosqlite
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
    if is_mongo_active():
        doc = await _mongo_db.login_states.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
        return doc

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM login_states WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def clear_login_state(user_id: int):
    if is_mongo_active():
        await _mongo_db.login_states.delete_one({"user_id": user_id})
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM login_states WHERE user_id = ?", (user_id,))
        await db.commit()


# --- Active Tagging State ---

async def start_tagging_db(chat_id: int, started_by: int, tagger_user_id: int):
    if is_mongo_active():
        await _mongo_db.active_tagging.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "chat_id": chat_id,
                    "started_by": started_by,
                    "tagger_user_id": tagger_user_id,
                    "is_active": 1
                }
            },
            upsert=True
        )
        return

    import aiosqlite
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
    if is_mongo_active():
        doc = await _mongo_db.active_tagging.find_one({"chat_id": chat_id})
        return bool(doc and doc.get("is_active") == 1)

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT is_active FROM active_tagging WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)


async def stop_tagging_db(chat_id: int):
    if is_mongo_active():
        await _mongo_db.active_tagging.update_one(
            {"chat_id": chat_id},
            {"$set": {"is_active": 0}}
        )
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE active_tagging SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        await db.commit()


# --- Favorite Users ---

async def add_favorite_user(owner_id: int, fav_user_id: int, fav_first_name: str, fav_username: Optional[str]):
    if is_mongo_active():
        await _mongo_db.favorite_users.update_one(
            {"owner_id": owner_id, "fav_user_id": fav_user_id},
            {
                "$set": {
                    "owner_id": owner_id,
                    "fav_user_id": fav_user_id,
                    "fav_first_name": fav_first_name,
                    "fav_username": fav_username,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        return

    import aiosqlite
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
    if is_mongo_active():
        res = await _mongo_db.favorite_users.delete_one({"owner_id": owner_id, "fav_user_id": fav_user_id})
        return res.deleted_count > 0

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM favorite_users WHERE owner_id = ? AND fav_user_id = ?",
            (owner_id, fav_user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_favorite_users(owner_id: int) -> List[Dict[str, Any]]:
    if is_mongo_active():
        cursor = _mongo_db.favorite_users.find({"owner_id": owner_id}).sort("created_at", 1)
        favs = []
        async for doc in cursor:
            doc.pop("_id", None)
            favs.append(doc)
        return favs

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM favorite_users WHERE owner_id = ? ORDER BY created_at ASC",
            (owner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def clear_favorite_users(owner_id: int):
    if is_mongo_active():
        await _mongo_db.favorite_users.delete_many({"owner_id": owner_id})
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM favorite_users WHERE owner_id = ?", (owner_id,))
        await db.commit()


# --- Saveit Settings ---

async def get_saveit_setting(user_id: int) -> bool:
    """Check if auto-save timed media is enabled (default True)."""
    if is_mongo_active():
        doc = await _mongo_db.saveit_settings.find_one({"user_id": user_id})
        return bool(doc.get("auto_save_timed", 1)) if doc else True

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT auto_save_timed FROM saveit_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True


async def set_saveit_setting(user_id: int, auto_save: bool):
    """Set auto-save timed media enabled/disabled."""
    val = 1 if auto_save else 0
    if is_mongo_active():
        await _mongo_db.saveit_settings.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "auto_save_timed": val}},
            upsert=True
        )
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO saveit_settings (user_id, auto_save_timed)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET auto_save_timed = excluded.auto_save_timed
        """, (user_id, val))
        await db.commit()


# --- Auto Message Settings & History ---

DEFAULT_AUTO_MESSAGE = (
    "Hello {name}! 👋\n\n"
    "Thanks for reaching out! I received your message and will get back to you as soon as possible.\n\n"
    "*(Automated Response)*"
)


async def get_auto_message_settings(user_id: int) -> Dict[str, Any]:
    """Get auto-responder settings for a user (message and enabled status)."""
    default_res = {
        "user_id": user_id,
        "message": DEFAULT_AUTO_MESSAGE,
        "is_enabled": True,
        "is_custom": False
    }
    if is_mongo_active():
        doc = await _mongo_db.auto_message_settings.find_one({"user_id": user_id})
        if not doc:
            # Check if this user_id is linked to another user_id or self_user_id
            user_doc = await _mongo_db.users.find_one({"$or": [{"user_id": user_id}, {"self_user_id": user_id}]})
            if user_doc:
                alt_id = user_doc.get("user_id") if user_doc.get("self_user_id") == user_id else user_doc.get("self_user_id")
                if alt_id and alt_id != user_id:
                    doc = await _mongo_db.auto_message_settings.find_one({"user_id": alt_id})

        if doc:
            custom_msg = doc.get("message")
            return {
                "user_id": user_id,
                "message": custom_msg if custom_msg else DEFAULT_AUTO_MESSAGE,
                "is_enabled": bool(doc.get("is_enabled", 1)),
                "is_custom": bool(custom_msg)
            }
        return default_res

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM auto_message_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            async with db.execute("SELECT user_id, self_user_id FROM users WHERE user_id = ? OR self_user_id = ?", (user_id, user_id)) as cursor:
                u_row = await cursor.fetchone()
                if u_row:
                    alt_id = u_row["user_id"] if u_row["self_user_id"] == user_id else u_row["self_user_id"]
                    if alt_id and alt_id != user_id:
                        async with db.execute("SELECT * FROM auto_message_settings WHERE user_id = ?", (alt_id,)) as alt_cursor:
                            row = await alt_cursor.fetchone()

        if row:
            custom_msg = row["message"]
            return {
                "user_id": user_id,
                "message": custom_msg if custom_msg else DEFAULT_AUTO_MESSAGE,
                "is_enabled": bool(row["is_enabled"]),
                "is_custom": bool(custom_msg)
            }
        return default_res



async def set_auto_message_text(user_id: int, message: str):
    """Set custom auto-responder message for user."""
    if is_mongo_active():
        await _mongo_db.auto_message_settings.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "message": message}},
            upsert=True
        )
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO auto_message_settings (user_id, message)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET message = excluded.message
        """, (user_id, message))
        await db.commit()


async def reset_auto_message_text(user_id: int):
    """Reset auto-responder message to default."""
    if is_mongo_active():
        await _mongo_db.auto_message_settings.update_one(
            {"user_id": user_id},
            {"$set": {"message": None}}
        )
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE auto_message_settings SET message = NULL WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def set_auto_message_enabled(user_id: int, is_enabled: bool):
    """Enable or disable auto-responder."""
    val = 1 if is_enabled else 0
    if is_mongo_active():
        await _mongo_db.auto_message_settings.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "is_enabled": val}},
            upsert=True
        )
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO auto_message_settings (user_id, is_enabled)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET is_enabled = excluded.is_enabled
        """, (user_id, val))
        await db.commit()


async def has_received_auto_message(assistant_id: int, peer_id: int) -> bool:
    """Check if this peer has already received an auto-message from this assistant."""
    if is_mongo_active():
        doc = await _mongo_db.auto_message_history.find_one({
            "assistant_id": assistant_id,
            "peer_id": peer_id
        })
        return doc is not None

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM auto_message_history WHERE assistant_id = ? AND peer_id = ?",
            (assistant_id, peer_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def mark_auto_message_sent(assistant_id: int, peer_id: int):
    """Record that an auto-message has been sent to this peer by this assistant."""
    if is_mongo_active():
        await _mongo_db.auto_message_history.update_one(
            {"assistant_id": assistant_id, "peer_id": peer_id},
            {
                "$set": {
                    "assistant_id": assistant_id,
                    "peer_id": peer_id,
                    "sent_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        return

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO auto_message_history (assistant_id, peer_id)
            VALUES (?, ?)
            ON CONFLICT(assistant_id, peer_id) DO UPDATE SET sent_at = CURRENT_TIMESTAMP
        """, (assistant_id, peer_id))
        await db.commit()


async def clear_auto_message_history(assistant_id: int) -> int:
    """Clear the sent history for this assistant so contacts can be greeted again."""
    if is_mongo_active():
        res = await _mongo_db.auto_message_history.delete_many({"assistant_id": assistant_id})
        return res.deleted_count

    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM auto_message_history WHERE assistant_id = ?", (assistant_id,))
        await db.commit()
        return cursor.rowcount

