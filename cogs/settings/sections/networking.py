import discord

from core.ui import UmaLayoutView
from db.guild_configs import guild_get_settings
from cogs.networking.utils import get_dev_role_options
from cogs.networking.views import NetworkingConfigureAvailableRolesView

from .base import AdminSettingsLayoutView, ChannelSelectView, Section


class NetworkingSettingsPanel(AdminSettingsLayoutView):
    """Detailed settings panel for networking configuration."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    def _format_channel(self, channel_id: int | None) -> str:
        if channel_id:
            return f"<#{channel_id}>"

        return "Not set"

    async def _rebuild_layout(self):
        settings = await guild_get_settings(self.guild_id) or {}
        dev_roles = await get_dev_role_options(self.guild_id)
        dev_roles_text = ", ".join(label for label, _ in dev_roles)

        channel_button = self.button(
            "Set networking channel",
            discord.ButtonStyle.success,
            self._set_networking_channel,
            emoji="\U0001F310",
            custom_id="settings_networking_channel",
        )
        roles_button = self.button(
            "Set Available Dev Roles",
            discord.ButtonStyle.success,
            self._set_networking_roles,
            emoji="\U0001F4BB",
            custom_id="settings_networking_roles",
        )

        channel_text = self._format_channel(settings.get("networking_channel"))

        self.set_container(
            self.text("## Networking settings"),
            self.separator(),
            self.text(f"Networking Channel: {channel_text}"),
            self.text(f"Dev Roles: {dev_roles_text}"),
            self.separator(),
            self.row(channel_button, roles_button),
            accent=discord.Colour.green(),
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

    async def _set_networking_channel(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choose the networking channel:",
            view=ChannelSelectView(
                "Set networking channel",
                "networking_channel",
                self.guild_id,
                self,
            ),
            ephemeral=True,
        )

    async def _set_networking_roles(self, interaction: discord.Interaction):
        view = NetworkingConfigureAvailableRolesView(
            self.guild_id,
            settings_view=self,
        )
        await view.send(interaction)


class NetworkingSection(Section):
    label = "Networking"
    emoji = "Networking"
    db_keys = ["networking_channel", "networking_dev_roles"]

    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        channel_id = settings.get("networking_channel")
        configured_roles = settings.get("networking_dev_roles") or []

        role_names: list[str] = []
        for configured_role in configured_roles:
            if isinstance(configured_role, dict):
                role_names.append(configured_role.get("label", str(configured_role)))
            else:
                role_names.append(str(configured_role))

        return [
            ("Networking channel", f"<#{channel_id}>" if channel_id else "Not set"),
            ("Dev roles", ", ".join(role_names) if role_names else "Default roles"),
        ]

    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        channel_button = discord.ui.Button(
            label="Set networking channel",
            style=discord.ButtonStyle.secondary,
            row=4,
        )

        async def set_channel(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Choose the networking channel:",
                view=ChannelSelectView(
                    "Set networking channel",
                    "networking_channel",
                    guild_id,
                    parent_view,
                ),
                ephemeral=True,
            )

        channel_button.callback = set_channel
        return [channel_button]
