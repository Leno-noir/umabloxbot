import discord
from discord import app_commands
from discord.ext import commands

from .views import SettingsView

#settings cog for managing bot configuration per server
class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    #command to access server settings panel
    @app_commands.command(name="settings", description="View and edit bot settings for this server")
    @app_commands.default_permissions(administrator=True)  #only admins can use this command
    async def settings(self, interaction: discord.Interaction):
        
        #create the settings view (UI panel with configuration options)
        view = SettingsView(interaction.guild_id)
        
        #send the settings panel to the user
        await view.send(interaction)



#function called when the cog is loaded by the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))