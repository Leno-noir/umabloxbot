import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from core import Colors, DISCORD_TOKEN, MAIN_GUILD_ID
from db.blacklist import bl_get
from db.connection import connect
from db.guild_configs import guild_get_blacklist_logs_channel

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

    #sync slash commands to the main guild
    try:
        guild = discord.Object(id=MAIN_GUILD_ID)
        
        #clear all old commands to force a clean resync
        bot.tree.clear_commands(guild=guild)
        
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Slash commands synced: {len(synced)}")
    except Exception as exc:
        print(f"Error syncing commands: {exc}")




#event triggered when a user joins any server the bot is in
@bot.event
async def on_member_join(member: discord.Member):
    """Alert the log channel if a blacklisted user joins any server."""
    
    #check if the user is on the blacklist
    record = await bl_get(str(member.id))
    if not record:
        return

    
    #get the log channel to send alerts (from database configuration)
    channel_id = await guild_get_blacklist_logs_channel(MAIN_GUILD_ID)
    if not channel_id:
        return

    
    #fetch the channel object
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    #create embed with blacklist join alert
    embed = discord.Embed(
        title="Blacklisted user joined a server",
        description=f"{member.mention} (`{member.id}`) is on the blacklist.",
        color=Colors.YELLOW,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Roblox", value=f"{record.get('roblox_user', '?')} (`{record['roblox_id']}`)", inline=False)
    embed.add_field(name="Reason", value=record["reason"], inline=False)
    embed.add_field(name="Server", value=member.guild.name, inline=False)

    #send the alert to the log channel
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
