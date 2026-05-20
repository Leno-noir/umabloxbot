import discord

from .base import ChannelSelectView, Section


class FeedbackSection(Section):
    label = "Feedback"
    emoji = "Feedback"
    db_keys = ["feedback_channel"]

    @staticmethod
    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        ch = settings.get("feedback_channel")
        return [("Feedback channel", f"<#{ch}>" if ch else "Not set")]

    @staticmethod
    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        btn = discord.ui.Button(label="Set feedback channel", style=discord.ButtonStyle.secondary, row=3)

        async def set_channel(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Choose the feedback channel:",
                view=ChannelSelectView("Set feedback channel", "feedback_channel", guild_id, parent_view),
                ephemeral=True,
            )

        btn.callback = set_channel
        return [btn]
