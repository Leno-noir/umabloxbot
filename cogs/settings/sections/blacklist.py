import discord

from core.ui import UmaLayoutView
from db.guild_configs import guild_get_settings

from .base import AdminSettingsLayoutView, ChannelSelectView, RoleSelectView, Section


class BlacklistSettingsPanel(AdminSettingsLayoutView):
    """Detailed settings panel for blacklist configuration."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    def _format_channel(self, channel_id: int | None) -> str:
        return f"<#{channel_id}>" if channel_id else "Not set"

    def _format_role(self, role_name: str | None) -> str:
        return role_name or "Not set"

    async def _rebuild_layout(self):
        settings = await guild_get_settings(self.guild_id) or {}

        log_btn = discord.ui.Button(
            label="Set log channel",
            style=discord.ButtonStyle.secondary,
            emoji="📝",
            custom_id="settings_blacklist_log_channel",
        )
        log_btn.callback = self._set_log_channel

        role_btn = discord.ui.Button(
            label="Set manager role",
            style=discord.ButtonStyle.secondary,
            emoji="🛡️",
            custom_id="settings_blacklist_manager_role",
        )
        role_btn.callback = self._set_manager_role

        self.set_container(
            self.text("## Blacklist settings"),
            self.separator(),
            self.text(f"Blacklist Log Channel: {self._format_channel(settings.get('blacklist_logs_channel'))}"),
            self.text(f"Blacklist Manager Role: {self._format_role(settings.get('blacklist_manager_role'))}"),
            self.separator(),
            self.row(log_btn),
            self.row(role_btn),
            accent=discord.Colour.red(),
        )

    async def send(self, interaction: discord.Interaction):
        await self._rebuild_layout()
        await interaction.response.send_message(view=self, ephemeral=True)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        if self._message is None:
            return

        await self._rebuild_layout()
        await self._message.edit(view=self)

    async def _set_log_channel(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choose the blacklist log channel:",
            view=ChannelSelectView("Set log channel", "blacklist_logs_channel", self.guild_id, self),
            ephemeral=True,
        )

    async def _set_manager_role(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choose the blacklist manager role:",
            view=RoleSelectView("Set blacklist manager role", "blacklist_manager_role", self.guild_id, self),
            ephemeral=True,
        )


class BlacklistSection(Section):
    label = "Blacklist"
    emoji = "Blacklist"
    db_keys = ["blacklist_logs_channel", "blacklist_manager_role", "blacklist_manager_role_id"]

    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        log_ch = settings.get("blacklist_logs_channel")
        bl_role = settings.get("blacklist_manager_role", "Not set")
        return [
            ("Blacklist logs channel", f"<#{log_ch}>" if log_ch else "Not set"),
            ("Blacklist manager role", bl_role),
        ]

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
