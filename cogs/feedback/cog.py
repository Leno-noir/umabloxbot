from discord import app_commands
from discord.ext import commands


class Feedback(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="feedback-ping", description="Temporary command used while scaffolding the feedback cog")
    async def feedback_ping(self, interaction):
        await interaction.response.send_message("Feedback cog is loaded.", ephemeral=True)
