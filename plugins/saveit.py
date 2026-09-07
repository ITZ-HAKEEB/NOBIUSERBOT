import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from core.client_manager import client_manager
from core.saveit import has_media, save_and_forward_media
from database.db import get_saveit_setting, set_saveit_setting

logger = logging.getLogger(__name__)

@Client.on_message(filters.command(["autosave", "savetimed"]))
async def autosave_toggle_handler(bot: Client, message: Message):
    """Toggle auto-saving disappearing/timed media on or off."""
    user_id = message.from_user.id
    current_state = await get_saveit_setting(user_id)

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg in ["on", "enable", "true", "yes", "1"]:
            new_state = True
        elif arg in ["off", "disable", "false", "no", "0"]:
            new_state = False
        else:
            return await message.reply_text(
                "⚠️ **`[ Usage: /autosave ]`**\n\n"
                "• **`/autosave on`** `— Enable auto-saving timed media`\n"
                "• **`/autosave off`** `— Disable auto-saving timed media`"
            )
    else:
        # Toggle current state
        new_state = not current_state

    await set_saveit_setting(user_id, new_state)
    state_str = "🟢 **`ENABLED`**" if new_state else "🔴 **`DISABLED`**"

    await message.reply_text(
        f"💾 **`[ SaveIt Auto-Saver Settings ]`**\n\n"
        f"• **`Auto-Save Disappearing Media:`** {state_str}\n\n"
        "💡 **`When enabled, any incoming timed photos or videos in private chats will be auto-saved uncompressed to your Saved Messages.`**"
    )


@Client.on_message(filters.command(["save", "saveit"]))
async def bot_saveit_handler(bot: Client, message: Message):
    """Manual saver triggered via bot."""
    user_id = message.from_user.id
    self_client = await client_manager.get_client_for_user(user_id)

    if not self_client or not self_client.is_connected:
        return await message.reply_text(
            "⚠️ **`[ No Self ID Connected! ]`**\n\n"
            "**`To save media and bypass forward/download restrictions, please connect your account via /login or /gen_session in PM!`**"
        )

    if not message.reply_to_message:
        return await message.reply_text(
            "⚠️ **`[ SaveIt Usage ]`**\n\n"
            "**`Reply to any photo, video, document, voice note or restricted media with /saveit (or .saveit) to save it directly to your Saved Messages!`**"
        )

    target_msg = message.reply_to_message
    if not has_media(target_msg):
        return await message.reply_text("❌ **`No media found in the replied message!`**")

    status_msg = await message.reply_text("⏳ **`Downloading and saving media to your Saved Messages...`**")
    success = await save_and_forward_media(client=self_client, message=target_msg, is_auto=False)

    if success:
        await status_msg.edit_text("✅ **`Media successfully saved to your Saved Messages!`**")
    else:
        await status_msg.edit_text("❌ **`Failed to download or save media.`**")
