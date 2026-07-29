"""Guild-aware slash command sync helpers with command categorization and permission management."""

import logging

import discord

from db.allowed_guilds import allowed_guild_list_enabled
from .command_definitions import get_commands_for_guild_type

logger = logging.getLogger(__name__)


def add_commands_for_guild_type(bot, guild_object, guild_type: str):
    for command_name in get_commands_for_guild_type(guild_type):
        command = bot.tree.get_command(command_name)
        if command:
            bot.tree.add_command(command, guild=guild_object, override=True)


async def sync_network_commands(
    bot,
    main_guild_id: int,
    *,
    clear_global_commands: bool = False,
):
    """Synchronize guild-scoped commands without rewriting them on reconnects.

    ``clear_global_commands`` exists only for an explicit maintenance run when
    migrating from an old global-command deployment; startup never enables it.
    """

    report: dict[str, int] = {}
    main_guild = discord.Object(id=main_guild_id)
    if clear_global_commands:
        legacy_global_commands = await bot.tree.fetch_commands()
        local_commands = list(bot.tree.get_commands())
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        # Clearing global commands also clears the local source commands that
        # are copied into each guild. Restore them locally without syncing
        # globally, then rebuild the guild-scoped command sets below.
        for command in local_commands:
            bot.tree.add_command(command, override=True)
        report["global_removed"] = len(legacy_global_commands)
        logger.info("Removed %s legacy global commands", report["global_removed"])

    # === MAIN GUILD: Full command set with manager-only restrictions ===
    bot.tree.clear_commands(guild=main_guild)
    add_commands_for_guild_type(bot, main_guild, "main")
    main_synced = await bot.tree.sync(guild=main_guild)
    report["main"] = len(main_synced)
    logger.info("Main guild commands synced: %s", len(main_synced))

    # Manager-only commands are protected at runtime by the `@is_manager()` decorator.

    # === OBSERVER GUILDS: Sync the guild-type feature set ===
    enabled_observer_records = await allowed_guild_list_enabled()
    enabled_observer_ids = {record["guild_id"] for record in enabled_observer_records}

    for guild in bot.guilds:
        if guild.id == main_guild_id:
            continue

        guild_object = discord.Object(id=guild.id)
        bot.tree.clear_commands(guild=guild_object)

        if guild.id in enabled_observer_ids:
            add_commands_for_guild_type(bot, guild_object, "observer")
            synced = await bot.tree.sync(guild=guild_object)
            report[f"observer:{guild.id}"] = len(synced)
            logger.info("Observer commands synced for %s: %s", guild.name, len(synced))
        else:
            add_commands_for_guild_type(bot, guild_object, "unknown")
            synced = await bot.tree.sync(guild=guild_object)
            report[f"unknown:{guild.id}"] = len(synced)
            logger.info("Funsies commands synced for %s: %s", guild.name, len(synced))

    return report
