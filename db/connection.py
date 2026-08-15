"""MongoDB connection management using Motor (async driver).

Handles the lifecycle of the MongoDB connection:
- Establishes connection on bot startup
- Provides database access throughout the bot
- Closes connection gracefully on shutdown
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient
from core.config import APPLICATION_MONGODB_DATABASE, MONGODB_URI

# Global MongoDB client instance (None until connect() is called)
_client: AsyncIOMotorClient | None = None # type: ignore
logger = logging.getLogger(__name__)

# returns the umablox database from the connected MongoDB client
def get_db():
    if _client is None:
        raise RuntimeError("MongoDB is not connected. Call connect() before accessing the database.")
    return _client["umablox"]


def get_application_db():
    """Return the isolated database used by user-installed app commands."""
    if _client is None:
        raise RuntimeError("MongoDB is not connected. Call connect() before accessing the database.")
    return _client[APPLICATION_MONGODB_DATABASE]

# establishes connection to MongoDB and verifies connectivity with a ping
# called once on bot startup in bot.main()
async def connect():
    global _client
    _client = AsyncIOMotorClient(MONGODB_URI)
    await _client.admin.command("ping")
    logger.info("MongoDB connected successfully")

# closes the MongoDB connection gracefully when the bot shuts down
async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None
