import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Set, Tuple
from pyrogram import Client
from pyrogram.types import Message

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Lock and cache for processed messages to prevent duplicate downloads
_save_lock = asyncio.Lock()
_saved_message_keys: Set[Tuple[int, int]] = set()

def is_timed_media(message: Message) -> bool:
    """Detect if a message contains disappearing/self-destructing media."""
    if not message:
        return False
    if getattr(message, "ttl_seconds", None):
        return True
    for attr in ("photo", "video", "voice", "video_note", "document", "audio", "animation"):
        obj = getattr(message, attr, None)
        if obj and getattr(obj, "ttl_seconds", None):
            return True
    return False

def has_media(message: Message) -> bool:
    """Check if message contains any downloadable media."""
    if not message:
        return False
    for attr in ("photo", "video", "voice", "video_note", "document", "audio", "animation", "sticker"):
        if getattr(message, attr, None):
            return True
    return False

def get_media_type(message: Message) -> str:
    """Identify the media category for caption display."""
    if is_timed_media(message):
        return "Timed / Disappearing Media ⏳"
    if message.photo:
        return "Photo 🖼️"
    if message.video:
        return "Video 🎥"
    if message.voice:
        return "Voice Note 🎙️"
    if message.video_note:
        return "Video Note (Round) 📹"
    if message.document:
        return f"Document ({message.document.file_name or 'File'}) 📄"
    if message.audio:
        return f"Audio ({message.audio.title or 'Track'}) 🎵"
    if message.animation:
        return "GIF / Animation 🎞️"
    if message.sticker:
        return "Sticker 🎨"
    return "Media File 💾"

async def save_and_forward_media(client: Client, message: Message, is_auto: bool = False) -> bool:
    """
    Downloads the given media message and delivers it uncompressed
    to the user's Telegram Saved Messages ('me').
    """
    if not has_media(message):
        return False

    msg_key = (message.chat.id, message.id)
    async with _save_lock:
        if msg_key in _saved_message_keys:
            logger.info(f"Message {msg_key} already processed, skipping.")
            return True
        _saved_message_keys.add(msg_key)

    file_path = None
    try:
        logger.info(f"Downloading media from chat {message.chat.id}, msg {message.id}...")
        file_path = await client.download_media(message, file=str(DOWNLOADS_DIR) + "/")
        if not file_path or not os.path.exists(file_path):
            logger.error(f"Download failed for message {message.id}")
            async with _save_lock:
                _saved_message_keys.discard(msg_key)
            return False

        # Build sender information
        sender = message.from_user
        if sender:
            sender_name = sender.first_name or "Unknown"
            sender_uname = f"@{sender.username}" if sender.username else f"ID: {sender.id}"
            sender_str = f"{sender_name} ({sender_uname})"
        else:
            sender_str = message.chat.title or str(message.chat.id)

        chat_title = message.chat.title or message.chat.first_name or "Direct Chat"
        media_type = get_media_type(message)
        source_label = "Auto-Captured Timed Media" if is_auto else "Manual SaveIt Request"

        caption = (
            f"💾 **`[ SaveIt Media Vault ]`**\n\n"
            f"📁 **`Source:`** `{source_label}`\n"
            f"👤 **`From:`** `{sender_str}`\n"
            f"💬 **`Chat:`** `{chat_title}`\n"
            f"📦 **`Type:`** `{media_type}`\n"
            f"⚡ **`Quality:`** `Original / Uncompressed`"
        )

        # Deliver to user's personal Saved Messages
        logger.info(f"Forwarding file {file_path} to Saved Messages ('me')...")
        await client.send_document(
            chat_id="me",
            document=file_path,
            caption=caption,
            force_document=True
        )
        logger.info(f"Successfully saved media to Saved Messages for {client.me.first_name}")
        return True

    except Exception as e:
        logger.error(f"Error saving media {msg_key}: {e}", exc_info=True)
        async with _save_lock:
            _saved_message_keys.discard(msg_key)
        return False
    finally:
        # Clean up local file from disk immediately
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {file_path}: {e}")
