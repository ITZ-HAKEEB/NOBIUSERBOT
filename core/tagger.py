import asyncio
import logging
import random
import html
from typing import Dict, Optional, List
from pyrogram import Client, enums, errors
from pyrogram.types import Message
import config
from database.db import start_tagging_db, stop_tagging_db

logger = logging.getLogger(__name__)

EMOJIS = [
    "🌟", "✨", "🔥", "🚀", "⚡", "💎", "💫", "🎯", "🎉", "👑",
    "🍕", "🍀", "🌸", "🦋", "🦄", "🌈", "🪐", "🏆", "🍉", "🎈",
    "🎸", "☀️", "🌙", "🌊", "🦁", "🐼", "🍒", "🔮", "🧿", "🪄"
]

class TaggerEngine:
    """Core tagging engine executing member mentions via Self ID."""

    def __init__(self):
        self.active_tasks: Dict[int, asyncio.Task] = {}  # chat_id -> Task
        self.stop_requested: Dict[int, bool] = {}        # chat_id -> bool

    def is_running(self, chat_id: int) -> bool:
        task = self.active_tasks.get(chat_id)
        return bool(task and not task.done())

    async def stop_tagging(self, chat_id: int) -> bool:
        """Signal an ongoing tagging process in a chat to stop."""
        if self.is_running(chat_id):
            self.stop_requested[chat_id] = True
            task = self.active_tasks.get(chat_id)
            if task and not task.done():
                task.cancel()
            await stop_tagging_db(chat_id)
            return True
        return False

    async def start_tagging(
        self,
        client: Client,
        chat_id: int,
        initiated_by: int,
        mode: str = "text",
        custom_text: str = "",
        reply_to_message_id: Optional[int] = None
    ) -> bool:
        """Start a tagging session in a chat."""
        if self.is_running(chat_id):
            return False

        self.stop_requested[chat_id] = False
        task = asyncio.create_task(
            self._tagging_worker(
                client=client,
                chat_id=chat_id,
                initiated_by=initiated_by,
                mode=mode,
                custom_text=custom_text,
                reply_to_message_id=reply_to_message_id
            )
        )
        self.active_tasks[chat_id] = task
        await start_tagging_db(chat_id, initiated_by, client.me.id if hasattr(client, "me") and client.me else 0)
        return True

    async def _tagging_worker(
        self,
        client: Client,
        chat_id: int,
        initiated_by: int,
        mode: str,
        custom_text: str,
        reply_to_message_id: Optional[int]
    ):
        tagged_count = 0
        batch: List[str] = []
        is_cancelled = False

        try:
            logger.info(f"Starting tagger in chat {chat_id} (mode: {mode}, text: '{custom_text}')")
            
            # Announce start
            start_banner = (
                f"🚀 **`[ Self ID Tagger Started! ]`**\n"
                f"📝 **`Mode:`** `{mode.upper()}`\n"
                f"💬 **`Message:`** `{custom_text or 'Default Mention'}`\n"
                f"💡 **`Type /stop or .stop anytime to cancel.`**"
            )
            try:
                await client.send_message(chat_id, start_banner, reply_to_message_id=reply_to_message_id)
            except Exception as e:
                logger.warning(f"Could not send start banner in {chat_id}: {e}")

            # Fetch members stream
            if mode == "fav":
                from database.db import get_favorite_users
                fav_users = await get_favorite_users(initiated_by)
                if not fav_users:
                    await client.send_message(
                        chat_id,
                        "⚠️ **`[ No Favorite Users Saved! ]`**\n\n"
                        "**`Add your favorite users first using /addfav @username or reply with /addfav.`**"
                    )
                    return

                async def _fav_gen():
                    for f in fav_users:
                        yield f["fav_user_id"], f["fav_first_name"]
                members_stream = _fav_gen()
            elif mode == "admin":
                async def _admin_gen():
                    async for m in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                        if m.user and not m.user.is_deleted:
                            yield m.user.id, m.user.first_name
                members_stream = _admin_gen()
            else:
                async def _all_gen():
                    async for m in client.get_chat_members(chat_id):
                        if m.user and not m.user.is_deleted and not m.user.is_bot:
                            yield m.user.id, m.user.first_name
                members_stream = _all_gen()

            delay = min(config.TAG_DELAY, 1.8) if mode == "fav" else config.TAG_DELAY

            async for uid, first_name in members_stream:
                if self.stop_requested.get(chat_id, False):
                    is_cancelled = True
                    break

                # Prepare mention in HTML format
                clean_name = html.escape((first_name or "Member").replace("<", "").replace(">", ""))
                mention = f'<a href="tg://user?id={uid}">{clean_name}</a>'
                batch.append(mention)

                if len(batch) >= config.USERS_PER_TAG:
                    if self.stop_requested.get(chat_id, False):
                        is_cancelled = True
                        break

                    await self._send_tag_batch(
                        client=client,
                        chat_id=chat_id,
                        batch=batch,
                        mode=mode,
                        custom_text=custom_text,
                        reply_to_message_id=reply_to_message_id
                    )
                    tagged_count += len(batch)
                    batch = []
                    await asyncio.sleep(delay)


            # Process remaining members in the last chunk
            if batch and not is_cancelled and not self.stop_requested.get(chat_id, False):
                await self._send_tag_batch(
                    client=client,
                    chat_id=chat_id,
                    batch=batch,
                    mode=mode,
                    custom_text=custom_text,
                    reply_to_message_id=reply_to_message_id
                )
                tagged_count += len(batch)

        except asyncio.CancelledError:
            is_cancelled = True
            logger.info(f"Tagging task cancelled for chat {chat_id}")
        except errors.ChatAdminRequired:
            try:
                await client.send_message(chat_id, "❌ **Error**: Need permission to view members list in this group.")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error in tagging loop {chat_id}: {e}", exc_info=True)
            try:
                await client.send_message(chat_id, f"⚠️ **Tagging encountered an error**: `{e}`")
            except Exception:
                pass
        finally:
            self.active_tasks.pop(chat_id, None)
            self.stop_requested.pop(chat_id, None)
            await stop_tagging_db(chat_id)

            # Send final report
            report = (
                f"🛑 **`[ Tagging stopped! Tagged {tagged_count} members. ]`**"
                if is_cancelled
                else f"✅ **`[ Tagging finished! Successfully tagged {tagged_count} members. ]`**"
            )
            try:
                await client.send_message(chat_id, report)
            except Exception:
                pass


    async def _send_tag_batch(
        self,
        client: Client,
        chat_id: int,
        batch: List[str],
        mode: str,
        custom_text: str,
        reply_to_message_id: Optional[int]
    ):
        """Constructs and delivers a single batch of mentions in HTML parse mode."""
        if len(batch) == 1:
            user_mention = batch[0]
            if mode == "fav":
                text = f"⭐ 💖 {user_mention} — {custom_text}".strip() if custom_text else f"⭐ 💖 {user_mention}!"
            elif mode == "emoji":
                emoji = random.choice(EMOJIS)
                text = f"{emoji} {user_mention} {custom_text}".strip() if custom_text else f"{emoji} {user_mention}"
            elif mode == "admin":
                text = f"🚨 👮‍♂️ {user_mention} — {custom_text}" if custom_text else f"🚨 👮‍♂️ {user_mention}"
            else:
                text = f"{custom_text} {user_mention}".strip() if custom_text else user_mention
        else:
            if mode == "fav":
                mentions_str = " ".join([f"⭐ {m}" for m in batch])
                text = f"💖 <b>Favorites:</b> {custom_text}\n\n{mentions_str}" if custom_text else f"💖 <b>Favorites:</b>\n\n{mentions_str}"
            elif mode == "emoji":
                mentions_str = " ".join([f"{random.choice(EMOJIS)} {m}" for m in batch])
                text = f"{custom_text}\n\n{mentions_str}" if custom_text else mentions_str
            elif mode == "admin":
                mentions_str = "\n".join([f"👮‍♂️ {m}" for m in batch])
                text = f"🚨 <b>Admins Call:</b> {custom_text}\n\n{mentions_str}" if custom_text else f"🚨 <b>Admins:</b>\n\n{mentions_str}"
            else:
                mentions_str = ", ".join(batch)
                text = f"{custom_text}\n\n{mentions_str}" if custom_text else mentions_str

        while True:
            try:
                await client.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_to_message_id=reply_to_message_id
                )
                break
            except errors.FloodWait as e:
                wait_time = e.value + 1
                logger.warning(f"FloodWait hit in {chat_id}: sleeping {wait_time}s")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.warning(f"Failed sending batch in HTML parse mode ({e}), retrying with disabled parse mode")
                try:
                    await client.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=enums.ParseMode.DISABLED,
                        disable_web_page_preview=True,
                        reply_to_message_id=reply_to_message_id
                    )
                except Exception as final_e:
                    logger.error(f"Failed to send batch in {chat_id}: {final_e}")
                break

tagger_engine = TaggerEngine()
