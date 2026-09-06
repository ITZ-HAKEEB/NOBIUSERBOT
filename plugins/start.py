from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db import add_or_update_user, get_user
import config

START_TEXT = """
✨ **Welcome to Self ID Tagger Bot!** ✨

This bot allows you to use your **own Telegram account (Self ID)** to tag group members seamlessly — without Bot API limits!

🔥 **Why Self ID?**
• Tags users even if they have no @username.
• Fetches all group members (bypassing Bot API 100-member caps).
• Runs via your account safely with customizable delays & anti-flood protection.

👇 **Choose an option below to get started:**
"""

HELP_TEXT = """
📖 **Commands & Usage Guide**

**Group Commands (Triggered via Bot or Self ID):**
• `/tag <message>` - Tag group members in batches with custom text.
• `/utag <message>` - Same as `/tag`.
• `/etag <message>` - Tag members decorated with stylish random emojis.
• `/admintag <message>` - Tag all group administrators.
• `/stop` or `/cancel` - Stop ongoing tagging immediately.

**Direct Selfbot Prefixes:**
You can also run commands straight from your account using `.` or `!`:
• `.tag <message>`
• `.etag <message>`
• `.admintag <message>`
• `.stop`

**Private Chat (Account & Session Setup):**
• `/login <string_session>` - Link your Pyrogram String Session instantly.
• `/login_phone` - Interactive phone + OTP login wizard in PM.
• `/myaccount` - Check your connected Self ID account status.
• `/logout` - Disconnect and delete your stored session.
• `/help` - Show this guide.
"""

ABOUT_TEXT = """
🤖 **About Self ID Tagger Bot**

• **Framework**: Pyrogram (MTProto)
• **Engine**: Asyncio Smart Batch Tagger
• **Speed**: Configurable delay between batches
• **Security**: Your session strings are encrypted locally in SQLite.

💡 Need a Pyrogram session? Run `python3 generate_session.py` or use the in-bot `/login_phone` wizard!
"""

def get_start_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Generate Session String", callback_data="btn_gen_session")
        ],
        [
            InlineKeyboardButton("🔑 Connect Self ID", callback_data="btn_connect"),
            InlineKeyboardButton("📖 Commands", callback_data="btn_help")
        ],
        [
            InlineKeyboardButton("ℹ️ About", callback_data="btn_about"),
            InlineKeyboardButton("👤 My Account", callback_data="btn_myaccount")
        ]
    ])

def get_back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_back")]
    ])

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await add_or_update_user(user.id, user.first_name, user.username)
    await message.reply_text(
        text=START_TEXT,
        reply_markup=get_start_buttons(),
        disable_web_page_preview=True
    )

@Client.on_message(filters.command("help"))
async def help_handler(client: Client, message: Message):
    await message.reply_text(
        text=HELP_TEXT,
        reply_markup=get_back_button() if message.chat.type.name == "PRIVATE" else None,
        disable_web_page_preview=True
    )

@Client.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "btn_back":
        await query.message.edit_text(START_TEXT, reply_markup=get_start_buttons())
    elif data == "btn_help":
        await query.message.edit_text(HELP_TEXT, reply_markup=get_back_button())
    elif data == "btn_about":
        await query.message.edit_text(ABOUT_TEXT, reply_markup=get_back_button())
    elif data == "btn_gen_session":
        gen_text = (
            "⚡ **Pyrogram v2 String Session Generator**\n\n"
            "You can generate a session string for your Telegram account directly inside this chat or via terminal.\n\n"
            "🔹 **In-Bot Generator (Recommended):**\n"
            "Click **Start Generation** below to begin. The bot will ask for your phone number, send you a Telegram code, and generate your session string!\n\n"
            "🔹 **Terminal Script:**\n"
            "Run `python3 generate_session.py` on your computer.\n\n"
            "👇 Click the button below to start generating right now:"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start In-Bot Generation", callback_data="btn_start_gen_wizard")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_back")]
        ])
        await query.message.edit_text(gen_text, reply_markup=markup)
    elif data == "btn_start_gen_wizard":
        from plugins.login import start_interactive_login
        await start_interactive_login(client, user_id, query.message.reply_text)
    elif data == "btn_connect":
        connect_instructions = (
            "🔑 **How to Connect Your Self ID:**\n\n"
            "**Method 1 (In-Bot Session Generator):**\n"
            "Click **⚡ Generate Session String** on the main menu or run `/login_phone`.\n\n"
            "**Method 2 (Paste Existing String Session):**\n"
            "Send: `/login YOUR_PYROGRAM_STRING_SESSION`\n\n"
            "💡 You can generate a string session on your computer with `python3 generate_session.py`."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Generate Session Now", callback_data="btn_gen_session")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_back")]
        ])
        await query.message.edit_text(connect_instructions, reply_markup=markup)
    elif data == "btn_myaccount":
        user_info = await get_user(user_id)
        if user_info and user_info.get("string_session"):
            status_text = (
                f"👤 **Connected Self ID Account:**\n\n"
                f"• **Name**: {user_info.get('self_first_name', 'Unknown')}\n"
                f"• **Username**: @{user_info.get('self_username') or 'None'}\n"
                f"• **User ID**: `{user_info.get('self_user_id')}`\n"
                f"• **Status**: 🟢 Active & Ready\n\n"
                f"To disconnect, send `/logout`."
            )
        else:
            status_text = (
                "⚠️ **No Self ID Connected!**\n\n"
                "You haven't linked your Telegram account yet.\n"
                "Click **⚡ Generate Session String** or send `/login_phone` to connect."
            )
        await query.message.edit_text(status_text, reply_markup=get_back_button())

    await query.answer()

