"""Blacklist database operations for the MongoDB 'blacklist' collection.

New schema: one document per user.
- current_* fields hold the active ban info
- history[] holds every ban/unban event ever
- active = True means currently banned

Document structure:
{
  discord_id:        str,
  roblox_id:         str,
  roblox_user:       str,
  active:            bool,

  # Only set when active = True
  current_reason:    str | None,
  current_evidence:  str | None,
  current_added_by:  str | None,
  current_added_at:  datetime | None,

  # Full event log — every ban and unban appended here
  history: [
    {
      reason:       str,
      evidence:     str | None,
      added_by:     str,
      added_at:     datetime,
      removed_by:   str | None,
      removed_at:   datetime | None,
      remove_reason: str | None,
    }
  ]
}
"""

from datetime import datetime, timezone
from .connection import get_db


async def bl_add(discord_id: str, roblox_id: str, roblox_user: str,
                 reason: str, added_by: str, evidence: str | None = None) -> dict:
    """
    Adds a user to the blacklist.

    Two cases:
    - User has never been blacklisted: creates a new document
    - User exists but is inactive: updates current_* and appends to history

    Returns the new history entry that was just created.
    """
    db  = get_db()
    now = datetime.now(timezone.utc)

    # This is the history entry we'll append regardless of case
    entry = {
        "reason":        reason,
        "evidence":      evidence,
        "roblox_id":        roblox_id,
        "roblox_user":      roblox_user,
        "added_by":      added_by,
        "added_at":      now,
        "removed_by":    None,
        "removed_at":    None,
        "remove_reason": None,
    }

    existing = await db.blacklist.find_one({"discord_id": discord_id})

    if existing is None:
        # First time this user is blacklisted — create the document
        await db.blacklist.insert_one({
            "discord_id":       discord_id,
            "roblox_id":        roblox_id,
            "roblox_user":      roblox_user,
            "active":           True,
            "current_reason":   reason,
            "current_evidence": evidence,
            "current_added_by": added_by,
            "current_added_at": now,
            "history":          [entry],
        })
    else:
        # User already has a document (was banned before) — update it
        # $set updates the current_* fields and active flag
        # $push appends the new entry to the history array
        # $set also updates roblox info in case it changed
        await db.blacklist.update_one(
            {"discord_id": discord_id},
            {
                "$set": {
                    "roblox_id":        roblox_id,
                    "roblox_user":      roblox_user,
                    "active":           True,
                    "current_reason":   reason,
                    "current_evidence": evidence,
                    "current_added_by": added_by,
                    "current_added_at": now,
                },
                "$push": {"history": entry},
            }
        )

    return entry


async def bl_remove(discord_id: str, removed_by: str, reason: str) -> bool:
    """
    Removes a user from the active blacklist.

    Sets active = False and clears current_* fields.
    Also updates the latest history entry with the removal info,
    so the history stays complete.

    Returns True if the user was found and removed, False otherwise.
    """
    db  = get_db()
    now = datetime.now(timezone.utc)

    # Find the active ban first — we need it to update the right history entry
    doc = await db.blacklist.find_one({"discord_id": discord_id, "active": True})
    if not doc:
        return False

    # Find the index of the latest history entry (the active ban)
    # It's always the last entry in the array
    last_index = len(doc["history"]) - 1

    # Update the document:
    # - Clear active status and current_* fields
    # - Fill in removal info on the last history entry using positional index
    await db.blacklist.update_one(
        {"discord_id": discord_id},
        {
            "$set": {
                "active":           False,
                "current_reason":   None,
                "current_evidence": None,
                "current_added_by": None,
                "current_added_at": None,
                # Update the specific history entry by its array index
                f"history.{last_index}.removed_by":    removed_by,
                f"history.{last_index}.removed_at":    now,
                f"history.{last_index}.remove_reason": reason,
            }
        }
    )
    return True


async def bl_get(discord_id: str) -> dict | None:
    """
    Returns the full document for a user if they are currently banned.
    Returns None if not banned or not found.

    Use this in on_member_join() to detect blacklisted users.
    """
    return await get_db().blacklist.find_one({"discord_id": discord_id, "active": True})


async def bl_is_banned(discord_id: str) -> bool:
    """Quick check — True if user is currently on the active blacklist."""
    return await bl_get(discord_id) is not None


async def bl_get_any(discord_id: str) -> dict | None:
    """
    Returns the document for a user regardless of active status.
    Use this for /blacklist-info — shows info even for past bans.
    """
    return await get_db().blacklist.find_one({"discord_id": discord_id})


async def bl_list_active(skip: int = 0, limit: int = 10) -> tuple[list[dict], int]:
    """
    Returns a paginated list of currently active bans + total count.
    Use this for /blacklist-list and the panel.
    """
    db     = get_db()
    total  = await db.blacklist.count_documents({"active": True})
    cursor = db.blacklist.find({"active": True}).sort("current_added_at", -1).skip(skip).limit(limit)
    docs   = await cursor.to_list(length=limit)
    return docs, total


async def bl_global_log(skip: int = 0, limit: int = 10) -> tuple[list[dict], int]:
    """
    Returns a paginated global log of blacklist events (ban/unban),
    newest first. Each history entry becomes one or two events.
    """
    db = get_db()
    docs = await db.blacklist.find({}).to_list(length=None)

    events: list[dict] = []
    for doc in docs:
        for entry in doc.get("history", []):
            # ban event
            events.append({
                "type": "ban",
                "discord_id": doc["discord_id"],
                "roblox_id": entry["roblox_id"],
                "roblox_user": entry["roblox_user"],
                "reason": entry["reason"],
                "by": entry["added_by"],
                "at": entry["added_at"],
                "evidence": entry.get("evidence"),
            })

            # unban event (if removed_at exists)
            if entry.get("removed_at"):
                events.append({
                    "type": "unban",
                    "discord_id": doc["discord_id"],
                    "roblox_id": doc["roblox_id"],
                    "roblox_user": doc["roblox_user"],
                    "reason": entry.get("remove_reason"),
                    "by": entry.get("removed_by"),
                    "at": entry["removed_at"],
                    "original_reason": entry["reason"],
                })

    events.sort(key=lambda e: e["at"], reverse=True)

    total = len(events)
    page_events = events[skip:skip + limit]
    return page_events, total



async def bl_history(discord_id: str) -> dict | None:
    """
    Returns the full document for a user including their complete history array.
    Use this for /blacklist-info and /blacklist-history commands.
    Returns None if the user is not found.
    """
    return await get_db().blacklist.find_one({"discord_id": discord_id})