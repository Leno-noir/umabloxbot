# Core module containing configuration and utilities
from .config import (
    Colors,
    DISCORD_TOKEN,
    MONGODB_URI,
    MAIN_GUILD_ID,
    validate_runtime_config,
)
from .command_definitions import COMMAND_GROUPS, GUILD_TYPE_COMMANDS, get_commands_for_guild_type, get_manager_only_commands
from .application_commands import application_command
from .utils import (
    format_discord_id, timestamp_to_discord, pagination_text,
    get_user_by_discord_id, format_guild_id, is_main_guild, get_guild_type,
)


async def sync_network_commands(
    bot,
    main_guild_id: int,
):
    from .command_sync import sync_network_commands as _sync_network_commands

    return await _sync_network_commands(bot, main_guild_id)

__all__ = [
    "Colors",
    "DISCORD_TOKEN",
    "MONGODB_URI",
    "MAIN_GUILD_ID",
    "validate_runtime_config",
    "sync_network_commands",
    "COMMAND_GROUPS",
    "GUILD_TYPE_COMMANDS",
    "get_commands_for_guild_type",
    "get_manager_only_commands",
    "application_command",
    "format_discord_id",
    "timestamp_to_discord",
    "pagination_text",
    "get_user_by_discord_id",
    "format_guild_id",
    "is_main_guild",
    "get_guild_type",
]
