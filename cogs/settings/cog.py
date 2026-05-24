import discord
from discord import app_commands
from discord.ext import commands

from core import MAIN_GUILD_ID, get_guild_type
from .observer_views import ObserverSettingsView
from .views import MainSettingsHomeView


#settings cog used as the entry point for guild-specific configuration panels
class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #routes /settings to the correct panel depending on the guild type
    @app_commands.command(name="settings", description="View and edit bot settings for this server")
    @app_commands.default_permissions(administrator=True)
    async def settings(self, interaction: discord.Interaction):
        guild_type = await get_guild_type(interaction.guild_id, MAIN_GUILD_ID)

        #main guild gets the full administration panel
        if guild_type == "main":
            view = MainSettingsHomeView(interaction.guild_id)
            await view.send(interaction)
            return

        #allowed observer guilds get a reduced local settings panel
        if guild_type == "observer":
            view = ObserverSettingsView(interaction.guild_id)
            await view.send(interaction)
            return

        #all other guilds are blocked from network settings
        await interaction.response.send_message(
            "This server is not allowed to use the bot network settings.",
            ephemeral=True,
        )


#function called when the cog is loaded by the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
