import logging

import discord
from discord import app_commands
from discord.ext import commands

from core import MAIN_GUILD_ID, format_discord_id, timestamp_to_discord
from db.guild_configs import guild_get_blacklist_logs_channel, guild_get_settings

logger = logging.getLogger(__name__)


async def send_ephemeral_message(
    interaction: discord.Interaction,
    message: str,
):
   
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
  
    else:
        await interaction.response.send_message(message, ephemeral=True)





## Restricts commands to the main guild
def is_main_guild_only():

    async def check_main_guild(interaction: discord.Interaction) -> bool:
        if interaction.guild_id == MAIN_GUILD_ID:
            return True

        await send_ephemeral_message(
            interaction,
            "Blacklist commands can only be used in Uma Portal.",
        )
       
        return False

    return app_commands.check(check_main_guild)





## Restricts commands to moderators or a configured custom role
def is_manager():

    async def authorize_blacklist_commands(interaction: discord.Interaction) -> bool:
        if interaction.permissions and interaction.permissions.ban_members:
            return True


        member = (
            interaction.user
            if isinstance(interaction.user, discord.Member)
            else None
        )  
        if member is None and interaction.guild is not None:
            member = interaction.guild.get_member(interaction.user.id)



        manager_role_name = await get_blacklist_manager_role_name()
        if manager_role_name and member is not None:
            if any(role.name == manager_role_name for role in member.roles):
                return True



        await send_ephemeral_message(
            interaction,
            "You do not have permission to use this command.",
        )
       
        return False

    return app_commands.check(authorize_blacklist_commands)






async def get_blacklist_manager_role_name() -> str | None:
    settings = await guild_get_settings(MAIN_GUILD_ID)
    
    return settings.get("blacklist_manager_role")






async def send_blacklist_log_broadcast(bot: commands.Bot, view: discord.ui.LayoutView):
    channel_id = await guild_get_blacklist_logs_channel(MAIN_GUILD_ID)
    if not channel_id:
        return

   
    channel = bot.get_channel(channel_id)
    if channel:
        try:
            await channel.send(view=view)
        except discord.Forbidden:
            logger.warning("Missing permission to send in blacklist log channel %s", channel_id)






async def send_blacklist_action_notification(
    bot: commands.Bot,
    interaction: discord.Interaction,
    view: discord.ui.LayoutView,
    user_label: str,
    action: str,
):
    
    await send_blacklist_log_broadcast(bot, view)

    messages = {
        "added": f"{user_label} has been added to the blacklist. Uma Portal has been notified.",
        "removed": f"{user_label} has been removed from the blacklist.",
    }

    await interaction.followup.send(messages[action], ephemeral=True)






async def refresh_blacklist_panel(bot: commands.Bot, guild_id: int | None):
    if guild_id is None:
        return

    blacklist_cog = bot.get_cog("Blacklist")
    if blacklist_cog is not None:
        await blacklist_cog.refresh_blacklist_panel(guild_id)






def blacklist_status_text(is_active: bool) -> str:
    return "CURRENTLY BANNED" if is_active else "NOT BANNED"






def format_event_log_record(record: dict) -> str:
    timestamp = timestamp_to_discord(record["at"])
    user_tag = f"<@{record['discord_id']}> | {record['discord_id']}"

    if record["type"] == "ban":
        return (
            f"**BANNED <t:{timestamp}:d>**\n"
            f"{user_tag}\n"
            f"Reason: {record['reason']}\n"
            f"By: {record['by']}"
        )

    return (
        f"**UNBANNED <t:{timestamp}:d>**\n"
        f"{user_tag}\n"
        f"Original ban reason: {record['original_reason']}\n"
        f"Remove reason: {record['reason']}\n"
        f"By: {record['by']}"
    )






def format_history_entry(entry: dict, index: int) -> str:
    added_timestamp = timestamp_to_discord(entry["added_at"])
    entry_text = (
        f"**BAN #{index} <t:{added_timestamp}:d>**\n"
        f"Reason: {entry['reason']}\n"
        f"By: {entry['added_by']}"
    )

    if entry.get("evidence"):
        entry_text += f"\nEvidence: {entry['evidence']}"

    if entry.get("removed_at"):
        removed_timestamp = timestamp_to_discord(entry["removed_at"])
        entry_text += (
            f"\n\n**UNBAN #{index} <t:{removed_timestamp}:d>**\n"
            f"Removed by: {entry['removed_by']}\n"
            f"Remove reason: {entry['remove_reason']}"
        )

    return entry_text






def get_active_blacklist_entry(doc: dict) -> dict | None:
    if not doc or not doc.get("active"):
        return None

    return {
        "reason": doc["current_reason"],
        "evidence": doc.get("current_evidence"),
        "added_by": doc["current_added_by"],
        "added_at": doc["current_added_at"],
        "roblox_user": doc["roblox_user"],
        "roblox_id": doc["roblox_id"],
    }






def get_past_blacklist_entries(doc: dict) -> list:
    history = doc.get("history", []) if doc else []
   
    return [record for record in history if record.get("removed_at") is not None]






def validate_discord_id():
    """Decorator to validate and normalize Discord ID from command input."""

    def decorator(func):
        async def wrapper(self, interaction: discord.Interaction, discord_id: str):
            formatted_discord_id = format_discord_id(discord_id)

            if not formatted_discord_id:
                await send_ephemeral_message(
                    interaction,
                    "Provide a valid Discord ID.",
                )
                return

            return await func(self, interaction, formatted_discord_id)

        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        return wrapper

    return decorator
