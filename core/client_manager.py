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
            if m.chat.id > 0:
                return await m.reply_text("⚠️ **`Tagging can only be used in groups!`**")
            html_text = m.text.html if hasattr(m.text, "html") and m.text.html else m.text
            custom_text = html_text.split(None, 1)[1] if len(m.text.split()) > 1 else "Hey everyone! 👋"
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
            if m.chat.id > 0:
                return await m.reply_text("⚠️ **`Tagging can only be used in groups!`**")
            html_text = m.text.html if hasattr(m.text, "html") and m.text.html else m.text
            custom_text = html_text.split(None, 1)[1] if len(m.text.split()) > 1 else ""
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
            if m.chat.id > 0:
                return await m.reply_text("⚠️ **`Tagging can only be used in groups!`**")
            html_text = m.text.html if hasattr(m.text, "html") and m.text.html else m.text
            custom_text = html_text.split(None, 1)[1] if len(m.text.split()) > 1 else "Attention Admins! 🚨"
            reply_id = m.reply_to_message_id if m.reply_to_message else None
            await tagger_engine.start_tagging(
                client=c,
                chat_id=m.chat.id,
                initiated_by=m.from_user.id,
                mode="admin",
                custom_text=custom_text,
                reply_to_message_id=reply_id
            )

        @client.on_message(filters.me & filters.command(["ftag", "favtag"], prefixes=[".", "!", "/"]))
        async def _self_ftag_handler(c: Client, m: Message):
            if m.chat.id > 0:
                return await m.reply_text("⚠️ **`Tagging can only be used in groups!`**")
            html_text = m.text.html if hasattr(m.text, "html") and m.text.html else m.text
            custom_text = html_text.split(None, 1)[1] if len(m.text.split()) > 1 else "Hey bestie! ⭐"
            reply_id = m.reply_to_message_id if m.reply_to_message else None
            await tagger_engine.start_tagging(
                client=c,
                chat_id=m.chat.id,
                initiated_by=m.from_user.id,
                mode="fav",
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

        # --- SaveIt Media Handlers (Timed Media Auto-Saver & .saveit) ---
        from core.saveit import is_timed_media, has_media, save_and_forward_media
        from database.db import get_saveit_setting

        @client.on_message(filters.private & ~filters.me, group=1)
        async def _auto_save_timed_handler(c: Client, m: Message):
            """Automatically intercepts disappearing/view-once photos and videos."""
            try:
                if is_timed_media(m):
                    user_id = c.me.id if c.me else None
                    if user_id and await get_saveit_setting(user_id):
                        logger.info(f"Auto-capturing timed media for user {user_id} from {m.chat.id}")
                        await save_and_forward_media(client=c, message=m, is_auto=True)
            finally:
                m.continue_propagation()

        @client.on_message(filters.me & filters.command(["save", "saveit"], prefixes=[".", "!", "/"]))
        async def _self_saveit_handler(c: Client, m: Message):
            """Manual saver: reply to any media with .saveit to save to Saved Messages."""
            if not m.reply_to_message:
                return await m.reply_text("⚠️ **`Reply to any photo, video or media with .saveit to save it to your Saved Messages!`**")

            target_msg = m.reply_to_message
            if not has_media(target_msg):
                return await m.reply_text("❌ **`No media found in replied message!`**")

            status = await m.reply_text("⏳ **`Saving media to Saved Messages...`**")
            success = await save_and_forward_media(client=c, message=target_msg, is_auto=False)
            if success:
                await status.edit_text("✅ **`Media successfully saved to your Saved Messages!`**")
            else:
                await status.edit_text("❌ **`Failed to download or save media.`**")

        # --- Auto DM Responder Handlers ---
        from core.automsg import handle_incoming_private_message
        from database.db import (
            get_auto_message_settings,
            set_auto_message_text,
            set_auto_message_enabled,
            reset_auto_message_text,
            clear_auto_message_history
        )

        @client.on_message(filters.private & ~filters.me, group=2)
        async def _auto_dm_listener(c: Client, m: Message):
            """Automatically greets first-time DM senders."""
            await handle_incoming_private_message(c, m)


        @client.on_message(filters.me & filters.command(["setautomsg", "setwelcome"], prefixes=[".", "!", "/"]))
        async def _self_set_automsg_handler(c: Client, m: Message):
            """Direct self command to set auto-responder message with HTML/custom emoji support."""
            html_text = m.text.html if hasattr(m.text, "html") and m.text.html else m.text
            new_text = ""
            if len(m.text.split(None, 1)) > 1:
                new_text = html_text.split(None, 1)[1].strip()
            elif m.reply_to_message:
                target = m.reply_to_message
                if target.text:
                    new_text = target.text.html if hasattr(target.text, "html") and target.text.html else target.text
                elif target.caption:
                    new_text = target.caption.html if hasattr(target.caption, "html") and target.caption.html else target.caption
                new_text = (new_text or "").strip()

            if not new_text:
                return await m.reply_text(
                    "⚠️ **`[ Usage: .setautomsg <text> ]`**\n\n"
                    "• **`Example:`** `.setautomsg Hey {name}! Thanks for messaging me. I will reply soon!`\n"
                    "• **`Or reply to any message (with text, bold, or custom emojis) with .setautomsg`**\n\n"
                    "📌 **`Supported Placeholders:`**\n"
                    "• `{name}` — First name\n"
                    "• `{username}` — @username\n"
                    "• `{mention}` — Clickable mention\n"
                    "• `{id}` — User ID\n"
                    "• `{my_name}` — Your name\n"
                    "✨ **`Telegram Premium custom emojis are fully supported!`**"
                )

            user_id = c.me.id
            await set_auto_message_text(user_id, new_text)
            try:
                await m.reply_text(
                    "✅ <b>[ Auto DM Message Updated! ]</b>\n\n"
                    f"📝 <b>New Message:</b>\n{new_text}\n\n"
                    "⚡ <i>This message will now be sent to anyone who DMs your assistant for the first time.</i>",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                await m.reply_text(
                    "✅ **`[ Auto DM Message Updated! ]`**\n\n"
                    f"📝 **`New Message:`**\n{m.text.split(None, 1)[1] if len(m.text.split()) > 1 else new_text}\n\n"
                    "⚡ **`This message will now be sent to anyone who DMs your assistant for the first time.`**"
                )

        @client.on_message(filters.me & filters.command(["automsg", "getautomsg"], prefixes=[".", "!", "/"]))
        async def _self_automsg_info_handler(c: Client, m: Message):
            """View status or toggle/reset auto-responder."""
            user_id = c.me.id
            parts = m.text.split()
            if len(parts) > 1:
                subcmd = parts[1].lower()
                if subcmd in ["on", "enable", "1"]:
                    await set_auto_message_enabled(user_id, True)
                    return await m.reply_text("🟢 **`Auto DM Responder is now ENABLED!`**")
                elif subcmd in ["off", "disable", "0"]:
                    await set_auto_message_enabled(user_id, False)
                    return await m.reply_text("🔴 **`Auto DM Responder is now DISABLED!`**")
                elif subcmd in ["reset"]:
                    await reset_auto_message_text(user_id)
                    return await m.reply_text("🔄 **`Auto DM message reset to default template!`**")
                elif subcmd in ["clear", "clearhistory", "cleargreeted"]:
                    count = await clear_auto_message_history(user_id)
                    return await m.reply_text(f"🧹 **`Cleared {count} greeted contacts from history! They will be greeted again on their next message.`**")

            settings = await get_auto_message_settings(user_id)
            state_str = "🟢 <b>ENABLED</b>" if settings["is_enabled"] else "🔴 <b>DISABLED</b>"
            type_str = "Custom" if settings.get("is_custom") else "Default"

            msg_preview = settings["message"]
            try:
                await m.reply_text(
                    "🤖 <b>[ Assistant Auto DM Settings ]</b>\n\n"
                    f"• <b>Status:</b> {state_str}\n"
                    f"• <b>Template Type:</b> <code>{type_str}</code>\n\n"
                    f"📝 <b>Current Message:</b>\n{msg_preview}\n\n"
                    "⚙️ <b>Controls:</b>\n"
                    "• <code>.automsg on|off</code> — Enable / Disable\n"
                    "• <code>.setautomsg &lt;text&gt;</code> — Change message\n"
                    "• <code>.resetautomsg</code> — Reset to default\n"
                    "• <code>.cleargreeted</code> — Reset greeted contacts",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                await m.reply_text(
                    "🤖 **`[ Assistant Auto DM Settings ]`**\n\n"
                    f"• **`Status:`** {'🟢 ENABLED' if settings['is_enabled'] else '🔴 DISABLED'}\n"
                    f"• **`Template Type:`** `{type_str}`\n\n"
                    f"📝 **`Current Message:`**\n{msg_preview}\n\n"
                    "⚙️ **`Controls:`**\n"
                    "• `.automsg on|off` — Enable / Disable\n"
                    "• `.setautomsg <text>` — Change message\n"
                    "• `.resetautomsg` — Reset to default\n"
                    "• `.cleargreeted` — Reset greeted contacts"
                )

        @client.on_message(filters.me & filters.command(["resetautomsg"], prefixes=[".", "!", "/"]))
        async def _self_reset_automsg_handler(c: Client, m: Message):
            user_id = c.me.id
            await reset_auto_message_text(user_id)
            await m.reply_text("🔄 **`Auto DM message has been reset to the default template!`**")

        @client.on_message(filters.me & filters.command(["cleargreeted"], prefixes=[".", "!", "/"]))
        async def _self_clear_greeted_handler(c: Client, m: Message):
            user_id = c.me.id
            count = await clear_auto_message_history(user_id)
            await m.reply_text(f"🧹 **`Cleared {count} contacts from greeted history!`**")


client_manager = ClientManager()

