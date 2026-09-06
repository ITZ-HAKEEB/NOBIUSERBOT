import logging
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from database.db import (
    add_favorite_user,
    remove_favorite_user,
    get_favorite_users,
    clear_favorite_users
)

logger = logging.getLogger(__name__)

async def extract_target_user(bot: Client, message: Message):
    """Extract user from replied message or argument (ID/username)."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user

    if len(message.command) > 1:
        target_raw = message.command[1].strip()
        try:
            target_id = int(target_raw) if target_raw.lstrip("-").isdigit() else target_raw
            return await bot.get_users(target_id)
        except Exception as e:
            logger.warning(f"Could not resolve target user '{target_raw}': {e}")
            return None

    return None


@Client.on_message(filters.command(["addfav", "fav"]))
async def add_fav_handler(bot: Client, message: Message):
    """Add a user to the sender's favorites list."""
    target_user = await extract_target_user(bot, message)

    if not target_user:
        return await message.reply_text(
            "⚠️ **`[ Usage: /addfav ]`**\n\n"
            "• **`Reply to any user's message with /addfav`**\n"
            "• **`Or use: /addfav @username or /addfav USER_ID`**"
        )

    if target_user.is_bot:
        return await message.reply_text("❌ **`Cannot add bot accounts to favorites.`**")

    owner_id = message.from_user.id
    await add_favorite_user(
        owner_id=owner_id,
        fav_user_id=target_user.id,
        fav_first_name=target_user.first_name or "Friend",
        fav_username=target_user.username
    )

    await message.reply_text(
        "⭐ **`[ Added to Favorites! ]`**\n\n"
        f"👤 **`Name:`** `{target_user.first_name}`\n"
        f"🆔 **`ID:`** `{target_user.id}`\n"
        f"🔗 **`Username:`** `@{target_user.username or 'None'}`\n\n"
        "⚡ **`Fast-tag favorites anytime using /ftag <text> or .ftag <text>!`**"
    )


@Client.on_message(filters.command(["remfav", "delfav"]))
async def rem_fav_handler(bot: Client, message: Message):
    """Remove a user from favorites list."""
    target_user = await extract_target_user(bot, message)

    if not target_user:
        return await message.reply_text(
            "⚠️ **`[ Usage: /remfav ]`**\n\n"
            "• **`Reply to user's message with /remfav`**\n"
            "• **`Or use: /remfav @username or /remfav USER_ID`**"
        )

    owner_id = message.from_user.id
    removed = await remove_favorite_user(owner_id, target_user.id)

    if removed:
        await message.reply_text(
            f"🗑️ **`[ Removed from Favorites! ]`**\n\n"
            f"• **`User:`** `{target_user.first_name}` (`{target_user.id}`)"
        )
    else:
        await message.reply_text("ℹ️ **`This user was not found in your favorites list.`**")


@Client.on_message(filters.command(["favs", "myfavs", "favorites"]))
async def list_favs_handler(bot: Client, message: Message):
    """List all saved favorite users."""
    owner_id = message.from_user.id
    favs = await get_favorite_users(owner_id)

    if not favs:
        return await message.reply_text(
            "⭐ **`[ No Favorite Users Saved! ]`**\n\n"
            "**`Add your friends to favorites with:`**\n"
            "• **`/addfav @username`**\n"
            "• **`Or reply to their message with /addfav`**"
        )

    lines = [f"⭐ **`[ Your Favorite Users ({len(favs)}) ]`**\n"]
    for i, f in enumerate(favs, 1):
        clean_name = (f["fav_first_name"] or "Friend").replace("[", "").replace("]", "")
        uname_str = f"@{f['fav_username']}" if f["fav_username"] else "No username"
        lines.append(f"{i}. [{clean_name}](tg://user?id={f['fav_user_id']}) — `{uname_str}` (`{f['fav_user_id']}`)")

    lines.append("\n⚡ **`Fast Tag Commands:`**")
    lines.append("• **`/ftag <message>`** `— Tag your favorites in groups`")
    lines.append("• **`.ftag <message>`** `— Fast tag from your account directly`")
    lines.append("• **`/remfav <id>`** `— Remove a user`")
    lines.append("• **`/clearfavs`** `— Delete all favorites`")

    await message.reply_text("\n".join(lines), disable_web_page_preview=True)


@Client.on_message(filters.command("clearfavs"))
async def clear_favs_handler(bot: Client, message: Message):
    """Clear all saved favorites."""
    owner_id = message.from_user.id
    await clear_favorite_users(owner_id)
    await message.reply_text("🗑️ **`[ All Favorite Users Cleared! ]`**")
