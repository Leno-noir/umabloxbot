from discord import app_commands
from discord.ext import commands


class Funsies(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="funsies-ping", description="Temporary command used while scaffolding the funsies cog")
    async def funsies_ping(self, interaction):
        await interaction.response.send_message("Funsies cog is loaded.", ephemeral=True)
