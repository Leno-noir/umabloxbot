from .connection import get_db

# sets the Discord channel where blacklist alerts are sent for a server
# called when user configures via /settings Blacklist section
# overwrites previous channel if one was set
async def guild_set_blacklist_logs_channel(guild_id: int, channel_id: int):
    db = get_db()
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {"$set": {"blacklist_logs_channel": channel_id}},
        upsert=True,
    )

# retrieves the configured blacklist log channel for a server
# returns channel ID if configured, None if no channel was set
# used to send alerts when users are added/removed from blacklist
async def guild_get_blacklist_logs_channel(guild_id: int) -> int | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc["blacklist_logs_channel"] if doc else None

# retrieves the local observer channel where join alerts should be posted
# returns channel ID if configured, None if no alert channel was set
async def guild_get_blacklisted_users_join_alert_channel(guild_id: int) -> int | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc["blacklisted_users_join_alert_channel"] if doc else None

# retrieves all configured settings for a server
# returns dictionary with all guild settings (empty dict if no config exists)
# used by /settings command to display current configuration
async def guild_get_settings(guild_id: int) -> dict:
    db  = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc or {}

# retrieves the manager role ID for a guild (used for command permissions)
# returns role ID if configured, None otherwise
# used by sync to restrict manager-only commands to authorized users
async def guild_get_manager_role_id(guild_id: int) -> int | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc.get("blacklist_manager_role_id") if doc else None

# updates one or more settings for a server
# called by /settings command when user saves configuration
# only specified keys are updated; existing settings not in 'updates' are preserved
# creates a new config document if one doesn't exist
async def guild_save_settings(guild_id: int, updates: dict):
    db = get_db()
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {"$set": updates},
        upsert=True,
    )
