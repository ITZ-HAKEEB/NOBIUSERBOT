# 🏷️ Telegram Self ID Tagger Bot

A modern, high-performance Telegram Tagger Bot built with **Python 3**, **Pyrogram (MTProto)**, and **Asyncio**. 

Unlike standard Telegram Bot API bots that are restricted from viewing member lists or mentioning users without usernames in large groups, this bot allows users to connect their own **Telegram Account ("Self ID")** via a Pyrogram String Session or interactive OTP login. The bot uses that linked user account to smoothly tag group members in batches with anti-floodwait safety!

---

## ✨ Features

- 👤 **Self ID Integration**:
  - Connect your personal Telegram user account via Pyrogram String Session (`/login <string>`).
  - Interactive phone number + OTP login wizard directly inside the bot's private chat (`/login_phone`).
  - Safe local SQLite storage with session revocation (`/logout`, `/myaccount`).
- 🤖 **Assistant Auto DM Responder**:
  - Automatically greets anyone who messages your connected assistant account in private DM for the **first time**.
  - Customizable auto-reply message set by yourself (`/setautomsg` or `.setautomsg`).
  - Dynamic placeholders: `{name}`, `{first_name}`, `{last_name}`, `{username}`, `{mention}`, `{id}`, `{my_name}`.
  - Prevents repeated spamming by recording greeted contacts in the database.
  - Controls to enable/disable (`/automsg on|off`), reset to default (`/resetautomsg`), or clear history (`/cleargreeted`).
- 👥 **Smart Member Mentions**:
  - `/tag <message>` or `/utag <message>`: Tags all group members in clean batches (default: 5 members per message).
  - `/etag <optional text>`: Tags members decorated with stylish randomized emojis.
  - `/admintag <message>`: Quickly alerts and tags group administrators.
  - Automatic filtering: skips deleted accounts and bots.
- ⚡ **Dual Execution Modes**:
  - **Via Bot in Group**: Send `/tag <message>` in group, and the bot instructs your Self ID account to post the tags.
  - **Direct Selfbot Command**: You can also use prefixes straight from your own account: `.tag <message>`, `.etag`, `.setautomsg`, `.automsg`, `.stop`.
- 🛑 **Instant Stop Control**:
  - `/stop` or `.stop` halts active tagging runs immediately.
- 🛡️ **FloodWait & Ban Prevention**:
  - Configurable delay (default: 2.5s) between message batches.
  - Built-in automatic `FloodWait` detection and exponential backoff.
- 🚀 **Session Generator Included**:
  - Run `python3 generate_session.py` to generate a Pyrogram v2 string session in seconds.

---

## 🛠️ Prerequisites

1. **Python 3.9+**
2. **API_ID & API_HASH**: Obtain from [my.telegram.org](https://my.telegram.org) (under "API development tools").
3. **BOT_TOKEN**: Create a new bot with [@BotFather](https://t.me/BotFather) on Telegram.

---

## 🚀 Quick Setup & Installation

### 1. Clone or Open the Repository
```bash
cd "Multi tasking bot"
```

### 2. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your preferred editor:
```ini
API_ID=12345678
API_HASH=your_api_hash_here
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
OWNER_ID=123456789

# Optional: Default string session for a dedicated 24/7 selfbot tagger
DEFAULT_STRING_SESSION=

# Tagger tuning
TAG_DELAY=2.5
USERS_PER_TAG=5
```

### 4. Run the Bot
```bash
python3 main.py
```

---

## 🔑 How to Connect Your Self ID Account

There are two easy methods:

### Method A: Interactive Phone Login (Recommended for Mobile/End-users)
1. Message your bot in private chat: `/start`
2. Send `/login_phone`
3. Enter your phone number with country code (e.g. `+1234567890`).
4. Enter the login code sent by Telegram. *(Tip: Send digits separated by spaces, like `1 2 3 4 5`, to avoid Telegram message filters)*.
5. If 2FA cloud password is enabled, enter your password when prompted.
6. Done! Your account is connected.

### Method B: Pyrogram String Session
1. Run the included generator:
   ```bash
   python3 generate_session.py
   ```
2. Enter your `API_ID` and `API_HASH`, follow the prompt, and copy the generated session string.
3. In your bot's private chat, send:
   ```
   /login <PASTE_YOUR_STRING_SESSION>
   ```

---

## 💬 Command Reference

### 👥 Group Commands
| Command | Description |
| :--- | :--- |
| `/tag <message>` | Tags all chat members in batches with custom text |
| `/utag <message>` | Alias for `/tag` |
| `/etag <message>` | Tags members with vibrant emojis |
| `/admintag <message>` | Tags only group administrators |
| `/stop` or `/cancel` | Cancels any active tagging in the group |

### 🤖 Assistant Auto DM Responder Commands
| Command | Description |
| :--- | :--- |
| `/setautomsg <text>` | Set custom greeting message for first-time private messages |
| `/automsg` | View auto-responder status and message preview |
| `/automsg on` / `/automsg off` | Enable or disable auto responder |
| `/resetautomsg` | Reset message to the default template |
| `/cleargreeted` | Clear greeted contacts history so they get greeted again |

### 👤 Selfbot Direct Prefixes (From your user account)
| Prefix Command | Description |
| :--- | :--- |
| `.tag <message>` | Directly tag group members from your account |
| `.etag <message>` | Tag members with emojis |
| `.admintag <message>` | Tag admins |
| `.setautomsg <text>` | Set auto-responder greeting message from your account |
| `.automsg` | Check auto-responder status & controls |
| `.automsg on` / `off` | Enable / disable auto responder |
| `.resetautomsg` | Reset auto-message to default |
| `.cleargreeted` | Clear greeted contact history |
| `.saveit` | Reply to any photo/video to save to Saved Messages |
| `.stop` | Cancel tagging |

### 🔒 Private Chat Commands
| Command | Description |
| :--- | :--- |
| `/start` | Open interactive main menu with Auto DM Responder controls |
| `/help` | Detailed command help guide |
| `/login_phone` | Step-by-step phone & OTP login |
| `/login <session>` | Quick session string link |
| `/myaccount` | View connected Self ID account status |
| `/logout` | Revoke & remove your linked account |

### 👑 Owner Commands
| Command | Description |
| :--- | :--- |
| `/stats` | View total users, active sessions, and active jobs |
| `/broadcast <text>` | Broadcast announcement to all bot users |
| `/ping` | Check bot latency |

---

## 🐳 Docker Deployment

To run in the background using Docker Compose:
```bash
docker-compose up -d --build
```
To view logs:
```bash
docker-compose logs -f
```

---

## ⚖️ Safety & Telegram Terms
- Ensure your `TAG_DELAY` is not set too low (recommended: 2.0s - 3.0s).
- Avoid spamming groups where you do not have permission to mention members.
<p align="center">
  <a href="https://www.heroku.com/deploy?template=https://github.com/ITZ-HAKEEB/NOBIUSERBOT">
    <img src="https://img.shields.io/badge/Deploy%20to-Heroku-000000?style=for-the-badge&logo=heroku&logoColor=white" alt="🚀Deploy to Heroku">
  </a>
</p>
