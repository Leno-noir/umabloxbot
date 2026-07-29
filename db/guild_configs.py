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


async def guild_get_rotector_enabled(guild_id: int) -> bool:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return bool(doc.get("rotector_enabled", False)) if doc else False


async def guild_get_rotector_alert_channel(guild_id: int) -> int | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc.get("rotector_alert_channel") if doc else None


async def guild_toggle_rotector_enabled(guild_id: int) -> bool:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    current_value = bool(doc.get("rotector_enabled", False)) if doc else False
    new_value = not current_value
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {"$set": {"rotector_enabled": new_value}},
        upsert=True,
    )
    return new_value


# retrieves all configured settings for a server
# returns dictionary with all guild settings (empty dict if no config exists)
# used by /settings command to display current configuration
async def guild_get_settings(guild_id: int) -> dict:
    db = get_db()
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


# ============================================================================
# FEEDBACK CONFIGURATION FUNCTIONS
# ============================================================================


# sets the Discord channel where feedback threads are created for a server
# called when user configures via /settings Feedback section
# overwrites previous channel if one was set
async def guild_set_feedback_channel(guild_id: int, channel_id: int):
    db = get_db()
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {"$set": {"feedback_channel": channel_id}},
        upsert=True,
    )


# retrieves the configured feedback channel for a server
# returns channel ID if configured, None if no channel was set
# used by bot to know where to create feedback threads
async def guild_get_feedback_channel(guild_id: int) -> int | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc.get("feedback_channel") if doc else None


# sets the Discord role that can manage feedback (view /feedback-panel and /feedback list)
# called when user configures via /settings Feedback section
# stores both role name and role ID for redundancy
async def guild_set_feedback_manager_role(guild_id: int, role_name: str, role_id: int):
    db = get_db()
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {
            "$set": {
                "feedback_manager_role": role_name,
                "feedback_manager_role_id": role_id,
            }
        },
        upsert=True,
    )


# retrieves the feedback manager role ID for a guild (used for command permissions)
# returns role ID if configured, None otherwise
# used by is_feedback_manager() permission check
async def guild_get_feedback_manager_role_id(guild_id: int) -> int | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc.get("feedback_manager_role_id") if doc else None


# retrieves the feedback manager role name for a guild (used for fallback display)
# returns role name if configured, None otherwise
async def guild_get_feedback_manager_role_name(guild_id: int) -> str | None:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc.get("feedback_manager_role") if doc else None


# toggles whether anonymous feedback submissions are allowed globally for a guild
# when True: users can choose to send feedback anonymously
# when False: all feedback must be attributed to sender
# this setting applies to ALL games in the guild
async def guild_toggle_feedback_anonymous(guild_id: int) -> bool:
    db = get_db()

    # Get current status
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    current_value = doc.get("feedback_anonymous_allowed", False) if doc else False

    # Toggle it
    new_value = not current_value

    # Update
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {"$set": {"feedback_anonymous_allowed": new_value}},
        upsert=True,
    )

    return new_value


# retrieves whether anonymous feedback is allowed for a guild
# returns True if allowed, False otherwise
async def guild_get_feedback_anonymous_allowed(guild_id: int) -> bool:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    return doc.get("feedback_anonymous_allowed", False) if doc else False


# saves the feedback panel message ID for a guild (to update it when games change)
# called when /feedback-panel is used by an admin
# allows automatic updates when games are added/removed
async def guild_set_feedback_panel_message(
    guild_id: int, channel_id: int, message_id: int
):
    db = get_db()
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {
            "$set": {
                "feedback_panel_channel_id": channel_id,
                "feedback_panel_message_id": message_id,
            }
        },
        upsert=True,
    )


# retrieves the feedback panel message ID for a guild (for updating)
# returns tuple of (channel_id, message_id) if set, (None, None) otherwise
async def guild_get_feedback_panel_message(
    guild_id: int,
) -> tuple[int | None, int | None]:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    if not doc:
        return None, None

    channel_id = doc.get("feedback_panel_channel_id")
    message_id = doc.get("feedback_panel_message_id")
    return channel_id, message_id


async def guild_set_blacklist_panel_message(
    guild_id: int, channel_id: int, message_id: int
):
    db = get_db()
    await db.guild_configs.update_one(
        {"guild_id": guild_id},
        {
            "$set": {
                "blacklist_panel_channel_id": channel_id,
                "blacklist_panel_message_id": message_id,
            }
        },
        upsert=True,
    )


async def guild_get_blacklist_panel_message(
    guild_id: int,
) -> tuple[int | None, int | None]:
    db = get_db()
    doc = await db.guild_configs.find_one({"guild_id": guild_id})
    if not doc:
        return None, None

    channel_id = doc.get("blacklist_panel_channel_id")
    message_id = doc.get("blacklist_panel_message_id")
    return channel_id, message_id
