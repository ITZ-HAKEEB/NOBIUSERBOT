import asyncio
import logging
from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import Message
import config
from database.db import get_user, get_all_users_with_sessions

logger = logging.getLogger(__name__)

class ClientManager:
    """Manages active Pyrogram Userbot (Self ID) client sessions."""

    def __init__(self):
        self.clients: Dict[int, Client] = {}  # telegram user_id -> Client
        self.default_client: Optional[Client] = None

    async def start_default_client(self) -> Optional[Client]:
        """Start the global default string session if provided in config."""
        if not config.DEFAULT_STRING_SESSION:
            return None
        try:
            client = Client(
                name="default_selfbot",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=config.DEFAULT_STRING_SESSION,
                in_memory=True
            )
            await client.start()
            me = await client.get_me()
            logger.info(f"Default Selfbot started successfully: {me.first_name} (@{me.username or me.id})")
            self._register_self_handlers(client)
            self.default_client = client
            return client
        except Exception as e:
            logger.error(f"Failed to start DEFAULT_STRING_SESSION: {e}")
            return None

    async def start_user_client(self, user_id: int, session_string: str) -> Client:
        """Start a user's Self ID client instance."""
        # Stop existing client if any
        if user_id in self.clients:
            await self.stop_user_client(user_id)

        client = Client(
            name=f"self_{user_id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True
        )
        await client.start()
        me = await client.get_me()
        logger.info(f"Selfbot started for user {user_id}: {me.first_name} (ID: {me.id})")
        self._register_self_handlers(client)
        self.clients[user_id] = client
        return client

    async def stop_user_client(self, user_id: int):
        """Stop and remove a user's Self ID client."""
        client = self.clients.pop(user_id, None)
        if client and client.is_connected:
            try:
                await client.stop()
                logger.info(f"Stopped Selfbot client for user {user_id}")
            except Exception as e:
                logger.warning(f"Error stopping client for {user_id}: {e}")

    async def get_client_for_user(self, user_id: int) -> Optional[Client]:
        """Get running client for user, or attempt to load from database."""
        if user_id in self.clients and self.clients[user_id].is_connected:
            return self.clients[user_id]

        user_data = await get_user(user_id)
        if user_data and user_data.get("string_session"):
            try:
                return await self.start_user_client(user_id, user_data["string_session"])
            except Exception as e:
                logger.error(f"Failed to revive client for user {user_id}: {e}")
                return None

        # Fallback to default client if available
        if self.default_client and self.default_client.is_connected:
            return self.default_client

        return None

    async def load_all_sessions(self):
        """Load and start all saved user clients from database on startup."""
        await self.start_default_client()
        saved_users = await get_all_users_with_sessions()
        logger.info(f"Loading {len(saved_users)} saved Self ID session(s)...")
        for u in saved_users:
            u_id = u["user_id"]
            s_str = u["string_session"]
            try:
                await self.start_user_client(u_id, s_str)
            except Exception as e:
                logger.warning(f"Failed to auto-start session for user {u_id}: {e}")

    async def stop_all(self):
        """Cleanly disconnect all running clients."""
        for u_id in list(self.clients.keys()):
            await self.stop_user_client(u_id)
        if self.default_client and self.default_client.is_connected:
            try:
                await self.default_client.stop()
            except Exception:
                pass

    def _register_self_handlers(self, client: Client):
        """Register prefix commands for direct execution by the self account."""
        from core.tagger import tagger_engine

        @client.on_message(filters.me & filters.command(["tag", "utag"], prefixes=[".", "!", "/"]))
        async def _self_tag_handler(c: Client, m: Message):
            custom_text = m.text.split(None, 1)[1] if len(m.text.split()) > 1 else "Hey everyone! 👋"
            reply_id = m.reply_to_message_id if m.reply_to_message else None
            await tagger_engine.start_tagging(
                client=c,
                chat_id=m.chat.id,
                initiated_by=m.from_user.id,
                mode="text",
                custom_text=custom_text,
                reply_to_message_id=reply_id
            )

        @client.on_message(filters.me & filters.command(["etag"], prefixes=[".", "!", "/"]))
        async def _self_etag_handler(c: Client, m: Message):
            custom_text = m.text.split(None, 1)[1] if len(m.text.split()) > 1 else ""
            reply_id = m.reply_to_message_id if m.reply_to_message else None
            await tagger_engine.start_tagging(
                client=c,
                chat_id=m.chat.id,
                initiated_by=m.from_user.id,
                mode="emoji",
                custom_text=custom_text,
                reply_to_message_id=reply_id
            )

        @client.on_message(filters.me & filters.command(["admintag"], prefixes=[".", "!", "/"]))
        async def _self_admintag_handler(c: Client, m: Message):
            custom_text = m.text.split(None, 1)[1] if len(m.text.split()) > 1 else "Attention Admins! 🚨"
            reply_id = m.reply_to_message_id if m.reply_to_message else None
            await tagger_engine.start_tagging(
                client=c,
                chat_id=m.chat.id,
                initiated_by=m.from_user.id,
                mode="admin",
                custom_text=custom_text,
                reply_to_message_id=reply_id
            )

        @client.on_message(filters.me & filters.command(["stop", "cancel"], prefixes=[".", "!", "/"]))
        async def _self_stop_handler(c: Client, m: Message):
            stopped = await tagger_engine.stop_tagging(m.chat.id)
            if stopped:
                await m.reply_text("🛑 **Tagging stopped successfully!**")
            else:
                await m.reply_text("ℹ️ No active tagging process found in this group.")

client_manager = ClientManager()
