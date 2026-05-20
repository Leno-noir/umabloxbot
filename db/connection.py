"""MongoDB connection management using Motor (async driver).

Handles the lifecycle of the MongoDB connection:
- Establishes connection on bot startup
- Provides database access throughout the bot
- Closes connection gracefully on shutdown
"""

from motor.motor_asyncio import AsyncIOMotorClient
from core import MONGODB_URI

# Global MongoDB client instance (None until connect() is called)
_client: AsyncIOMotorClient | None = None # type: ignore

# returns the umablox database from the connected MongoDB client
def get_db():
    return _client["umablox"]

# establishes connection to MongoDB and verifies connectivity with a ping
# called once on bot startup in bot.main()
async def connect():
    global _client
    _client = AsyncIOMotorClient(MONGODB_URI)
    await _client.admin.command("ping")
    print("✅ MongoDB connected successfully")

# closes the MongoDB connection gracefully when the bot shuts down
async def disconnect():
    if _client:
        _client.close()