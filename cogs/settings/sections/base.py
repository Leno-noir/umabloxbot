from __future__ import annotations

import discord

from db.guild_configs import guild_save_settings


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
        # If this is a manager role, also save the ID for permission restrictions
        if "manager_role" in self._key:
            settings[self._key.replace("_role", "_role_id")] = role.id
        await guild_save_settings(self._guild_id, settings)
        await interaction.response.send_message(
            f"Role set to **{role.name}**",
            ephemeral=True,
        )
        await self._parent_view.refresh(interaction)


class ChannelSelectView(discord.ui.View):
    def __init__(self, title: str, key: str, guild_id: int, parent_view):
        super().__init__(timeout=120)
        self.title = title
        self.add_item(ChannelSelect(key, guild_id, parent_view))


class RoleSelectView(discord.ui.View):
    def __init__(self, title: str, key: str, guild_id: int, parent_view):
        super().__init__(timeout=120)
        self.title = title
        self.add_item(RoleSelect(key, guild_id, parent_view))


class Section:
    label: str = "Section"
    emoji: str = "Settings"
    db_keys: list[str] = []

    @staticmethod
    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        return []

    @staticmethod
    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        return []
