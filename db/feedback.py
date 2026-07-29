"""Database operations for the feedback feature."""

from datetime import datetime, timezone

from .connection import get_db


async def feedback_add_game(
    guild_id: int,
    name: str,
    role_name: str,
    role_id: int,
    thread_id: int,
    anonymous_allowed: bool = False,
) -> dict:
    """Add a game configuration for a guild."""
    db = get_db()

    game_document = {
        "guild_id": guild_id,
        "name": name,
        "role_name": role_name,
        "role_id": role_id,
        "thread_id": thread_id,
        "active": True,
    }

    await db.feedback_games.insert_one(game_document)
    return game_document


async def feedback_remove_game(guild_id: int, name: str) -> bool:
    """Remove a game configuration without deleting its submitted feedback."""
    db = get_db()
    delete_result = await db.feedback_games.delete_one(
        {
            "guild_id": guild_id,
            "name": name,
        }
    )

    return delete_result.deleted_count > 0


async def feedback_get_games(guild_id: int) -> list[dict]:
    """Return all configured games for a guild, sorted by name."""
    db = get_db()
    cursor = db.feedback_games.find({"guild_id": guild_id}).sort("name", 1)
    return await cursor.to_list(length=None)


async def feedback_get_game(guild_id: int, name: str) -> dict | None:
    """Return one configured game by name."""
    db = get_db()
    return await db.feedback_games.find_one(
        {
            "guild_id": guild_id,
            "name": name,
        }
    )


async def feedback_toggle_game_active(guild_id: int, name: str) -> bool:
    """Toggle whether a game accepts feedback."""
    db = get_db()

    game = await feedback_get_game(guild_id, name)
    if not game:
        return False

    update_result = await db.feedback_games.update_one(
        {"guild_id": guild_id, "name": name},
        {"$set": {"active": not game["active"]}},
    )

    return update_result.modified_count > 0


async def feedback_submit(
    guild_id: int,
    game_name: str,
    category: str,
    description: str,
    anonymous: bool,
    sender_id: int,
) -> dict:
    """Store a new feedback entry."""
    db = get_db()

    feedback_document = {
        "guild_id": guild_id,
        "game_name": game_name,
        "category": category,
        "description": description,
        "anonymous": anonymous,
        "sender_id": str(sender_id),
        "sent_at": datetime.now(timezone.utc),
    }

    await db.feedback_entries.insert_one(feedback_document)
    return feedback_document


async def feedback_list(
    guild_id: int,
    game_name: str,
    category: str | None = None,
) -> list[dict]:
    """Return feedback entries for a game, newest first."""
    db = get_db()

    feedback_query = {
        "guild_id": guild_id,
        "game_name": game_name,
    }
    if category:
        feedback_query["category"] = category

    cursor = db.feedback_entries.find(feedback_query).sort("sent_at", -1)
    return await cursor.to_list(length=None)


async def feedback_count(guild_id: int, game_name: str) -> int:
    """Count feedback entries for a game."""
    db = get_db()
    return await db.feedback_entries.count_documents(
        {
            "guild_id": guild_id,
            "game_name": game_name,
        }
    )
