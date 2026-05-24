import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from core import DISCORD_TOKEN, MAIN_GUILD_ID, sync_network_commands
from db import allowed_guild_is_enabled
from db.blacklist import bl_get
from db.connection import connect
from db.guild_configs import (
    guild_get_blacklisted_users_join_alert_channel,
)
from cogs.blacklist.utils import build_blacklist_join_alert_embed

#configure bot intents (permissions for reading guild events)
intents = discord.Intents.default()
intents.members = True

#create the bot instance with command prefix and configured intents
bot = commands.Bot(command_prefix="!", intents=intents)

#list of all cogs (modules) to load on startup
COGS = [
    "cogs.blacklist",
    "cogs.settings",
    "cogs.feedback",
    "cogs.promotion",
    "cogs.networking",
    "cogs.funsies",
]

#expose sync helper so settings views can refresh command visibility after allowlist changes
bot.sync_network_commands = lambda: sync_network_commands(bot, MAIN_GUILD_ID)

#event triggered when the bot successfully connects and is ready
@bot.event
async def on_ready():
    #print bot connection info
    print(f"Bot online as: {bot.user} (ID: {bot.user.id})")
    print(f"Connected servers: {len(bot.guilds)}")

    #list all registered slash commands
    for cmd in bot.tree.get_commands():
        print(f"[tree] {cmd.name}")

    #list all servers the bot is in
    for guild in bot.guilds:
        print(f"- {guild.name} ({guild.id})")

    #sync slash commands according to guild type
    try:
        await bot.sync_network_commands()
    except Exception as exc:
        print(f"Error syncing commands: {exc}")




#event triggered when a user joins any server the bot is in
@bot.event
async def on_member_join(member: discord.Member):
    """Send join alerts only for enabled observer guilds with a local alert channel."""

    #the main guild does not need observer join alerts
    if member.guild.id == MAIN_GUILD_ID:
        return

    #ignore servers that are not enabled observer guilds
    if not await allowed_guild_is_enabled(member.guild.id):
        return

    #check if the user is on the blacklist
    record = await bl_get(str(member.id))
    if not record:
        return

    #get the local observer alert channel for this guild
    channel_id = await guild_get_blacklisted_users_join_alert_channel(member.guild.id)
    if not channel_id:
        return

    #fetch the configured channel from the observer guild
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    #create embed with blacklist join alert
    embed = build_blacklist_join_alert_embed(member, record)

    #send the alert to the local observer alert channel
    await channel.send(embed=embed)




#global error handler for all slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    #log the error to console
    print(f"App command error: {type(error).__name__}: {error}")

    #handle permission check failures (from @is_manager decorator)
    if isinstance(error, app_commands.CheckFailure):
        if interaction.response.is_done():
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True,
            )
        return

    #handle other command errors with generic error message
    if interaction.response.is_done():
        await interaction.followup.send(
            "Something went wrong while running this command.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "Something went wrong while running this command.",
            ephemeral=True,
        )



#main async function that initializes and starts the bot
async def main():
    async with bot:
        #connect to the database
        await connect()
        
        
        #load all cogs
        for extension in COGS:
            try:
                await bot.load_extension(extension)
                print(f"Loaded extension: {extension}")
            except Exception as exc:
                print(f"Failed to load extension {extension}: {exc}")
                raise
            
            
        #start the bot with the token from config 
        await bot.start(DISCORD_TOKEN)


#entry point for the script
if __name__ == "__main__":
    asyncio.run(main())
