"""Guild-aware slash command sync helpers with command categorization and permission management."""

import discord

from db import allowed_guild_list_enabled


async def sync_network_commands(bot, main_guild_id: int):
    # Sync commands by guild type with role-based visibility.

    main_guild = discord.Object(id=main_guild_id)
    global_commands = list(bot.tree.get_commands())

    # Clear global commands from Discord before rebuilding guild-specific visibility (just for testing)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()

    # Restore commands locally so they can be copied into guild-specific trees
    for command in global_commands:
        bot.tree.add_command(command, override=True)

    # === MAIN GUILD: Full command set with manager-only restrictions ===
    bot.tree.clear_commands(guild=main_guild)
    bot.tree.copy_global_to(guild=main_guild)
    main_synced = await bot.tree.sync(guild=main_guild)
    print(f"Main guild commands synced: {len(main_synced)}")

    # Manager-only commands are protected at runtime by the `@is_manager()` decorator.

    # === OBSERVER GUILDS: Only /settings command ===
    enabled_observer_records = await allowed_guild_list_enabled()
    enabled_observer_ids = {record["guild_id"] for record in enabled_observer_records}

    for guild in bot.guilds:
        if guild.id == main_guild_id:
            continue

        guild_object = discord.Object(id=guild.id)
        bot.tree.clear_commands(guild=guild_object)

        if guild.id in enabled_observer_ids:
            # Observer guilds get only /settings
            settings_command = bot.tree.get_command("settings")
            if settings_command:
                bot.tree.add_command(settings_command, guild=guild_object, override=True)
            synced = await bot.tree.sync(guild=guild_object)
            print(f"Observer commands synced for {guild.name}: {len(synced)}")
        else:
            synced = await bot.tree.sync(guild=guild_object)
            print(f"Cleared guild commands for {guild.name}: {len(synced)}")
