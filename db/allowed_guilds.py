"""MongoDB helpers for observer guild allowlist management.

This collection defines which external guilds are officially part of the bot
network and allowed to use observer-only features.
"""

from datetime import datetime, timezone

from .connection import get_db

#add a guild to the allowlist or update it if it already exists
async def allowed_guild_add(
    guild_id: int,
    guild_name: str,
    added_by: str,
    server_type: str = "observer",
) -> dict:
    """Add or update an allowed guild in the network allowlist."""
    db = get_db()
    record = {
        "guild_id": guild_id,
        "guild_name": guild_name,
        "server_type": server_type,
        "enabled": True,
        "added_at": datetime.now(timezone.utc),
        "added_by": added_by,
    }
    
    await db.allowed_guilds.update_one(
        {"guild_id": guild_id},
        {"$set": record},
        upsert=True,
    )
    return record

#remove a guild from the allowlist (deletes the record entirely)
async def allowed_guild_remove(guild_id: int) -> bool:
    """Remove a guild from the allowlist."""
    db = get_db()
    result = await db.allowed_guilds.delete_one({"guild_id": guild_id})
    return result.deleted_count > 0

#fetch a single allowlist record by guild ID
async def allowed_guild_get(guild_id: int) -> dict | None:
    """Fetch a single allowed guild record."""
    db = get_db()
    return await db.allowed_guilds.find_one({"guild_id": guild_id})

#check if a guild is allowed and enabled in the allowlist, 
# used as a check for commands that should only work in observer guilds
async def allowed_guild_exists(guild_id: int) -> bool:
    """Check if a guild already exists in the allowlist."""
    return await allowed_guild_get(guild_id) is not None

#check if a guild is allowed and enabled in the allowlist,
# used as a check for commands that should only work in observer guilds
async def allowed_guild_is_enabled(guild_id: int) -> bool:
    """Return True only if the guild exists and is currently enabled."""
    doc = await allowed_guild_get(guild_id)
    return bool(doc and doc.get("enabled"))

#change the enabled status of a guild without deleting it,
async def allowed_guild_set_enabled(guild_id: int, enabled: bool) -> bool:
    """Enable or disable an allowed guild without deleting it."""
    db = get_db()
    result = await db.allowed_guilds.update_one(
        {"guild_id": guild_id},
        {"$set": {"enabled": enabled}},
    )
    return result.modified_count > 0

#gets a list of all allowed guilds in the database with pagination
async def allowed_guild_list(skip: int = 0, limit: int = 10) -> tuple[list[dict], int]:
    """Return paginated allowlist entries ordered by guild name."""
    db = get_db()
    total = await db.allowed_guilds.count_documents({})
    cursor = db.allowed_guilds.find({}).sort("guild_name", 1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return docs, total


#gets all currently enabled observer guilds, used by command sync/runtime checks
async def allowed_guild_list_enabled() -> list[dict]:
    """Return all enabled observer guilds."""
    db = get_db()
    cursor = db.allowed_guilds.find({"enabled": True, "server_type": "observer"}).sort("guild_name", 1)
    return await cursor.to_list(length=None)
