import discord

from .base import ChannelSelectView, RoleSelectView, Section


class BlacklistSection(Section):
    label = "Blacklist"
    emoji = "Blacklist"
    db_keys = ["blacklist_logs_channel", "blacklist_manager_role", "blacklist_manager_role_id"]

    @staticmethod
    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        log_ch = settings.get("blacklist_logs_channel")
        bl_role = settings.get("blacklist_manager_role", "Not set")
        return [
            ("Blacklist logs channel", f"<#{log_ch}>" if log_ch else "Not set"),
            ("Blacklist manager role", bl_role),
        ]

    @staticmethod
    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        log_btn = discord.ui.Button(label="Set log channel", style=discord.ButtonStyle.secondary, row=1)
        role_btn = discord.ui.Button(label="Set blacklist role", style=discord.ButtonStyle.secondary, row=1)

        async def set_log(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Choose the blacklist log channel:",
                view=ChannelSelectView("Set log channel", "blacklist_logs_channel", guild_id, parent_view),
                ephemeral=True,
            )

        async def set_role(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Choose the blacklist manager role:",
                view=RoleSelectView("Set blacklist manager role", "blacklist_manager_role", guild_id, parent_view),
                ephemeral=True,
            )

        log_btn.callback = set_log
        role_btn.callback = set_role
        return [log_btn, role_btn]
