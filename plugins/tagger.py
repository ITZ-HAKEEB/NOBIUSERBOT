import logging
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from core.client_manager import client_manager
from core.tagger import tagger_engine

logger = logging.getLogger(__name__)

async def resolve_self_client(bot: Client, message: Message):
    """Ensure the sender has a linked selfbot and it's present in the chat."""
    user_id = message.from_user.id
    self_client = await client_manager.get_client_for_user(user_id)

    if not self_client or not self_client.is_connected:
        bot_user = bot.me
        await message.reply_text(
            "⚠️ **`[ No Self ID Connected! ]`**\n\n"
            "**`This bot uses your personal Telegram account to tag group members without limits.`**\n\n"
            f"👉 [**`Click here to connect in PM`**](https://t.me/{bot_user.username}?start=connect) **`or send /gen_session!`**",
            disable_web_page_preview=True
        )
        return None

    # Check if selfbot is in the current chat
    try:
        await self_client.get_chat_member(message.chat.id, "me")
    except errors.UserNotParticipant:
        me = self_client.me
        name = me.first_name if me else "Your account"
        await message.reply_text(
            f"⚠️ **`[ Self ID Missing from Group! ]`**\n\n"
            f"**`Your linked account`** `{name}` **`must join this group before tagging members.`**"
        )
        return None
    except Exception as e:
        logger.warning(f"Could not verify selfbot membership in {message.chat.id}: {e}")

    return self_client


@Client.on_message(filters.command(["tag", "utag"]) & filters.group)
async def tag_group_handler(bot: Client, message: Message):
    """Tag all members in batches with custom text."""
    self_client = await resolve_self_client(bot, message)
    if not self_client:
        return

    html_text = message.text.html if hasattr(message.text, "html") and message.text.html else message.text
    custom_text = html_text.split(None, 1)[1] if len(message.text.split()) > 1 else "Hey everyone! 👋"
    reply_id = message.reply_to_message_id if message.reply_to_message else None

    started = await tagger_engine.start_tagging(
        client=self_client,
        chat_id=message.chat.id,
        initiated_by=message.from_user.id,
        mode="text",
        custom_text=custom_text,
        reply_to_message_id=reply_id
    )

    if not started:
        await message.reply_text("⚠️ **`A tagging session is already active in this group! Use /stop to cancel.`**")


@Client.on_message(filters.command("etag") & filters.group)
async def etag_group_handler(bot: Client, message: Message):
    """Tag all members decorated with random emojis."""
    self_client = await resolve_self_client(bot, message)
    if not self_client:
        return

    html_text = message.text.html if hasattr(message.text, "html") and message.text.html else message.text
    custom_text = html_text.split(None, 1)[1] if len(message.text.split()) > 1 else ""
    reply_id = message.reply_to_message_id if message.reply_to_message else None

    started = await tagger_engine.start_tagging(
        client=self_client,
        chat_id=message.chat.id,
        initiated_by=message.from_user.id,
        mode="emoji",
        custom_text=custom_text,
        reply_to_message_id=reply_id
    )

    if not started:
        await message.reply_text("⚠️ **`A tagging session is already active in this group! Use /stop to cancel.`**")


@Client.on_message(filters.command("admintag") & filters.group)
async def admintag_group_handler(bot: Client, message: Message):
    """Tag group administrators only."""
    self_client = await resolve_self_client(bot, message)
    if not self_client:
        return

    html_text = message.text.html if hasattr(message.text, "html") and message.text.html else message.text
    custom_text = html_text.split(None, 1)[1] if len(message.text.split()) > 1 else "Admins attention needed! 🚨"
    reply_id = message.reply_to_message_id if message.reply_to_message else None

    started = await tagger_engine.start_tagging(
        client=self_client,
        chat_id=message.chat.id,
        initiated_by=message.from_user.id,
        mode="admin",
        custom_text=custom_text,
        reply_to_message_id=reply_id
    )

    if not started:
        await message.reply_text("⚠️ **`A tagging session is already active in this group! Use /stop to cancel.`**")


@Client.on_message(filters.command(["ftag", "favtag"]) & filters.group)
async def ftag_group_handler(bot: Client, message: Message):
    """Fast tag saved favorite users only."""
    self_client = await resolve_self_client(bot, message)
    if not self_client:
        return

    html_text = message.text.html if hasattr(message.text, "html") and message.text.html else message.text
    custom_text = html_text.split(None, 1)[1] if len(message.text.split()) > 1 else "Wake up bestie! ⭐"
    reply_id = message.reply_to_message_id if message.reply_to_message else None

    started = await tagger_engine.start_tagging(
        client=self_client,
        chat_id=message.chat.id,
        initiated_by=message.from_user.id,
        mode="fav",
        custom_text=custom_text,
        reply_to_message_id=reply_id
    )

    if not started:
        await message.reply_text("⚠️ **`A tagging session is already active in this group! Use /stop to cancel.`**")


@Client.on_message(filters.command(["stop", "cancel"]) & filters.group)

async def stop_group_handler(bot: Client, message: Message):
    """Stop active tagging in the group."""
    stopped = await tagger_engine.stop_tagging(message.chat.id)
    if stopped:
        await message.reply_text("🛑 **`Tagging has been cancelled successfully.`**")
    else:
        await message.reply_text("ℹ️ **`No active tagging session running in this group.`**")
