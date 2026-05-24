from __future__ import annotations

import discord

from db.guild_configs import guild_get_settings
from .allowed_servers_views import AllowedServersView
from .sections.blacklist import BlacklistSection
from .sections.feedback import FeedbackSection
from .sections.networking import NetworkingSection
from .sections.promotion import PromotionSection

#register all sections here — order controls display order in the main guild settings panel
SECTIONS = [BlacklistSection, PromotionSection, FeedbackSection, NetworkingSection]


class MainGuildSettingsPanel(discord.ui.View):
    """Detailed per-module settings panel for the main guild."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    def _add_section_buttons(self, settings: dict):
        """Attach buttons from all configured settings sections."""
        self.clear_items()
        for section in SECTIONS:
            for btn in section.get_buttons(self.guild_id, self):
                self.add_item(btn)

    @staticmethod
    async def build_embed(guild: discord.Guild) -> discord.Embed:
        """Build the embed that shows current main guild settings."""
        settings = await guild_get_settings(guild.id) or {}

        embed = discord.Embed(
            title=f"Main Guild Settings - {guild.name}",
            description="Configure channels, roles, and module settings for the main guild.",
            color=0x5865F2,
        )

        for section in SECTIONS:
            fields = await section.get_fields(settings)
            lines = "\n".join(f"**{label}:** {value}" for label, value in fields)
            embed.add_field(
                name=f"{section.emoji} {section.label}",
                value=lines or "No settings configured.",
                inline=False,
            )

        embed.set_footer(text="Only administrators can change these settings.")
        return embed

    async def send(self, interaction: discord.Interaction):
        """Send the main guild settings panel."""
        settings = await guild_get_settings(interaction.guild_id) or {}
        self._add_section_buttons(settings)
        embed = await self.build_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        """Refresh the main guild settings panel after changes."""
        if self._message is None:
            return

        guild = interaction.guild if interaction is not None else self._message.guild
        if guild is None:
            return

        settings = await guild_get_settings(guild.id) or {}
        self._add_section_buttons(settings)
        embed = await self.build_embed(guild)
        await self._message.edit(embed=embed, view=self)


class MainSettingsHomeView(discord.ui.View):
    """Home panel for main guild settings and allowlist management."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id

    async def send(self, interaction: discord.Interaction):
        """Send the main settings home screen with navigation options."""
        embed = discord.Embed(
            title="Settings",
            description="Choose which part of the bot network you want to manage.",
            color=0x5865F2,
        )
        embed.add_field(
            name="Main Guild Settings",
            value="Configure roles, channels, and module settings for Uma Portal.",
            inline=False,
        )
        embed.add_field(
            name="Allowed Servers",
            value="Manage observer servers that are approved to participate in the network.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    @discord.ui.button(label="Main Guild Settings", style=discord.ButtonStyle.primary)
    async def open_main_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the detailed settings panel for the main guild."""
        view = MainGuildSettingsPanel(self.guild_id)
        await view.send(interaction)

    @discord.ui.button(label="Allowed Servers", style=discord.ButtonStyle.secondary)
    async def open_allowed_servers(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the allowlist management panel."""
        view = AllowedServersView()
        await view.send(interaction)
