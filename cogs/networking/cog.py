from discord import app_commands
from discord.ext import commands


class Networking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="networking-ping", description="Temporary command used while scaffolding the networking cog")
    async def networking_ping(self, interaction):
        await interaction.response.send_message("Networking cog is loaded.", ephemeral=True)
