import os

from dotenv import load_dotenv

#load environment variables from .env file
load_dotenv()


#discord bot token for authentication
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

#mongodb connection uri
MONGODB_URI = os.getenv("MONGODB_URI")

#main guild (server) id where the bot operates
#defaults to 0 if not set in .env
MAIN_GUILD_ID = int(os.getenv("MAIN_GUILD_ID", 0))


#color constants used in embeds throughout the bot
class Colors:
    RED = 0xE74C3C
    GREEN = 0x2ECC71
    BLUE = 0x3498DB
    YELLOW = 0xF1C40F
    GRAY = 0x95A5A6
