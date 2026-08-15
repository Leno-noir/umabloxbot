import os

from dotenv import load_dotenv

#load environment variables from .env file
load_dotenv()


def env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable using a documented, strict format."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Discord bot token and MongoDB connection URI.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
APPLICATION_MONGODB_DATABASE = os.getenv("APPLICATION_MONGODB_DATABASE", "umablox_application").strip() or "umablox_application"

# Kept non-fatal at import time so tooling and tests can import this module.
try:
    MAIN_GUILD_ID = int(os.getenv("MAIN_GUILD_ID", "0"))
except ValueError:
    MAIN_GUILD_ID = 0

ROTECTOR_API_KEY = os.getenv("ROTECTOR_API_KEY")
ROTECTOR_API_BASE_URL = os.getenv("ROTECTOR_API_BASE_URL", "https://roscoe.rotector.com")
BLOXLINK_API_KEY = os.getenv("BLOXLINK_API_KEY")
BLOXLINK_API_BASE_URL = os.getenv("BLOXLINK_API_BASE_URL", "https://api.blox.link/v4/public")
ROVER_API_BASE_URL = os.getenv("ROVER_API_BASE_URL", "https://registry.rover.link/api")
BOT_ENV = os.getenv("BOT_ENV", "production").strip().lower()
IS_DEVELOPMENT = BOT_ENV in {"development", "dev", "local"}
ROTECTOR_ENABLED = env_flag("ROTECTOR_ENABLED", default=False)


def validate_runtime_config() -> None:
    """Fail fast with actionable errors before the bot connects to Discord."""
    missing = [
        name
        for name, value in {
            "DISCORD_TOKEN": DISCORD_TOKEN,
            "MONGODB_URI": MONGODB_URI,
        }.items()
        if not value
    ]
    if MAIN_GUILD_ID <= 0:
        missing.append("MAIN_GUILD_ID (a positive Discord guild ID)")
    if missing:
        raise RuntimeError("Missing or invalid required configuration: " + ", ".join(missing))


#color constants used in embeds throughout the bot
class Colors:
    RED = 0xE74C3C
    GREEN = 0x2ECC71
    BLUE = 0x3498DB
    YELLOW = 0xF1C40F
    GRAY = 0x95A5A6
