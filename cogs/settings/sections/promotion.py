import discord

from .base import ChannelSelectView, Section, SettingModal


class PromotionSection(Section):
    label = "Promotion"
    emoji = "Promotion"
    db_keys = ["promo_channel", "rotation_hours"]

    @staticmethod
    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        promo_ch = settings.get("promo_channel")
        interval = settings.get("rotation_hours", 24)
        return [
            ("Promo channel", f"<#{promo_ch}>" if promo_ch else "Not set"),
            ("Rotation interval", f"{interval}h"),
        ]

    @staticmethod
    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        ch_btn = discord.ui.Button(label="Set promo channel", style=discord.ButtonStyle.secondary, row=2)
        int_btn = discord.ui.Button(label="Set rotation interval", style=discord.ButtonStyle.secondary, row=2)

        async def set_channel(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Choose the promotion channel:",
                view=ChannelSelectView("Set promo channel", "promo_channel", guild_id, parent_view),
                ephemeral=True,
            )

        async def set_interval(interaction: discord.Interaction):
            await interaction.response.send_modal(
                SettingModal(
                    title="Set rotation interval",
                    label="Hours between rotations",
                    placeholder="e.g. 24",
                    key="rotation_hours",
                    guild_id=guild_id,
                    parent_view=parent_view,
                )
            )

        ch_btn.callback = set_channel
        int_btn.callback = set_interval
        return [ch_btn, int_btn]
