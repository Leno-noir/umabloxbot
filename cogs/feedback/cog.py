import logging

import discord
from discord import app_commands
from discord.ext import commands

from db.feedback import feedback_get_games
from db.guild_configs import (
    guild_get_feedback_anonymous_allowed,
    guild_get_feedback_panel_message,
    guild_set_feedback_panel_message,
)
from .utils import get_active_feedback_games, is_feedback_manager
from .views import (
    FeedbackCategorySelectView,
    FeedbackGameSelectView,
    FeedbackListGameSelectView,
    FeedbackListView,
    FeedbackPanelView,
)

logger = logging.getLogger(__name__)


class Feedback(commands.Cog):
    """Cog for managing feedback submissions and viewing."""

    feedback_group = app_commands.Group(
        name="feedback",
        description="Submit and review game feedback",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot




    async def _send_feedback_flow(
        self,
        interaction: discord.Interaction,
        active_games: list[dict],
    ):
        
        anonymous_allowed = await guild_get_feedback_anonymous_allowed(
            interaction.guild_id
        )
      
        # if there is just one game no need to select which one, go directly to category selection
        if len(active_games) == 1:
            game = active_games[0]
           
            await interaction.followup.send(
                "Select a feedback category:",
                view=FeedbackCategorySelectView(
                    game_name=game["name"],
                    bot=self.bot,
                    anonymous_allowed=anonymous_allowed,
                ),
                ephemeral=True,
            )
            return


        await interaction.followup.send(
            "Choose a game to submit feedback for:",
            view=FeedbackGameSelectView(
                active_games,
                self.bot,
                anonymous_allowed,
            ),
            ephemeral=True,
        )





    @is_feedback_manager()

    @feedback_group.command(
        name="panel",
        description="Create/update a public feedback panel for everyone",
    )
    async def feedback_panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            active_games = await get_active_feedback_games(interaction.guild_id)

            if not active_games:
                await interaction.followup.send(
                    "❌ No games are currently accepting feedback.",
                    ephemeral=True,
                )
                return

            
            view = FeedbackPanelView(active_games, self.bot, interaction.guild_id)
            
            channel_id, message_id = await guild_get_feedback_panel_message(
                interaction.guild_id
            )

            if channel_id and message_id:
                try:
                    channel = interaction.guild.get_channel(channel_id)
                    
                    if channel:
                        message = await channel.fetch_message(message_id)
                       
                        await message.edit(view=view)
                        await interaction.followup.send(
                            f"✅ Feedback panel updated!\n"
                            f"📍 Channel: {channel.mention}",
                            ephemeral=True,
                        )
                        return
                except (discord.NotFound, discord.Forbidden):
                    pass

           
           
            panel_message = await interaction.channel.send(view=view)
            
            await guild_set_feedback_panel_message(
                interaction.guild_id,
                interaction.channel_id,
                panel_message.id,
            )

            await interaction.followup.send(
                "✅ Feedback panel created!",
                ephemeral=True,
            )

        except Exception:
            logger.exception("Error in feedback panel")
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True,
            )





    @feedback_group.command(
        name="send",
        description="Submit feedback for a game",
    )
   
    async def feedback_send(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            active_games = await get_active_feedback_games(interaction.guild_id)

            if not active_games:
                await interaction.followup.send(
                    "❌ No games are currently accepting feedback.",
                    ephemeral=True,
                )
                return

            await self._send_feedback_flow(interaction, active_games)

        except Exception:
            logger.exception("Error in feedback-send")
          
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True,
            )





    @feedback_group.command(
        name="list",
        description="View feedback received for a game",
    )
   
    @is_feedback_manager()
   
    async def feedback_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            all_games = await feedback_get_games(interaction.guild_id)

            if not all_games:
                await interaction.followup.send(
                    "❌ No games configured yet.",
                    ephemeral=True,
                )
                return

          
            if len(all_games) == 1:
                game = all_games[0]
                view = FeedbackListView(self.bot, interaction.guild_id, game["name"])
              
                await view.send(interaction, ephemeral=True)
                return

          
            await interaction.followup.send(
                "Choose a game to view feedback for:",
               
                view=FeedbackListGameSelectView(
                    all_games,
                    self.bot,
                    interaction.guild_id,
                ),
                ephemeral=True,
            )

        except Exception:
            logger.exception("Error in feedback-list")
            await interaction.followup.send(
                "❌ An error occurred. Please try again.",
                ephemeral=True,
            )





    async def refresh_feedback_panel(self, guild_id: int):
        try:
            channel_id, message_id = await guild_get_feedback_panel_message(guild_id)
            if not channel_id or not message_id:
                return

            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

           
            channel = guild.get_channel(channel_id)
            if not channel:
                return

          
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                return

           
            active_games = await get_active_feedback_games(guild_id)
            if not active_games:
                return

          
            view = FeedbackPanelView(active_games, self.bot, guild_id)
            await message.edit(view=view)

        except Exception:
            logger.exception("Error refreshing feedback panel")


async def setup(bot: commands.Bot):
    await bot.add_cog(Feedback(bot))
