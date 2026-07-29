from __future__ import annotations

import discord

from core.ui import UmaLayoutView
from db.guild_configs import guild_save_settings


async def is_settings_administrator(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    return bool(permissions and permissions.administrator)


async def deny_non_admin(interaction: discord.Interaction) -> None:
    message = "Administrator permission is required."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


class AdminSettingsLayoutView(UmaLayoutView):
    """Settings UI that re-checks administrator access on every callback."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await is_settings_administrator(interaction):
            return True
        await deny_non_admin(interaction)
        return False


class AdminSettingsView(discord.ui.View):
    """Standard Discord view variant for settings selects and confirmations."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await is_settings_administrator(interaction):
            return True
        await deny_non_admin(interaction)
        return False


class SettingModal(discord.ui.Modal):
    """Base modal for editing a single text setting value."""

    field = discord.ui.TextInput(label="Value", placeholder="")

    def __init__(self, title: str, label: str, placeholder: str, key: str, guild_id: int, parent_view):
        super().__init__(title=title)
        self.field.label = label
        self.field.placeholder = placeholder
        self._key = key
        self._guild_id = guild_id
        self._parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await guild_save_settings(self._guild_id, {self._key: self.field.value.strip()})
        await interaction.response.send_message(
            f"**{self.field.label}** updated.",
            ephemeral=True,
        )
        await self._parent_view.refresh(interaction)






class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, key: str, guild_id: int, parent_view):
        super().__init__(
            placeholder="Choose a channel...",
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
            ],
        )
        self._key = key
        self._guild_id = guild_id
        self._parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        await guild_save_settings(self._guild_id, {self._key: channel.id})
        await interaction.response.send_message(
            f"Channel set to {channel.mention}",
            ephemeral=True,
        )
        await self._parent_view.refresh(interaction)


class RoleSelect(discord.ui.RoleSelect):
    def __init__(self, key: str, guild_id: int, parent_view):
        super().__init__(
            placeholder="Choose a role...",
            min_values=1,
            max_values=1,
        )
        self._key = key
        self._guild_id = guild_id
        self._parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        # Save both role name and ID for manager-only commands
        settings = {self._key: role.name}
        # Save a matching ID field for role settings used by permissions or pings.
        if self._key.endswith("_role"):
            settings[self._key.replace("_role", "_role_id")] = role.id
        await guild_save_settings(self._guild_id, settings)
        await interaction.response.send_message(
            f"Role set to **{role.name}**",
            ephemeral=True,
        )
        await self._parent_view.refresh(interaction)


class ChannelSelectView(AdminSettingsView):
    def __init__(self, title: str, key: str, guild_id: int, parent_view):
        super().__init__(timeout=120)
        self.title = title
        self.add_item(ChannelSelect(key, guild_id, parent_view))


class RoleSelectView(AdminSettingsView):
    def __init__(self, title: str, key: str, guild_id: int, parent_view):
        super().__init__(timeout=120)
        self.title = title
        self.add_item(RoleSelect(key, guild_id, parent_view))


class Section:
    label: str = "Section"
    emoji: str = "Settings"
    db_keys: list[str] = []

    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        return []

    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        return []
