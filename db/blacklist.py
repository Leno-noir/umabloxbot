"""Blacklist database operations for the MongoDB 'blacklist' collection.

Handles all database interactions for:
- Adding users to the blacklist
- Removing (marking as inactive) blacklist entries
- Querying blacklist status
- Retrieving history and logs

All dates are stored in UTC timezone for consistency across timezones.
"""

from datetime import datetime, timezone
from .connection import get_db

# MongoDB Document structure in the "blacklist" collection:
# {
#   discord_id:    str          # Discord user ID (unique lookup key)
#   roblox_id:     str          # Roblox user ID
#   roblox_user:   str          # Roblox username for display
#   reason:        str          # Why user was blacklisted
#   evidence:      str | None   # Link to evidence document (optional)
#   added_by:      str          # Discord user ID of who added them
#   added_at:      datetime     # When added (UTC)
#   active:        bool         # True = currently banned, False = removed
#   removed_by:    str | None   # Discord user ID of who removed them
#   removed_at:    datetime | None  # When removed (UTC)
#   remove_reason: str | None   # Why they were removed
# }

# adds a user to the blacklist with all required information
# automatically sets 'active' = True and 'added_at' = current UTC time
async def bl_add(discord_id: str, roblox_id: str, roblox_user: str,
                 reason: str, added_by: str, evidence: str | None = None) -> dict:
    db  = get_db()
    doc = {
        "discord_id":  discord_id,
        "roblox_id":   roblox_id,
        "roblox_user": roblox_user,
        "reason":      reason,
        "evidence":    evidence,
        "added_by":    added_by,
        "added_at":    datetime.now(timezone.utc),
        "active":      True,
    }
    await db.blacklist.insert_one(doc)
    return doc

# marks a user as inactive (removed from blacklist) while keeping history
# does NOT delete the document - just sets active=False for history keeping
async def bl_remove(discord_id: str, removed_by: str, reason: str) -> bool:
    db     = get_db()
    result = await db.blacklist.update_one(
        {"discord_id": discord_id, "active": True},
        {"$set": {
            "active":        False,
            "removed_by":    removed_by,
            "removed_at":    datetime.now(timezone.utc),
            "remove_reason": reason,
        }}
    )
    return result.modified_count > 0

# retrieves the active blacklist entry for a user
# use this to check if a user is on the active blacklist
async def bl_get(discord_id: str) -> dict | None:
    db = get_db()
    return await db.blacklist.find_one({"discord_id": discord_id, "active": True})

# checks if a user is currently on the active blacklist
# use this in on_member_join() to detect blacklisted users joining
async def bl_is_banned(discord_id: str) -> bool:
    return await bl_get(discord_id) is not None

# retrieves complete blacklist history for a user
# returns all blacklist entries (active and removed), sorted newest first
# use this for the /blacklist-history command to show all records
async def bl_history(discord_id: str) -> list[dict]:
    db     = get_db()
    cursor = db.blacklist.find({"discord_id": discord_id}).sort("added_at", -1)
    return await cursor.to_list(length=50)

# retrieves a paginated list of currently active bans
# returns tuple of (list of documents, total active ban count)
# use this for the /blacklist-list command with pagination
async def bl_list_active(skip: int = 0, limit: int = 10) -> tuple[list[dict], int]:
    db     = get_db()
    total  = await db.blacklist.count_documents({"active": True})
    cursor = db.blacklist.find({"active": True}).sort("added_at", -1).skip(skip).limit(limit)
    docs   = await cursor.to_list(length=limit)
    return docs, total

# retrieves a paginated log of ALL blacklist events across all users
# returns tuple of (list of documents, total event count)
# includes both active bans and historical removals
# use this for the /blacklist-log command with pagination
async def bl_global_log(skip: int = 0, limit: int = 10) -> tuple[list[dict], int]:
    db     = get_db()
    total  = await db.blacklist.count_documents({})
    cursor = db.blacklist.find({}).sort("added_at", -1).skip(skip).limit(limit)
    docs   = await cursor.to_list(length=limit)
    return docs, total