"""Safe, idempotent indexes required by the production data model."""

from .connection import get_db


async def ensure_core_indexes() -> None:
    """Create query and integrity indexes without modifying existing documents."""
    db = get_db()

    await db.blacklist.create_index("discord_id", unique=True, name="unique_discord_id")
    await db.guild_configs.create_index("guild_id", unique=True, name="unique_guild_config")
    await db.allowed_guilds.create_index("guild_id", unique=True, name="unique_allowed_guild")
    await db.allowed_guilds.create_index([("enabled", 1), ("server_type", 1), ("guild_name", 1)])

    await db.feedback_games.create_index(
        [("guild_id", 1), ("name", 1)],
        unique=True,
        name="unique_feedback_game_per_guild",
    )
    await db.feedback_entries.create_index(
        [("guild_id", 1), ("game_name", 1), ("sent_at", -1)],
        name="feedback_entries_by_game",
    )

    await db.networking_posts.create_index(
        [("guild_id", 1), ("post_type", 1), ("status", 1), ("created_at", -1)],
        name="networking_posts_listing",
    )
    await db.networking_posts.create_index(
        [("guild_id", 1), ("author_id", 1), ("post_type", 1), ("status", 1)],
        name="networking_posts_by_author",
    )
