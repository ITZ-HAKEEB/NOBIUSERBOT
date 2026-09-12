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
    if not message:
        return

    peer = message.from_user
    if not peer:
        return

    # Ignore bots, service notifications, and official Telegram system accounts
    if peer.is_bot or getattr(message, "service", False) or peer.id in (777000, 42777):
        return

    # Ensure assistant user identity is available
    assistant = client.me
    if not assistant:
        try:
            assistant = await client.get_me()
            client.me = assistant
        except Exception as e:
            logger.warning(f"[AutoDM] Failed to resolve client.me: {e}")

    assistant_id = assistant.id if assistant else None
    if not assistant_id:
        return

    # Ignore messages sent by self
    if peer.id == assistant_id:
        return

    lock_key = (assistant_id, peer.id)
    async with _auto_msg_lock:
        if lock_key in _processing_peers:
            return
        _processing_peers.add(lock_key)

    try:
        msg_preview = (message.text[:25] + "...") if message.text else "media"
        logger.info(f"[AutoDM] Incoming PM for assistant {assistant_id} ({assistant.first_name}) from {peer.id} ({peer.first_name}): '{msg_preview}'")

        # 1. Check if feature is enabled for this assistant
        settings = await get_auto_message_settings(assistant_id)
        if not settings.get("is_enabled", True):
            logger.info(f"[AutoDM] Auto DM responder is disabled for assistant {assistant_id}")
            return

        # 2. Check if this peer has already received an auto-message from this assistant
        already_greeted = await has_received_auto_message(assistant_id, peer.id)
        if already_greeted:
            logger.info(f"[AutoDM] Peer {peer.id} ({peer.first_name}) has already been greeted by assistant {assistant_id}. Skipping.")
            return

        # 3. Format message template
        template = settings.get("message") or DEFAULT_AUTO_MESSAGE
        reply_text = format_auto_message(template, peer, assistant)

        logger.info(f"[AutoDM] First-time DM detected! Sending auto-reply to {peer.id} ({peer.first_name}) from assistant {assistant_id}...")

        # Small human-like pacing delay
        await asyncio.sleep(0.3)

        # 4. Deliver message: try reply_text first, fallback to send_message
        sent = False
        try:
            await message.reply_text(reply_text, disable_web_page_preview=True)
            sent = True
        except Exception as err:
            logger.warning(f"[AutoDM] message.reply_text failed ({err}), attempting client.send_message...")
            try:
                await client.send_message(chat_id=message.chat.id, text=reply_text, disable_web_page_preview=True)
                sent = True
            except Exception as send_err:
                logger.error(f"[AutoDM] client.send_message also failed: {send_err}")

        # 5. Mark as sent once message is successfully delivered
        if sent:
            await mark_auto_message_sent(assistant_id, peer.id)
            logger.info(f"[AutoDM] Successfully delivered auto DM to {peer.id} and recorded in database.")

    except errors.FloodWait as f:
        logger.warning(f"[AutoDM] FloodWait of {f.value}s encountered while sending auto-message to {peer.id}")
    except (errors.UserIsBlocked, errors.PeerIdInvalid, errors.InputUserDeactivated) as e:
        logger.warning(f"[AutoDM] Cannot message {peer.id} ({e}), recording as processed.")
        await mark_auto_message_sent(assistant_id, peer.id)
    except Exception as e:
        logger.error(f"[AutoDM] Unexpected error handling private message from {peer.id}: {e}", exc_info=True)
    finally:
        async with _auto_msg_lock:
            _processing_peers.discard(lock_key)
