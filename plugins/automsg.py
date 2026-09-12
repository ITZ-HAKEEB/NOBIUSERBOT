import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from core.client_manager import client_manager
from database.db import (
    get_user,
    get_auto_message_settings,
    set_auto_message_text,
    set_auto_message_enabled,
    reset_auto_message_text,
    clear_auto_message_history,
    DEFAULT_AUTO_MESSAGE
)
from utils.fonts import to_mono

logger = logging.getLogger(__name__)


async def get_effective_assistant_id(user_id: int) -> int:
    """Resolve the assistant/self Telegram ID for the given bot user."""
    client = await client_manager.get_client_for_user(user_id)
    if client and client.me:
        return client.me.id
    user_info = await get_user(user_id)
    if user_info and user_info.get("self_user_id"):
        return user_info["self_user_id"]
    return user_id


@Client.on_message(filters.command(["setautomsg", "setwelcome"]))
async def bot_set_automsg_handler(bot: Client, message: Message):
    """Set custom auto-responder message via Bot."""
    user_id = message.from_user.id
    assistant_id = await get_effective_assistant_id(user_id)

    new_text = ""
    if len(message.command) > 1:
        new_text = message.text.split(None, 1)[1].strip()
    elif message.reply_to_message and message.reply_to_message.text:
        new_text = message.reply_to_message.text.strip()

    if not new_text:
        return await message.reply_text(
            "⚠️ **`[ Usage: /setautomsg <text> ]`**\n\n"
            "**`Set the greeting message automatically sent when someone DMs your assistant for the first time.`**\n\n"
            "💡 **`Example:`**\n"
            "`/setautomsg Hey {name}! 👋 Thank you for messaging me. I will reply soon!`\n\n"
            "📌 **`Supported Dynamic Placeholders:`**\n"
            "• `{name}` — First name of sender\n"
            "• `{username}` — @username of sender\n"
            "• `{mention}` — Clickable mention\n"
            "• `{id}` — Sender's Telegram ID\n"
            "• `{my_name}` — Your assistant account name"
        )

    await set_auto_message_text(assistant_id, new_text)
    if assistant_id != user_id:
        await set_auto_message_text(user_id, new_text)

    await message.reply_text(
        "✅ **`[ Auto DM Message Updated! ]`**\n\n"
        f"📝 **`New Greeting Message:`**\n{new_text}\n\n"
        "⚡ **`This message will now be automatically sent when someone contacts your assistant in private chat for the first time.`**"
    )


@Client.on_message(filters.command(["automsg", "getautomsg"]))
async def bot_automsg_info_handler(bot: Client, message: Message):
    """View status or toggle/reset auto-responder via Bot."""
    user_id = message.from_user.id
    assistant_id = await get_effective_assistant_id(user_id)

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg in ["on", "enable", "true", "yes", "1"]:
            await set_auto_message_enabled(assistant_id, True)
            if assistant_id != user_id:
                await set_auto_message_enabled(user_id, True)
            return await message.reply_text("🟢 **`Auto DM Responder is now ENABLED!`**")
        elif arg in ["off", "disable", "false", "no", "0"]:
            await set_auto_message_enabled(assistant_id, False)
            if assistant_id != user_id:
                await set_auto_message_enabled(user_id, False)
            return await message.reply_text("🔴 **`Auto DM Responder is now DISABLED!`**")
        elif arg in ["reset"]:
            await reset_auto_message_text(assistant_id)
            if assistant_id != user_id:
                await reset_auto_message_text(user_id)
            return await message.reply_text("🔄 **`Auto DM message reset to default template!`**")
        elif arg in ["clear", "clearhistory", "cleargreeted"]:
            count = await clear_auto_message_history(assistant_id)
            return await message.reply_text(f"🧹 **`Cleared {count} contacts from greeted history!`**")

    settings = await get_auto_message_settings(assistant_id)
    state_str = "🟢 **`ENABLED`**" if settings["is_enabled"] else "🔴 **`DISABLED`**"
    type_str = "Custom Message" if settings.get("is_custom") else "Default Template"
    msg_preview = settings["message"]

    toggle_btn_text = f"🔴 {to_mono('Disable Auto DM')}" if settings["is_enabled"] else f"🟢 {to_mono('Enable Auto DM')}"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_btn_text, callback_data="btn_toggle_automsg")],
        [InlineKeyboardButton(f"🔄 {to_mono('Reset to Default')}", callback_data="btn_reset_automsg")],
        [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
    ])

    await message.reply_text(
        "🤖 **`[ Assistant Auto DM Responder ]`**\n\n"
        f"• **`Status:`** {state_str}\n"
        f"• **`Message Type:`** `{type_str}`\n\n"
        f"📝 **`Current Auto Message:`**\n{msg_preview}\n\n"
        "💡 **`Commands:`**\n"
        "• `/setautomsg <text>` — Customize message\n"
        "• `/automsg on` / `/automsg off` — Toggle\n"
        "• `/resetautomsg` — Revert to default\n"
        "• `/cleargreeted` — Clear greeted list",
        reply_markup=markup
    )


@Client.on_message(filters.command(["resetautomsg"]))
async def bot_reset_automsg_handler(bot: Client, message: Message):
    """Reset auto-responder message to default."""
    user_id = message.from_user.id
    assistant_id = await get_effective_assistant_id(user_id)
    await reset_auto_message_text(assistant_id)
    if assistant_id != user_id:
        await reset_auto_message_text(user_id)
    await message.reply_text("🔄 **`Auto DM message has been reset to the default template!`**")


@Client.on_message(filters.command(["cleargreeted"]))
async def bot_clear_greeted_handler(bot: Client, message: Message):
    """Clear list of greeted contacts so they will receive the auto-message again."""
    user_id = message.from_user.id
    assistant_id = await get_effective_assistant_id(user_id)
    count = await clear_auto_message_history(assistant_id)
    await message.reply_text(
        f"🧹 **`[ Greeted History Cleared ]`**\n\n"
        f"• **`Cleared Contacts:`** `{count}`\n"
        "⚡ **`Next time any of these contacts message your assistant in PM, they will receive the auto-greeting again.`**"
    )
