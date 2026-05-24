from __future__ import annotations

import discord

from db import guild_get_settings, guild_save_settings

#this is the configurations panel shown in
#observer guilds that have been allowlisted by the main guild admin,

#saves the other servers selected channel
#for join alerts of blacklisted users, and shows the current setting in an embed field
class ObserverChannelSelect(discord.ui.ChannelSelect):
    """Channel picker used by observer guilds to define join alerts."""

    def __init__(self, guild_id: int, parent_view):
        super().__init__(
            placeholder="Choose the join alert channel...",
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
            ],
        )
        self.guild_id = guild_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        await guild_save_settings(
            self.guild_id,
            {"blacklisted_users_join_alert_channel": channel.id},
        )
        await interaction.response.send_message(
            f"Join alert channel set to {channel.mention}.",
            ephemeral=True,
        )
        await self.parent_view.refresh(interaction)


#observer server version of the settings panel
#only shows the option to set the channel for blacklist join alerts, and no other settings
class ObserverSettingsView(discord.ui.View):
    """Reduced settings panel shown in allowed observer guilds only."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None
        self.add_item(ObserverChannelSelect(guild_id, self))

    async def build_embed(self, guild: discord.Guild) -> discord.Embed:
        """Build the observer settings embed with the local alert channel."""
        settings = await guild_get_settings(guild.id) or {}
        channel_id = settings.get("blacklisted_users_join_alert_channel")

        embed = discord.Embed(
            title=f"Observer Settings - {guild.name}",
            description="Configure local blacklist join alerts for this server.",
            color=0x5865F2,
        )
        embed.add_field(
            name="Blacklisted users join alert channel",
            value=f"<#{channel_id}>" if channel_id else "Not set",
            inline=False,
        )
        embed.set_footer(text="Only administrators can change these settings.")
        return embed

    async def send(self, interaction: discord.Interaction):
        """Send the observer settings panel as an ephemeral message."""
        embed = await self.build_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        """Refresh the observer settings panel after a value changes."""
        if self._message is None:
            return

        guild = interaction.guild if interaction is not None else self._message.guild
        if guild is None:
            return

        embed = await self.build_embed(guild)
        await self._message.edit(embed=embed, view=self)
