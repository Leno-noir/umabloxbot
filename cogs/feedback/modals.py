import logging

import discord
from discord.ext import commands

from db.feedback import feedback_get_game, feedback_submit
from .utils import category_label, feedback_sender_label

logger = logging.getLogger(__name__)

#Modal for submitting feedback
class FeedbackSubmitModal(discord.ui.Modal, title="Submit Feedback"):

    description = discord.ui.TextInput(
        label="Feedback Description",
        placeholder="Describe your feedback in detail...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=10,
        max_length=2000,
    )

    def __init__(
        self,
        game_name: str,
        category: str,
        anonymous: bool,
        bot: commands.Bot,
    ):
        super().__init__()
        self.game_name = game_name
        self.feedback_category = category
        self.send_anonymously = anonymous
        self.bot = bot
        self.title = f"Feedback: {game_name} ({category.capitalize()})"

   
   
    async def on_submit(self, interaction: discord.Interaction):
        from .views import FeedbackNotificationView

        await interaction.response.defer(ephemeral=True)

        try:
            game = await feedback_get_game(interaction.guild_id, self.game_name)

            if not game:
                await interaction.followup.send(
                    f"Game '{self.game_name}' not found.",
                    ephemeral=True,
                )
                return

          
            feedback_description = self.description.value
          
            await feedback_submit(
                guild_id=interaction.guild_id,
                game_name=self.game_name,
                category=self.feedback_category,
                description=feedback_description,
                anonymous=self.send_anonymously,
                sender_id=interaction.user.id,
            )

            sent_at = discord.utils.utcnow()
            notification_view = FeedbackNotificationView(
                game_name=self.game_name,
                category=category_label(self.feedback_category),
                feedback_message=feedback_description,
                sender_name=feedback_sender_label(
                    interaction,
                    self.send_anonymously,
                ),
                sent_at=discord.utils.format_dt(sent_at, style="f"),
            )

           
            feedback_thread = interaction.guild.get_thread(game["thread_id"])
          
            if feedback_thread:
                game_role = interaction.guild.get_role(game["role_id"])
                if game_role:
                    await feedback_thread.send(content=game_role.mention)

                await feedback_thread.send(view=notification_view)

            await interaction.followup.send(
                f"Your feedback for **{self.game_name}** has been submitted!",
                ephemeral=True,
            )

        except Exception:
            logger.exception("Error submitting feedback")
            await interaction.followup.send(
                "An error occurred while submitting your feedback. Please try again.",
                ephemeral=True,
            )
