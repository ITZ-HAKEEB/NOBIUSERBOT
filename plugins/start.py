from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db import add_or_update_user, get_user
from utils.fonts import to_mono

START_TEXT = """
✨ **`[ ⎯⎯ Sᴇʟғ ID Tᴀɢɢᴇʀ Bᴏᴛ ⎯⎯ ]`** ✨

**`This bot allows you to link your own Telegram account (Self ID) to tag group members seamlessly — bypassing Bot API limits!`**

🔥 **`[ Fᴇᴀᴛᴜʀᴇs ]`**
• **`Tag all members without username restrictions`**
• **`Smart batches with anti-floodwait safety`**
• **`Auto DM Welcome responder for first-time private messages`**
• **`Direct selfbot prefixes (.tag, .etag, .automsg, .stop)`**
• **`SaveIt timed/disappearing media auto-saver`**
• **`Instant stop and cancellation controls`**

👇 **`Choose an option below to proceed:`**
"""

HELP_TEXT = """
📖 **`[ Cᴏᴍᴍᴀɴᴅs & Usᴀɢᴇ Gᴜɪᴅᴇ ]`**

👥 **`Group Tagging Commands:`**
• **`/tag <text>`** `— Tag members in clean batches`
• **`/utag <text>`** `— Alias for /tag`
• **`/etag <text>`** `— Tag with randomized emojis`
• **`/admintag <text>`** `— Mention group admins only`
• **`/stop`** `— Instantly cancel active tagging`

🤖 **`Assistant Auto DM Responder:`**
• **`/setautomsg <text>`** `— Set greeting message for first-time PM senders`
• **`/automsg`** `— View status & auto-message preview`
• **`/automsg on|off`** `— Enable or disable auto DM responder`
• **`/resetautomsg`** `— Reset auto-message to default template`
• **`/cleargreeted`** `— Clear greeted history to re-greet contacts`

⭐ **`Favorite Users & Fast Tag:`**
• **`/ftag <text>`** `— Fast tag only your favorite users`
• **`.ftag <text>`** `— Direct account fast tag`
• **`/addfav <@user>`** `— Add a user to your favorites`
• **`/remfav <@user>`** `— Remove a user from favorites`
• **`/favs`** `— List all saved favorite users`
• **`/clearfavs`** `— Clear all favorite users`

💾 **`SaveIt Media Vault (Timed & Restricted Saver):`**
• **`.saveit`** `(or /saveit) — Reply to any media or view-once to save to Saved Messages`
• **`/autosave`** `— Toggle auto-saving incoming disappearing photos/videos`
• **`/autosave on|off`** `— Enable or disable auto-saving timed media`

⚡ **`Direct Account Prefixes:`**
• **`.tag <text>`**
• **`.etag <text>`**
• **`.ftag <text>`**
• **`.admintag <text>`**
• **`.setautomsg <text>`**
• **`.automsg`**
• **`.resetautomsg`**
• **`.cleargreeted`**
• **`.saveit`**
• **`.stop`**

🔒 **`Private Chat Setup:`**
• **`/gen_session`** `— Interactive session generator`
• **`/login <session>`** `— Link Pyrogram string session`
• **`/login_phone`** `— Step-by-step OTP login wizard`
• **`/myaccount`** `— View connected Self ID details`
• **`/logout`** `— Revoke and remove saved session`
"""

ABOUT_TEXT = """
🤖 **`[ Aʙᴏᴜᴛ Sᴇʟғ ID Tᴀɢɢᴇʀ & SᴀᴠᴇIᴛ Bᴏᴛ ]`**

• **`Engine:`** `Pyrogram v2 MTProto Client`
• **`Architecture:`** `Asyncio Multi-Client Manager`
• **`Auto Responder:`** `First-Time DM Welcome Responder`
• **`Vault:`** `SaveIt Auto-Saver for Timed & View-Once Media`
• **`Database:`** `Async SQLite Storage`
• **`Pacing:`** `2.5s Anti-Flood Auto Backoff`
"""

def get_start_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"⚡ {to_mono('Generate Session String')}", callback_data="btn_gen_session")
        ],
        [
            InlineKeyboardButton(f"💾 {to_mono('SaveIt Media Vault')}", callback_data="btn_saveit"),
            InlineKeyboardButton(f"🤖 {to_mono('Auto DM Responder')}", callback_data="btn_automsg")
        ],
        [
            InlineKeyboardButton(f"⭐ {to_mono('Favorite Users')}", callback_data="btn_favs"),
            InlineKeyboardButton(f"🔑 {to_mono('Connect Self ID')}", callback_data="btn_connect")
        ],
        [
            InlineKeyboardButton(f"📖 {to_mono('Commands')}", callback_data="btn_help"),
            InlineKeyboardButton(f"ℹ️ {to_mono('About')}", callback_data="btn_about")
        ],
        [
            InlineKeyboardButton(f"👤 {to_mono('My Account')}", callback_data="btn_myaccount")
        ]
    ])



def get_back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
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
            "⚡ **`[ Pyrogram v2 Session Generator ]`**\n\n"
            "**`Generate a session string for your Telegram account directly inside this chat:`**\n\n"
            "🔹 **`In-Bot Generator (Recommended):`**\n"
            "**`Click the button below to start. The bot will request your phone number, send a Telegram OTP, and generate your string!`**\n\n"
            "🔹 **`Terminal Script:`**\n"
            "**`Run python3 generate_session.py on your machine.`**\n\n"
            "👇 **`Click below to start generating:`**"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🚀 {to_mono('Start In-Bot Generation')}", callback_data="btn_start_gen_wizard")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(gen_text, reply_markup=markup)
    elif data == "btn_start_gen_wizard":
        from plugins.login import start_interactive_login
        await start_interactive_login(client, user_id, query.message.reply_text)
    elif data == "btn_connect":
        connect_instructions = (
            "🔑 **`[ Connect Your Self ID ]`**\n\n"
            "**`Method 1 (In-Bot Session Generator):`**\n"
            "**`Tap Generate Session String on the menu or send /gen_session.`**\n\n"
            "**`Method 2 (Paste Existing String Session):`**\n"
            "**`Send: /login YOUR_PYROGRAM_STRING_SESSION`**\n\n"
            "💡 **`Your session string is stored safely in local encrypted SQLite.`**"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚡ {to_mono('Generate Session Now')}", callback_data="btn_gen_session")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(connect_instructions, reply_markup=markup)
    elif data == "btn_favs":
        from database.db import get_favorite_users
        favs = await get_favorite_users(user_id)
        if not favs:
            fav_text = (
                "⭐ **`[ Favorite Users ]`**\n\n"
                "**`You have no favorite users saved yet!`**\n\n"
                "💡 **`How to add your favorites:`**\n"
                "• **`/addfav @username`**\n"
                "• **`Or reply to their message with /addfav`**\n\n"
                "⚡ **`Fast Tag in any group:`**\n"
                "• **`/ftag <message>`** `— Fast tag via Bot`\n"
                "• **`.ftag <message>`** `— Fast tag via your account`"
            )
        else:
            lines = [f"⭐ **`[ Your Favorite Users ({len(favs)}) ]`**\n"]
            for i, f in enumerate(favs, 1):
                clean_name = (f["fav_first_name"] or "Friend").replace("[", "").replace("]", "")
                uname_str = f"@{f['fav_username']}" if f["fav_username"] else "No username"
                lines.append(f"{i}. [{clean_name}](tg://user?id={f['fav_user_id']}) — `{uname_str}`")
            lines.append("\n⚡ **`Fast-tag them anytime in groups with /ftag or .ftag!`**")
            fav_text = "\n".join(lines)

        await query.message.edit_text(fav_text, reply_markup=get_back_button(), disable_web_page_preview=True)
    elif data == "btn_saveit":
        from database.db import get_saveit_setting
        is_on = await get_saveit_setting(user_id)
        state_str = "🟢 **`ENABLED`**" if is_on else "🔴 **`DISABLED`**"
        btn_action = f"🔴 {to_mono('Disable Auto-Saver')}" if is_on else f"🟢 {to_mono('Enable Auto-Saver')}"

        saveit_text = (
            "💾 **`[ SaveIt Media Vault ]`**\n\n"
            f"• **`Auto-Save Disappearing Media:`** {state_str}\n\n"
            "🔥 **`What SaveIt Does:`**\n"
            "• **`Auto-captures incoming view-once / disappearing photos & videos`**\n"
            "• **`Saves restricted media (bypasses forwarding blocks)`**\n"
            "• **`Sends uncompressed original files straight to your Saved Messages`**\n\n"
            "💡 **`Manual Usage:`**\n"
            "**`Reply to ANY photo, video or voice note with .saveit (or /saveit)!`**"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_action, callback_data="btn_toggle_autosave")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(saveit_text, reply_markup=markup)
    elif data == "btn_toggle_autosave":
        from database.db import get_saveit_setting, set_saveit_setting
        is_on = await get_saveit_setting(user_id)
        new_state = not is_on
        await set_saveit_setting(user_id, new_state)

        state_str = "🟢 **`ENABLED`**" if new_state else "🔴 **`DISABLED`**"
        btn_action = f"🔴 {to_mono('Disable Auto-Saver')}" if new_state else f"🟢 {to_mono('Enable Auto-Saver')}"

        saveit_text = (
            "💾 **`[ SaveIt Media Vault ]`**\n\n"
            f"• **`Auto-Save Disappearing Media:`** {state_str}\n\n"
            "🔥 **`What SaveIt Does:`**\n"
            "• **`Auto-captures incoming view-once / disappearing photos & videos`**\n"
            "• **`Saves restricted media (bypasses forwarding blocks)`**\n"
            "• **`Sends uncompressed original files straight to your Saved Messages`**\n\n"
            "💡 **`Manual Usage:`**\n"
            "**`Reply to ANY photo, video or voice note with .saveit (or /saveit)!`**"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_action, callback_data="btn_toggle_autosave")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(saveit_text, reply_markup=markup)
    elif data == "btn_automsg":
        from plugins.automsg import get_effective_assistant_id
        from database.db import get_auto_message_settings
        assistant_id = await get_effective_assistant_id(user_id)
        settings = await get_auto_message_settings(assistant_id)

        is_on = settings["is_enabled"]
        state_str = "🟢 **`ENABLED`**" if is_on else "🔴 **`DISABLED`**"
        type_str = "Custom Message" if settings.get("is_custom") else "Default Template"
        btn_action = f"🔴 {to_mono('Disable Auto DM')}" if is_on else f"🟢 {to_mono('Enable Auto DM')}"

        automsg_text = (
            "🤖 **`[ Assistant Auto DM Responder ]`**\n\n"
            f"• **`Status:`** {state_str}\n"
            f"• **`Template Type:`** `{type_str}`\n\n"
            f"📝 **`Current Auto Message:`**\n{settings['message']}\n\n"
            "💡 **`How it works:`**\n"
            "• **`Sent automatically only the first time someone DMs your assistant in private.`**\n"
            "• **`Customize via:`** `/setautomsg <text>` or `.setautomsg <text>`\n"
            "• **`Reset message:`** `/resetautomsg`\n"
            "• **`Clear history:`** `/cleargreeted`"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_action, callback_data="btn_toggle_automsg")],
            [InlineKeyboardButton(f"🔄 {to_mono('Reset to Default')}", callback_data="btn_reset_automsg")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(automsg_text, reply_markup=markup)
    elif data == "btn_toggle_automsg":
        from plugins.automsg import get_effective_assistant_id
        from database.db import get_auto_message_settings, set_auto_message_enabled
        assistant_id = await get_effective_assistant_id(user_id)
        settings = await get_auto_message_settings(assistant_id)
        new_state = not settings["is_enabled"]
        await set_auto_message_enabled(assistant_id, new_state)
        if assistant_id != user_id:
            await set_auto_message_enabled(user_id, new_state)

        state_str = "🟢 **`ENABLED`**" if new_state else "🔴 **`DISABLED`**"
        type_str = "Custom Message" if settings.get("is_custom") else "Default Template"
        btn_action = f"🔴 {to_mono('Disable Auto DM')}" if new_state else f"🟢 {to_mono('Enable Auto DM')}"

        automsg_text = (
            "🤖 **`[ Assistant Auto DM Responder ]`**\n\n"
            f"• **`Status:`** {state_str}\n"
            f"• **`Template Type:`** `{type_str}`\n\n"
            f"📝 **`Current Auto Message:`**\n{settings['message']}\n\n"
            "💡 **`How it works:`**\n"
            "• **`Sent automatically only the first time someone DMs your assistant in private.`**\n"
            "• **`Customize via:`** `/setautomsg <text>` or `.setautomsg <text>`\n"
            "• **`Reset message:`** `/resetautomsg`\n"
            "• **`Clear history:`** `/cleargreeted`"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_action, callback_data="btn_toggle_automsg")],
            [InlineKeyboardButton(f"🔄 {to_mono('Reset to Default')}", callback_data="btn_reset_automsg")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(automsg_text, reply_markup=markup)
    elif data == "btn_reset_automsg":
        from plugins.automsg import get_effective_assistant_id
        from database.db import get_auto_message_settings, reset_auto_message_text
        assistant_id = await get_effective_assistant_id(user_id)
        await reset_auto_message_text(assistant_id)
        if assistant_id != user_id:
            await reset_auto_message_text(user_id)
        settings = await get_auto_message_settings(assistant_id)

        state_str = "🟢 **`ENABLED`**" if settings["is_enabled"] else "🔴 **`DISABLED`**"
        btn_action = f"🔴 {to_mono('Disable Auto DM')}" if settings["is_enabled"] else f"🟢 {to_mono('Enable Auto DM')}"

        automsg_text = (
            "🤖 **`[ Assistant Auto DM Responder ]`**\n\n"
            f"• **`Status:`** {state_str}\n"
            f"• **`Template Type:`** `Default Template`\n\n"
            f"📝 **`Current Auto Message:`**\n{settings['message']}\n\n"
            "💡 **`How it works:`**\n"
            "• **`Sent automatically only the first time someone DMs your assistant in private.`**\n"
            "• **`Customize via:`** `/setautomsg <text>` or `.setautomsg <text>`\n"
            "• **`Reset message:`** `/resetautomsg`\n"
            "• **`Clear history:`** `/cleargreeted`"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_action, callback_data="btn_toggle_automsg")],
            [InlineKeyboardButton(f"🔄 {to_mono('Reset to Default')}", callback_data="btn_reset_automsg")],
            [InlineKeyboardButton(f"🔙 {to_mono('Back to Menu')}", callback_data="btn_back")]
        ])
        await query.message.edit_text(automsg_text, reply_markup=markup)
    elif data == "btn_myaccount":

        user_info = await get_user(user_id)
        if user_info and user_info.get("string_session"):
            status_text = (
                "👤 **`[ Connected Self ID Account ]`**\n\n"
                f"• **`Name:`** `{user_info.get('self_first_name', 'Unknown')}`\n"
                f"• **`Username:`** `@{user_info.get('self_username') or 'None'}`\n"
                f"• **`User ID:`** `{user_info.get('self_user_id')}`\n"
                f"• **`Status:`** `🟢 Active & Ready`\n\n"
                "**`To disconnect this account, send /logout.`**"
            )
        else:
            status_text = (
                "⚠️ **`[ No Self ID Connected! ]`**\n\n"
                "**`You have not linked your Telegram account yet.`**\n"
                "**`Click Generate Session String or send /login_phone to connect.`**"
            )
        await query.message.edit_text(status_text, reply_markup=get_back_button())

    await query.answer()


