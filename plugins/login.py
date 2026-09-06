import logging
from typing import Dict
from pyrogram import Client, filters, errors
from pyrogram.types import Message
import config
from database.db import (
    set_user_session,
    get_user,
    remove_user_session,
    save_login_state,
    get_login_state,
    clear_login_state
)
from core.client_manager import client_manager

logger = logging.getLogger(__name__)

# In-memory store for active phone login temp clients: user_id -> Client
temp_login_clients: Dict[int, Client] = {}

@Client.on_message(filters.command("login") & filters.private)
async def login_session_handler(bot: Client, message: Message):
    """Directly link a Pyrogram v2 string session."""
    user_id = message.from_user.id
    parts = message.text.split(None, 1)

    if len(parts) < 2:
        return await message.reply_text(
            "⚠️ **`[ Usage ]`**\n"
            "• **`/login <your_pyrogram_string_session>`**\n\n"
            "💡 **`Or use /gen_session to generate an OTP session directly in chat.`**"
        )

    session_string = parts[1].strip()
    status_msg = await message.reply_text("🔄 **`Verifying your session string...`**")

    try:
        test_client = Client(
            name=f"test_{user_id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True
        )
        await test_client.start()
        me = await test_client.get_me()
        await test_client.stop()

        # Save to database
        await set_user_session(
            user_id=user_id,
            string_session=session_string,
            self_user_id=me.id,
            self_first_name=me.first_name,
            self_username=me.username
        )

        # Start dynamic client
        await client_manager.start_user_client(user_id, session_string)

        await status_msg.edit_text(
            "✅ **`[ Self ID Connected Successfully! ]`**\n\n"
            f"👤 **`Name:`** `{me.first_name}`\n"
            f"🆔 **`ID:`** `{me.id}`\n"
            f"🔗 **`Username:`** `@{me.username or 'None'}`\n\n"
            "**`Your account is ready! Add it to groups and use /tag or .tag.`**"
        )
    except errors.AuthKeyInvalid:
        await status_msg.edit_text("❌ **`Failed: Session string is invalid or expired.`**")
    except Exception as e:
        logger.error(f"Login error for user {user_id}: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ **`Error linking session:`** `{e}`")


async def start_interactive_login(bot: Client, user_id: int, reply_func):
    """Reusable starter for in-bot phone login / session generation."""
    await clear_login_state(user_id)
    if user_id in temp_login_clients:
        try:
            await temp_login_clients[user_id].disconnect()
        except Exception:
            pass
        temp_login_clients.pop(user_id, None)

    await save_login_state(user_id, phone_number="", phone_code_hash="", step="WAITING_PHONE")

    await reply_func(
        "📱 **`[ Pyrogram Session Generator & Login ]`**\n\n"
        "**`Please send your Phone Number with country code:`**\n"
        "**`Example: +919876543210 or +1234567890`**\n\n"
        "*(**`Send /cancel_login anytime to abort`**)*"
    )


@Client.on_message(filters.command(["login_phone", "generate", "gen_session"]) & filters.private)
async def login_phone_start(bot: Client, message: Message):
    """Start interactive phone login wizard."""
    await start_interactive_login(bot, message.from_user.id, message.reply_text)


@Client.on_message(filters.command("cancel_login") & filters.private)
async def cancel_login_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    await clear_login_state(user_id)
    if user_id in temp_login_clients:
        try:
            await temp_login_clients[user_id].disconnect()
        except Exception:
            pass
        temp_login_clients.pop(user_id, None)
    await message.reply_text("🛑 **`Login process cancelled.`**")


@Client.on_message(filters.command("myaccount") & filters.private)
async def myaccount_handler(bot: Client, message: Message):
    """View connected self ID details."""
    user_id = message.from_user.id
    user_info = await get_user(user_id)

    if not user_info or not user_info.get("string_session"):
        return await message.reply_text(
            "⚠️ **`[ No Self ID Linked! ]`**\n\n"
            "**`Use /gen_session or /login <string_session> to connect.`**"
        )

    is_running = user_id in client_manager.clients and client_manager.clients[user_id].is_connected
    status_emoji = "🟢 Running" if is_running else "🟡 Disconnected (will auto-reconnect)"

    await message.reply_text(
        "👤 **`[ Connected Self ID Account ]`**\n\n"
        f"• **`Name:`** `{user_info.get('self_first_name')}`\n"
        f"• **`User ID:`** `{user_info.get('self_user_id')}`\n"
        f"• **`Username:`** `@{user_info.get('self_username') or 'None'}`\n"
        f"• **`Status:`** `{status_emoji}`\n\n"
        "**`Send /logout if you wish to disconnect this account.`**"
    )


@Client.on_message(filters.command("logout") & filters.private)
async def logout_handler(bot: Client, message: Message):
    """Disconnect and wipe session."""
    user_id = message.from_user.id
    await client_manager.stop_user_client(user_id)
    await remove_user_session(user_id)
    await message.reply_text("🚪 **`Logged out successfully! Your Self ID session has been deleted.`**")


# Listener for interactive phone login steps
@Client.on_message(filters.private & ~filters.command(["login", "login_phone", "generate", "gen_session", "cancel_login", "start", "help", "myaccount", "logout"]))
async def interactive_login_steps(bot: Client, message: Message):
    user_id = message.from_user.id
    state = await get_login_state(user_id)
    if not state or not state.get("step"):
        return

    step = state["step"]
    text = (message.text or "").strip()

    if step == "WAITING_PHONE":
        phone_number = text.replace(" ", "").replace("-", "")
        if not (phone_number.startswith("+") and phone_number[1:].isdigit() and len(phone_number) >= 8):
            return await message.reply_text(
                "❌ **`Invalid Phone Number format.`**\n"
                "**`Please ensure it starts with + followed by country code (e.g. +919876543210):`**"
            )

        status_msg = await message.reply_text("⏳ **`Requesting Telegram verification code...`**")
        try:
            temp_client = Client(
                name=f"temp_{user_id}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                in_memory=True
            )
            await temp_client.connect()
            code_result = await temp_client.send_code(phone_number)
            temp_login_clients[user_id] = temp_client

            await save_login_state(
                user_id=user_id,
                phone_number=phone_number,
                phone_code_hash=code_result.phone_code_hash,
                step="WAITING_OTP"
            )

            await status_msg.edit_text(
                "📩 **`[ Telegram Code Dispatched! ]`**\n\n"
                "**`Please check your Telegram app for the login code.`**\n\n"
                "⚠️ **`IMPORTANT: Send the code with spaces between digits!`**\n"
                "**`Example: If code is 54321, send: 5 4 3 2 1`**"
            )
        except errors.PhoneNumberInvalid:
            await status_msg.edit_text("❌ **`The phone number entered is invalid. Please try /gen_session again.`**")
            await clear_login_state(user_id)
        except Exception as e:
            logger.error(f"Error requesting code for {user_id}: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ **`Error requesting login code:`** `{e}`")
            await clear_login_state(user_id)

    elif step == "WAITING_OTP":
        otp_code = text.replace(" ", "").replace("-", "")
        if not otp_code.isdigit():
            return await message.reply_text("❌ **`Code must contain only digits. Example: 1 2 3 4 5`**")

        temp_client = temp_login_clients.get(user_id)
        if not temp_client:
            await clear_login_state(user_id)
            return await message.reply_text("⚠️ **`Session expired. Please restart with /gen_session.`**")

        status_msg = await message.reply_text("⏳ **`Verifying authentication code...`**")
        try:
            await temp_client.sign_in(
                phone_number=state["phone_number"],
                phone_code_hash=state["phone_code_hash"],
                phone_code=otp_code
            )

            # Successfully logged in without 2FA
            session_str = await temp_client.export_session_string()
            me = await temp_client.get_me()
            await temp_client.disconnect()
            temp_login_clients.pop(user_id, None)

            await set_user_session(
                user_id=user_id,
                string_session=session_str,
                self_user_id=me.id,
                self_first_name=me.first_name,
                self_username=me.username
            )
            await clear_login_state(user_id)
            await client_manager.start_user_client(user_id, session_str)

            await status_msg.edit_text(
                "🎉 **`[ Session Generated & Connected Successfully! ]`**\n\n"
                f"👤 **`Account:`** `{me.first_name}`\n"
                f"🆔 **`ID:`** `{me.id}`\n"
                f"🔗 **`Username:`** `@{me.username or 'None'}`\n\n"
                "📋 **`Your Pyrogram String Session (tap to copy):`**\n"
                f"```{session_str}```\n\n"
                "✅ **`Linked as your Self ID! Ready for /tag or .tag in groups.`**"
            )
        except errors.SessionPasswordNeeded:
            await save_login_state(
                user_id=user_id,
                phone_number=state["phone_number"],
                phone_code_hash=state["phone_code_hash"],
                step="WAITING_2FA"
            )
            await status_msg.edit_text(
                "🔐 **`[ 2-Step Verification (2FA) Detected ]`**\n\n"
                "**`Please send your Telegram cloud password to complete login:`**"
            )
        except (errors.PhoneCodeInvalid, errors.PhoneCodeExpired):
            await status_msg.edit_text("❌ **`Invalid or expired code. Please re-enter or /cancel_login:`**")
        except Exception as e:
            logger.error(f"Error checking OTP for {user_id}: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ **`Login error:`** `{e}`")
            await clear_login_state(user_id)

    elif step == "WAITING_2FA":
        password = text
        temp_client = temp_login_clients.get(user_id)
        if not temp_client:
            await clear_login_state(user_id)
            return await message.reply_text("⚠️ **`Session expired. Please restart with /gen_session.`**")

        status_msg = await message.reply_text("⏳ **`Verifying 2FA password...`**")
        try:
            await temp_client.check_password(password)
            session_str = await temp_client.export_session_string()
            me = await temp_client.get_me()
            await temp_client.disconnect()
            temp_login_clients.pop(user_id, None)

            await set_user_session(
                user_id=user_id,
                string_session=session_str,
                self_user_id=me.id,
                self_first_name=me.first_name,
                self_username=me.username
            )
            await clear_login_state(user_id)
            await client_manager.start_user_client(user_id, session_str)

            await status_msg.edit_text(
                "🎉 **`[ Session Generated & Connected Successfully! ]`**\n\n"
                f"👤 **`Account:`** `{me.first_name}`\n"
                f"🆔 **`ID:`** `{me.id}`\n"
                f"🔗 **`Username:`** `@{me.username or 'None'}`\n\n"
                "📋 **`Your Pyrogram String Session (tap to copy):`**\n"
                f"```{session_str}```\n\n"
                "✅ **`Linked as your Self ID! Ready for /tag or .tag in groups.`**"
            )

        except errors.PasswordHashInvalid:
            await status_msg.edit_text("❌ **`Incorrect 2FA password. Please try again (or /cancel_login):`**")
        except Exception as e:
            logger.error(f"2FA error for {user_id}: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ **`2FA verification error:`** `{e}`")
            await clear_login_state(user_id)
