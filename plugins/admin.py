import time
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import config
from database.db import get_total_users, get_all_users_with_sessions
from core.client_manager import client_manager
from core.tagger import tagger_engine

logger = logging.getLogger(__name__)

def is_owner(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id == config.OWNER_ID

owner_filter = filters.create(is_owner)

@Client.on_message(filters.command("ping"))
async def ping_handler(bot: Client, message: Message):
    start = time.perf_counter()
    reply = await message.reply_text("🏓 **Pinging...**")
    end = time.perf_counter()
    latency_ms = round((end - start) * 1000, 2)
    await reply.edit_text(f"🏓 **Pong!** `{latency_ms}ms`")


@Client.on_message(filters.command("stats") & owner_filter)
async def stats_handler(bot: Client, message: Message):
    """View bot and system statistics."""
    total_users = await get_total_users()
    sessions = await get_all_users_with_sessions()
    active_in_mem = len([c for c in client_manager.clients.values() if c.is_connected])
    active_tagging_runs = len([t for t in tagger_engine.active_tasks.values() if not t.done()])

    stats_msg = (
        f"📊 **Self ID Tagger Bot Statistics**\n\n"
        f"👥 **Total Registered Users**: `{total_users}`\n"
        f"💾 **Saved Self ID Sessions**: `{len(sessions)}`\n"
        f"🟢 **Live Connected Clients**: `{active_in_mem}`\n"
        f"⚡ **Active Tagging Jobs**: `{active_tagging_runs}`\n"
        f"⚙️ **Tag Delay**: `{config.TAG_DELAY}s`\n"
        f"👥 **Users Per Tag**: `{config.USERS_PER_TAG}`"
    )
    await message.reply_text(stats_msg)


@Client.on_message(filters.command("broadcast") & owner_filter)
async def broadcast_handler(bot: Client, message: Message):
    """Broadcast an announcement to all users."""
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("⚠️ Reply to a message or provide text: `/broadcast <message>`")

    status = await message.reply_text("📢 **Broadcasting message...**")
    all_users = await get_all_users_with_sessions()
    # Also fetch all users from db
    import aiosqlite
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            user_rows = await cursor.fetchall()

    success, failed = 0, 0
    for row in user_rows:
        uid = row[0]
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(uid)
            else:
                text = message.text.split(None, 1)[1]
                await bot.send_message(uid, text)
            success += 1
        except Exception:
            failed += 1

    await status.edit_text(
        f"📢 **Broadcast Finished!**\n\n"
        f"✅ Sent: `{success}`\n"
        f"❌ Failed: `{failed}`"
    )
