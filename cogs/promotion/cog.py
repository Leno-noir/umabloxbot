from discord import app_commands
from discord.ext import commands


class Promotion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="promotion-ping", description="Temporary command used while scaffolding the promotion cog")
    async def promotion_ping(self, interaction):
        await interaction.response.send_message("Promotion cog is loaded.", ephemeral=True)
