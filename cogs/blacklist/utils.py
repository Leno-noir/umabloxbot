import discord
from discord import app_commands
from discord.ext import commands

from core import MAIN_GUILD_ID, format_discord_id
from db.guild_configs import guild_get_blacklist_logs_channel

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

        #TODO: fetch custom blacklist role from database configuration if available
        #for now, only Ban Members permission is checked

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