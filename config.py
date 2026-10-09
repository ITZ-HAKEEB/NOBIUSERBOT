import os
from dotenv import load_dotenv

load_dotenv()

try:
    API_ID = int(os.getenv("API_ID", "0") or "0")
except ValueError:
    API_ID = 0

API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")
except ValueError:
    OWNER_ID = 0

DEFAULT_STRING_SESSION = os.getenv("DEFAULT_STRING_SESSION", "").strip()

try:
    TAG_DELAY = float(os.getenv("TAG_DELAY", "2.5") or "2.5")
except ValueError:
    TAG_DELAY = 2.5

try:
    USERS_PER_TAG = int(os.getenv("USERS_PER_TAG", "1") or "1")
except ValueError:
    USERS_PER_TAG = 1

DATABASE_PATH = os.getenv("DATABASE_PATH", "tagger_bot.db")

# MongoDB
MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "multitasking").strip()


def is_configured() -> bool:
    """Check if mandatory credentials are set."""
    return bool(API_ID and API_HASH and BOT_TOKEN)

