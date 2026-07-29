from __future__ import annotations

import discord

from cogs.funsies.views import FunsiesSettingsPanel
from core.ui import UmaLayoutView
from db.funsies import funsies_get_gacha_rarity_chances, funsies_get_gacha_rarity_names, funsies_get_settings
from db.guild_configs import guild_get_settings
from .allowed_servers_views import AllowedServersView
from .sections.blacklist import BlacklistSettingsPanel
from .sections.feedback import FeedbackSettingsPanel
from .sections.networking import NetworkingSettingsPanel
from .sections.base import AdminSettingsLayoutView


class MainGuildSettingsPanel(AdminSettingsLayoutView):
    """Modern main guild settings panel with summary and section shortcuts."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    def _format_channel(self, channel_id: int | None) -> str:
        return f"<#{channel_id}>" if channel_id else "Not set"

    def _format_role(self, role_name: str | None) -> str:
        return role_name or "Not set"

    def _format_bool(self, value: bool) -> str:
        return "Yes" if value else "No"

    def _build_info_container(self, settings: dict, funsies_settings: dict, chances_text: str) -> discord.ui.Container:
        return self.container(
            self.media("https://i.imgur.com/JMOAUkc.png"),
            self.separator(),
            self.text("## Actual configurations"),
            self.separator(),
            self.text("**Blacklist**"),
            self.text(f"Blacklist Log Channel: {self._format_channel(settings.get('blacklist_logs_channel'))}"),
            self.text(f"Blacklist Manager Role: {self._format_role(settings.get('blacklist_manager_role'))}"),
            self.separator(),
            self.text("**Feedback**"),
            self.text(f"Feedback Channel: {self._format_channel(settings.get('feedback_channel'))}"),
            self.text(f"Feedback Manager Role: {self._format_role(settings.get('feedback_manager_role'))}"),
            self.text(f"Anonymous Feedback Allowed: {self._format_bool(settings.get('feedback_anonymous_allowed', False))}"),
            self.separator(),
            self.text("**Networking**"),
            self.text(f"Networking Channel: {self._format_channel(settings.get('networking_channel'))}"),
            self.separator(),
            self.text("**Funsies**"),
            self.text(f"Quote Enabled: {self._format_bool(funsies_settings.get('quote_enabled', True))}"),
            self.text(f"Fact Enabled: {self._format_bool(funsies_settings.get('fact_enabled', True))}"),
            self.text(
                f"Uma Collection Enabled: {self._format_bool(funsies_settings.get('uma_collection_enabled', True))}"
            ),
            self.text(f"Daily Gacha Limit: {funsies_settings.get('daily_gacha_limit', 50)}"),
            self.text(f"Gacha Chances: {chances_text}"),
            accent=discord.Colour(3447003),
        )

    def _build_navigation_container(self) -> discord.ui.Container:
        blacklist_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Blacklist Settings",
            custom_id="settings_blacklist_section",
        )
        blacklist_btn.callback = self._open_blacklist_settings

        feedback_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Feedback Settings",
            custom_id="settings_feedback_section",
        )
        feedback_btn.callback = self._open_feedback_settings

        networking_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Networking Settings",
            custom_id="settings_networking_section",
        )
        networking_btn.callback = self._open_networking_settings

        funsies_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Funsies Settings",
            custom_id="settings_funsies_section",
        )
        funsies_btn.callback = self._open_funsies_settings

        return self.container(
            self.row(blacklist_btn, feedback_btn),
            self.row(networking_btn, funsies_btn),
            accent=discord.Colour(5793266),
        )

    async def _rebuild_layout(self):
        settings = await guild_get_settings(self.guild_id) or {}
        funsies_settings = await funsies_get_settings(self.guild_id)
        gacha_chances = await funsies_get_gacha_rarity_chances(self.guild_id)
        rarity_names = await funsies_get_gacha_rarity_names(self.guild_id)
        chances_text = ", ".join(
            f"{rarity_names.get(rarity, rarity)} {chance}%"
            for rarity, chance in gacha_chances.items()
        )
        self.set_items(
            self._build_info_container(settings, funsies_settings, chances_text),
            self._build_navigation_container(),
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

    async def _open_blacklist_settings(self, interaction: discord.Interaction):
        panel = BlacklistSettingsPanel(self.guild_id)
        await panel.send(interaction)

    async def _open_feedback_settings(self, interaction: discord.Interaction):
        panel = FeedbackSettingsPanel(self.guild_id)
        await panel.send(interaction)

    async def _open_networking_settings(self, interaction: discord.Interaction):
        panel = NetworkingSettingsPanel(self.guild_id)
        await panel.send(interaction)

    async def _open_funsies_settings(self, interaction: discord.Interaction):
        panel = FunsiesSettingsPanel(self.guild_id)
        await panel.send(interaction)


class MainSettingsHomeView(AdminSettingsLayoutView):
    """Home panel for main guild settings and allowlist management using modern UI."""

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

        main_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Main Guild Settings",
            custom_id="settings_main_guild",
        )
        main_btn.callback = self._open_main_settings

        allowed_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Allowed Server Settings",
            custom_id="settings_allowed_servers",
        )
        allowed_btn.callback = self._open_allowed_servers

        self.set_container(
            self.media("https://i.imgur.com/JMOAUkc.png"),
            self.text("Choose which part of the bot you want to configure"),
            self.separator(),
            self.row(main_btn),
            self.row(allowed_btn),
            accent=discord.Colour(10070709),
        )

    async def send(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=self, ephemeral=True)

    async def _open_main_settings(self, interaction: discord.Interaction):
        view = MainGuildSettingsPanel(self.guild_id)
        await view.send(interaction)

    async def _open_allowed_servers(self, interaction: discord.Interaction):
        view = AllowedServersView()
        await view.send(interaction)
