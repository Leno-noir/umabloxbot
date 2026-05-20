import discord

from .base import ChannelSelectView, Section


class NetworkingSection(Section):
    label = "Networking"
    emoji = "Networking"
    db_keys = ["networking_channel"]

    @staticmethod
    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        ch = settings.get("networking_channel")
        return [("Networking channel", f"<#{ch}>" if ch else "Not set")]

    @staticmethod
    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        btn = discord.ui.Button(label="Set networking channel", style=discord.ButtonStyle.secondary, row=4)

        async def set_channel(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Choose the networking channel:",
                view=ChannelSelectView("Set networking channel", "networking_channel", guild_id, parent_view),
                ephemeral=True,
            )

        btn.callback = set_channel
        return [btn]
