import discord
from discord import app_commands
from discord.ext import commands

from core import Colors, MAIN_GUILD_ID, format_discord_id, pagination_text, timestamp_to_discord
from db.guild_configs import guild_get_blacklist_logs_channel, guild_get_settings

#ensures blacklist commands can only be used inside the main guild
def is_main_guild_only():
    """Restrict blacklist commands to the configured main guild."""

    async def check_main_guild(interaction: discord.Interaction) -> bool:
        if interaction.guild_id == MAIN_GUILD_ID:
            return True

        if interaction.response.is_done():
            await interaction.followup.send(
                "Blacklist commands can only be used in Uma Portal.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Blacklist commands can only be used in Uma Portal.",
                ephemeral=True,
            )
        return False

    return app_commands.check(check_main_guild)


#functions to set restricted acess for some blacklist commands
#it sets an verification when using certain commands
def is_manager():
    """Allow restricted blacklist commands for moderators or a configured custom role."""

    async def authorize_blacklist_commands(interaction: discord.Interaction) -> bool:
        # Moderators (users with ban permissions) can always use the commands
        if interaction.permissions and interaction.permissions.ban_members:
            return True

        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None and interaction.guild is not None:
            member = interaction.guild.get_member(interaction.user.id)

        #main guild can also authorize by a custom configured blacklist manager role
        manager_role_name = await get_blacklist_manager_role_name()
        if manager_role_name and member is not None:
            if any(role.name == manager_role_name for role in member.roles):
                return True

        #error message if nothing above returned true
        if interaction.response.is_done():
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True,
            )
        return False

    return app_commands.check(authorize_blacklist_commands)


#fetches the configured blacklist manager role from the main guild settings
async def get_blacklist_manager_role_name() -> str | None:
    """Return the blacklist manager role name configured in main guild settings."""
    settings = await guild_get_settings(MAIN_GUILD_ID)
    return settings.get("blacklist_manager_role")

#sends a embed message to the configured log channel with the information of the action that was done in the blacklist (add/remove)
async def send_blacklist_log_broadcast(bot: commands.Bot, embed: discord.Embed):
    """Send a notification embed to the Uma Portal log channel only."""
    #fetch log channel from database configuration
    channel_id = await guild_get_blacklist_logs_channel(MAIN_GUILD_ID)
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if channel:
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permission to send in log channel {channel_id}")

#sends a notification for the user that submitted the action and also to the log channel, with a embed containing the information of the action that was done in the blacklist (add/remove)
async def send_blacklist_action_notification(
    bot: commands.Bot,
    interaction: discord.Interaction,
    embed: discord.Embed,
    user_label: str,
    action: str,  # "added" or "removed"
):
    """Send blacklist action to log channel and notify user."""
    await send_blacklist_log_broadcast(bot, embed)
    
    messages = {
        "added": f"{user_label} has been added to the blacklist. Uma Portal has been notified.",
        "removed": f"{user_label} has been removed from the blacklist.",
    }
    
    await interaction.followup.send(messages[action], ephemeral=True)


#builds the embed sent when a user is added to the blacklist
def build_blacklist_added_embed(
    discord_user_label: str,
    roblox_user: str,
    roblox_id: str,
    reason: str,
    added_by: str,
    timestamp,
    guild_name: str,
    evidence: str | None = None,
) -> discord.Embed:
    """Build the add notification embed."""
    embed = discord.Embed(
        title="User added to blacklist",
        color=Colors.RED,
        timestamp=timestamp,
    )
    embed.add_field(name="Discord user", value=discord_user_label, inline=False)
    embed.add_field(name="Roblox", value=f"{roblox_user} (`{roblox_id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    if evidence:
        embed.add_field(name="Evidence", value=evidence, inline=False)
    embed.add_field(name="Added by", value=added_by, inline=False)
    embed.set_footer(text=f"Server: {guild_name}")
    return embed


#builds the embed sent when a user is removed from the blacklist
def build_blacklist_removed_embed(
    discord_user_label: str,
    reason: str,
    removed_by: str,
    guild_name: str,
) -> discord.Embed:
    """Build the removal notification embed."""
    embed = discord.Embed(
        title="User removed from blacklist",
        color=Colors.GREEN,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Discord user", value=discord_user_label, inline=False)
    embed.add_field(name="Reason for removal", value=reason, inline=False)
    embed.add_field(name="Removed by", value=removed_by, inline=False)
    embed.set_footer(text=f"Server: {guild_name}")
    return embed


#builds the observer join alert embed for blacklisted users
def build_blacklist_join_alert_embed(member: discord.Member, record: dict) -> discord.Embed:
    """Build the observer join alert embed."""
    embed = discord.Embed(
        title="Blacklisted user joined a server",
        description=f"{member.mention} (`{member.id}`) is on the blacklist.",
        color=Colors.YELLOW,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Roblox", value=f"{record.get('roblox_user', '?')} (`{record['roblox_id']}`)", inline=False)
    embed.add_field(name="Reason", value=record["reason"], inline=False)
    embed.add_field(name="Server", value=member.guild.name, inline=False)
    return embed


#builds the embed used by /blacklist-info
def build_blacklist_info_embed(discord_id: str, discord_user_label: str, history: list[dict]) -> tuple[discord.Embed, str | None]:
    """Build the blacklist info embed and return the related Roblox ID."""
    active = get_active_blacklist_entry(history)
    embed = discord.Embed(
        title=f"Blacklist info - {discord_user_label}",
        description="CURRENTLY BANNED" if active else "No active ban",
        color=Colors.RED if active else Colors.GRAY,
    )

    if active:
        added_ts = timestamp_to_discord(active["added_at"])
        embed.add_field(name="Discord ID", value=discord_id, inline=False)
        embed.add_field(name="Roblox", value=f"{active['roblox_user']} (`{active['roblox_id']}`)", inline=False)
        embed.add_field(name="Reason", value=active["reason"], inline=False)
        if active.get("evidence"):
            embed.add_field(name="Evidence", value=active["evidence"], inline=False)
        embed.add_field(name="Added by", value=active["added_by"], inline=False)
        embed.add_field(name="Date", value=f"<t:{added_ts}:F>", inline=False)

    past = get_past_blacklist_entries(history)
    if past:
        lines = [
            f"- <t:{timestamp_to_discord(record['added_at'])}:d> - {record['reason']} (removed by {record.get('removed_by', '?')})"
            for record in past[:5]
        ]
        embed.add_field(name=f"Past entries ({len(past)})", value="\n".join(lines), inline=False)

    roblox_id = active["roblox_id"] if active else history[0].get("roblox_id")
    return embed, roblox_id


#builds the embed used by /blacklist-history
def build_blacklist_history_embed(discord_id: str, discord_user_label: str, history: list[dict]) -> discord.Embed:
    """Build the full blacklist history embed."""
    embed = discord.Embed(
        title=f"Blacklist history - {discord_user_label}",
        description=f"{len(history)} event(s) on record",
        color=Colors.BLUE,
    )

    for record in history:
        added_ts = timestamp_to_discord(record["added_at"])
        if record["active"]:
            lines = [
                f"**Discord ID:** {discord_id}",
                f"**Reason:** {record['reason']}",
                f"**Roblox:** {record.get('roblox_user', '?')} (`{record['roblox_id']}`)",
                f"**Added by:** {record['added_by']}",
            ]
            if record.get("evidence"):
                lines.insert(3, f"**Evidence:** {record['evidence']}")
            embed.add_field(name=f"Banned - <t:{added_ts}:d>", value="\n".join(lines), inline=False)
        else:
            removed_ts = timestamp_to_discord(record["removed_at"]) if record.get("removed_at") else None
            lines = [
                f"**Discord ID:** {discord_id}",
                f"**Ban reason:** {record['reason']}",
            ]
            if removed_ts:
                lines += [
                    f"**Removed by:** {record.get('removed_by', '?')} on <t:{removed_ts}:d>",
                    f"**Removal reason:** {record.get('remove_reason', '?')}",
                ]
            embed.add_field(name=f"Unbanned - added <t:{added_ts}:d>", value="\n".join(lines), inline=False)

    return embed


#builds the embed used by /blacklist-list
def build_blacklist_list_embed(page: int, records: list[dict], total: int) -> discord.Embed:
    """Build the paginated blacklist list embed."""
    embed = discord.Embed(
        title=f"Blacklist - Page {page}",
        description=f"**{total}** banned user(s) in total",
        color=Colors.RED,
    )
    for record in records:
        added_ts = timestamp_to_discord(record["added_at"])
        embed.add_field(
            name=f"{record.get('roblox_user', '?')} | <@{record['discord_id']}>",
            value=f"Reason: {record['reason']}\nAdded: <t:{added_ts}:d> by {record['added_by']}",
            inline=False,
        )
    embed.set_footer(text=pagination_text(page, total))
    return embed


#builds the embed used by /blacklist-log
def build_blacklist_log_embed(page: int, records: list[dict], total: int) -> discord.Embed:
    """Build the paginated blacklist event log embed."""
    embed = discord.Embed(
        title=f"Blacklist event log - Page {page}",
        description=f"**{total}** event(s) in total",
        color=Colors.BLUE,
    )
    for record in records:
        added_ts = timestamp_to_discord(record["added_at"])
        user_tag = f"<@{record['discord_id']}> ({record.get('roblox_user', '?')})"
        if record["active"]:
            embed.add_field(
                name=f"Banned <t:{added_ts}:d>",
                value=f"{user_tag}\n**Reason:** {record['reason']}\n**By:** {record['added_by']}",
                inline=False,
            )
        else:
            removed_ts = timestamp_to_discord(record["removed_at"]) if record.get("removed_at") else None
            removed_line = f"\n**Removed:** <t:{removed_ts}:d> by {record.get('removed_by', '?')}" if removed_ts else ""
            embed.add_field(
                name=f"Unbanned (banned <t:{added_ts}:d>)",
                value=f"{user_tag}\n**Ban reason:** {record['reason']}{removed_line}",
                inline=False,
            )
    embed.set_footer(text=pagination_text(page, total))
    return embed
    
#gets a blacklist entry from the database and checks if its active, 
# if it is, it returns the entry, if not, it returns None
def get_active_blacklist_entry(history: list) -> dict | None:
    """Get the currently active blacklist entry from history."""
    for record in history:
        if record["active"]:
            return record
    return None


#gets blacklist entry for the past entries of a user
def get_past_blacklist_entries(history: list) -> list:
    """Get all inactive (past) blacklist entries from history."""
    return [record for record in history if not record["active"]]


#decorator to validate and normalize discord id from command input
def validate_discord_id():
    """Decorator to validate and normalize Discord ID from command input."""
    def decorator(func):
        async def wrapper(self, interaction: discord.Interaction, discord_id: str):
            
            #format and validate the discord_id (extracts digits, removes invalid characters)
            formated_discord_id = format_discord_id(discord_id)
            
            #if the discord_id is invalid, send error message and stop execution
            if not formated_discord_id:
                await interaction.response.send_message("Provide a valid Discord ID.", ephemeral=True)
                return
            
            #if valid, call the original command function with the formatted discord_id
            return await func(self, interaction, formated_discord_id)
        
        #preserve the original function's name and qualname for discord.py parameter detection
        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        return wrapper
    return decorator
