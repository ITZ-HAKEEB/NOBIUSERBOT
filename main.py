import asyncio
import logging
import sys
from pyrogram import Client, idle
import config
from database.db import init_db
from core.client_manager import client_manager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TaggerBot")

async def main():
    logger.info("Starting Telegram Self ID Tagger Bot...")

    if not config.is_configured():
        logger.error(
            "Missing configuration! Please copy .env.example to .env and fill in "
            "API_ID, API_HASH, and BOT_TOKEN."
        )
        sys.exit(1)

    # 1. Initialize SQLite database
    logger.info("Initializing database...")
    await init_db()

    # 2. Initialize Main Bot client
    bot = Client(
        name="tagger_bot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
        plugins=dict(root="plugins"),
        in_memory=True
    )

    try:
        await bot.start()
        bot_info = await bot.get_me()
        logger.info(f"Bot started successfully: @{bot_info.username} ({bot_info.first_name})")

        # 3. Load saved user Self ID sessions
        await client_manager.load_all_sessions()

        logger.info("Bot is active and ready to handle tagging requests.")
        await idle()

    except Exception as e:
        logger.critical(f"Fatal error during execution: {e}", exc_info=True)
    finally:
        logger.info("Shutting down bot and disconnecting all active clients...")
        await client_manager.stop_all()
        if bot.is_connected:
            await bot.stop()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated.")
