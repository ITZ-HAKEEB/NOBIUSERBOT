import logging
import asyncio
from typing import Optional
from pyrogram import Client, errors
from pyrogram.types import Message, User
from database.db import (
    DEFAULT_AUTO_MESSAGE,
    get_auto_message_settings,
    has_received_auto_message,
    mark_auto_message_sent
)

logger = logging.getLogger(__name__)

# Mutex to avoid duplicate greetings during concurrent incoming messages from the same user
_auto_msg_lock = asyncio.Lock()
_processing_peers = set()


def format_auto_message(template: str, peer: User, assistant: Optional[User] = None) -> str:
    """Format the auto-responder template with peer and assistant variables."""
    first_name = peer.first_name or "Friend"
    last_name = peer.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{peer.username}" if peer.username else first_name
    mention = f"[{first_name}](tg://user?id={peer.id})"
    my_name = (assistant.first_name or "Assistant") if assistant else "Assistant"

    replacements = {
        "{name}": first_name,
        "{first_name}": first_name,
        "{last_name}": last_name,
        "{full_name}": full_name,
        "{username}": username,
        "{mention}": mention,
        "{id}": str(peer.id),
        "{my_name}": my_name,
    }

    result = template
    for placeholder, val in replacements.items():
        result = result.replace(placeholder, val)
    return result


async def handle_incoming_private_message(client: Client, message: Message):
    """
    Evaluates incoming private message sent to the assistant client.
    If it is the first time the sender messages the assistant, automatically
    sends the configured greeting message.
    """
    if not message or not message.from_user:
        return

    peer = message.from_user

    # Do not reply to bots, services, or messages from self
    if peer.is_bot or getattr(message, "service", False):
        return
    if client.me and peer.id == client.me.id:
        return

    assistant_id = client.me.id if client.me else None
    if not assistant_id:
        return

    lock_key = (assistant_id, peer.id)
    async with _auto_msg_lock:
        if lock_key in _processing_peers:
            return
        _processing_peers.add(lock_key)

    try:
        # Check if feature is enabled for this assistant
        settings = await get_auto_message_settings(assistant_id)
        if not settings.get("is_enabled", True):
            return

        # Check if this peer has already been sent an auto-message
        already_greeted = await has_received_auto_message(assistant_id, peer.id)
        if already_greeted:
            return

        # Mark as sent immediately to avoid race conditions on subsequent messages
        await mark_auto_message_sent(assistant_id, peer.id)

        # Prepare formatted response
        template = settings.get("message") or DEFAULT_AUTO_MESSAGE
        reply_text = format_auto_message(template, peer, client.me)

        # Small human-like delay (0.5s)
        await asyncio.sleep(0.5)

        logger.info(f"Sending first-time Auto DM from assistant {assistant_id} to {peer.id} ({peer.first_name})")
        await message.reply_text(reply_text, disable_web_page_preview=True)

    except errors.FloodWait as f:
        logger.warning(f"FloodWait of {f.value}s while attempting to send auto-message to {peer.id}")
    except (errors.UserIsBlocked, errors.PeerIdInvalid, errors.InputUserDeactivated):
        logger.warning(f"Cannot send auto-message to {peer.id}: user blocked/invalid/deactivated")
    except Exception as e:
        logger.error(f"Failed to send auto-responder message to {peer.id}: {e}", exc_info=True)
    finally:
        async with _auto_msg_lock:
            _processing_peers.discard(lock_key)
