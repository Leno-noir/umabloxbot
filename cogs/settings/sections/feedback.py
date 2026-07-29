"""Settings section for the feedback module.

Allows admins to configure:
- Feedback channel
- Feedback manager role
- Anonymous feedback toggle (global)
- Add/remove/toggle games
"""

import logging

import discord

from core import Colors
from core.ui import UmaLayoutView
from db.feedback import (
    feedback_add_game,
    feedback_get_games,
    feedback_remove_game,
    feedback_toggle_game_active,
)
from db.guild_configs import (
    guild_get_feedback_channel,
    guild_get_settings,
    guild_save_settings,
    guild_toggle_feedback_anonymous,
)

logger = logging.getLogger(__name__)
from .base import AdminSettingsLayoutView, AdminSettingsView, ChannelSelectView, Section


class FeedbackSettingsPanel(AdminSettingsLayoutView):
    """Detailed settings panel for feedback configuration."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    def _format_channel(self, channel_id: int | None) -> str:
        return f"<#{channel_id}>" if channel_id else "Not set"

    def _format_role(self, role_name: str | None) -> str:
        return role_name or "Not set"

    def _format_bool(self, value: bool) -> str:
        return ":white_check_mark: Yes" if value else "❌ No"

    def _build_games_lines(self, games: list[dict]) -> list[discord.ui.TextDisplay]:
        if not games:
            return [self.text("Games: No games configured yet")]

        lines = [self.text(f"**Games ({len(games)})**")]
        for game in games:
            status = ":white_check_mark:  Active" if game["active"] else "❌ Inactive"
            lines.append(self.text(f"- {game['name']} | {game['role_name']} | {status}"))
        return lines

    async def _rebuild_layout(self):
        settings = await guild_get_settings(self.guild_id) or {}
        games = await feedback_get_games(self.guild_id)

        channel_btn = discord.ui.Button(
            label="Set Feedback Channel",
            style=discord.ButtonStyle.secondary,
            emoji="📨",
            custom_id="settings_feedback_channel",
        )
        channel_btn.callback = self._set_channel

        role_btn = discord.ui.Button(
            label="Set Manager Role",
            style=discord.ButtonStyle.secondary,
            emoji="🛡️",
            custom_id="settings_feedback_role",
        )
        role_btn.callback = self._set_role

        anon_btn = discord.ui.Button(
            label="Toggle Anonymous",
            style=discord.ButtonStyle.primary,
            emoji="🕶️",
            custom_id="settings_feedback_anonymous",
        )
        anon_btn.callback = self._toggle_anon

        add_game_btn = discord.ui.Button(
            label="Add Game",
            style=discord.ButtonStyle.success,
            emoji="➕",
            custom_id="settings_feedback_add_game",
        )
        add_game_btn.callback = self._add_game

        remove_game_btn = discord.ui.Button(
            label="Remove Game",
            style=discord.ButtonStyle.danger,
            emoji="➖",
            custom_id="settings_feedback_remove_game",
        )
        remove_game_btn.callback = self._remove_game

        toggle_game_btn = discord.ui.Button(
            label="Toggle Game Active",
            style=discord.ButtonStyle.secondary,
            emoji="⚙️",
            custom_id="settings_feedback_toggle_game",
        )
        toggle_game_btn.callback = self._toggle_game

        self.set_container(
            self.text("## Feedback settings"),
            self.text("Manage feedback channels, access, and tracked games."),
            self.separator(),
            self.text(f"Feedback Channel: {self._format_channel(settings.get('feedback_channel'))}"),
            self.text(f"Manager Role: {self._format_role(settings.get('feedback_manager_role'))}"),
            self.text(f"Anonymous Allowed: {self._format_bool(settings.get('feedback_anonymous_allowed', False))}"),
            self.separator(),
            *self._build_games_lines(games),
            self.separator(),
            self.row(channel_btn, role_btn),
            self.row(anon_btn, add_game_btn),
            self.row(remove_game_btn, toggle_game_btn),
            accent=discord.Colour.blue(),
        )

    async def send(self, interaction: discord.Interaction):
        """Send the feedback settings panel."""
        await self._rebuild_layout()
        await interaction.response.send_message(view=self, ephemeral=True)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        """Refresh the feedback settings panel after changes."""
        if self._message is None:
            return

        await self._rebuild_layout()
        await self._message.edit(view=self)

    async def _set_channel(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choose the feedback channel:",
            view=ChannelSelectView(
                "Set feedback channel",
                "feedback_channel",
                self.guild_id,
                self,
            ),
            ephemeral=True,
        )

    async def _set_role(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choose the feedback manager role:",
            view=FeedbackManagerRoleSelectView(self.guild_id, self),
            ephemeral=True,
        )

    async def _toggle_anon(self, interaction: discord.Interaction):
        new_status = await guild_toggle_feedback_anonymous(self.guild_id)
        status_text = "Enabled" if new_status else "Disabled"
        await interaction.response.send_message(
            f"Anonymous submissions: {status_text}",
            ephemeral=True,
        )
        await self.refresh(interaction)

    async def _add_game(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackAddGameModal(self.guild_id, self))

    async def _remove_game(self, interaction: discord.Interaction):
        games = await feedback_get_games(self.guild_id)

        if not games:
            await interaction.response.send_message(
                "No games configured yet.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Choose a game to remove:",
            view=FeedbackGameRemoveSelectView(games, self.guild_id, self),
            ephemeral=True,
        )

    async def _toggle_game(self, interaction: discord.Interaction):
        games = await feedback_get_games(self.guild_id)

        if not games:
            await interaction.response.send_message(
                "No games configured yet.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Choose a game to toggle:",
            view=FeedbackGameToggleSelectView(games, self.guild_id, self),
            ephemeral=True,
        )


class FeedbackAddGameModal(discord.ui.Modal, title="Add Feedback Game"):
    """Modal to add a new game to the feedback system."""

    game_name = discord.ui.TextInput(
        label="Game Name",
        placeholder="e.g., Umapyoi Legends",
        required=True,
    )

    def __init__(self, guild_id: int, parent_view):
        super().__init__()
        self.guild_id = guild_id
        self.parent_view = parent_view
        self.selected_role = None

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Now choose the role for this game:",
            view=FeedbackGameRoleSelectView(
                self.guild_id,
                self.game_name.value,
                self.parent_view,
            ),
            ephemeral=True,
        )


class FeedbackGameRoleSelect(discord.ui.RoleSelect):
    """Role selector for a specific game."""

    def __init__(self, guild_id: int, game_name: str, parent_view):
        super().__init__(
            placeholder="Choose role for this game...",
            min_values=1,
            max_values=1,
        )
        self.guild_id = guild_id
        self.game_name = game_name
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]

        try:
            channel_id = await guild_get_feedback_channel(self.guild_id)
            if not channel_id:
                await interaction.response.send_message(
                    "Feedback channel not configured. Set it first in /settings > Feedback.",
                    ephemeral=True,
                )
                return

            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message(
                    "Feedback channel not found.",
                    ephemeral=True,
                )
                return

            thread = await channel.create_thread(
                name=f"🐴 {self.game_name}",
                type=discord.ChannelType.private_thread,
            )

            await feedback_add_game(
                guild_id=self.guild_id,
                name=self.game_name,
                role_name=role.name,
                role_id=role.id,
                thread_id=thread.id,
            )

            await interaction.response.send_message(
                f"Game **{self.game_name}** added! Role: **{role.name}**\n"
                f"Feedback thread: {thread.mention}",
                ephemeral=True,
            )

            await self.parent_view.refresh(interaction)

            try:
                feedback_cog = interaction.client.get_cog("Feedback")
                if feedback_cog:
                    await feedback_cog.refresh_feedback_panel(self.guild_id)
            except Exception:
                logger.exception("Could not refresh feedback panel after adding a game")

        except Exception:
            logger.exception("Error adding feedback game")
            await interaction.response.send_message(
                "Error adding game. Please try again.",
                ephemeral=True,
            )


class FeedbackGameRoleSelectView(AdminSettingsView):
    """View container for role selection."""

    def __init__(self, guild_id: int, game_name: str, parent_view):
        super().__init__(timeout=120)
        self.add_item(FeedbackGameRoleSelect(guild_id, game_name, parent_view))


class FeedbackGameRemoveSelect(discord.ui.Select):
    """Dropdown to remove an existing game."""

    def __init__(self, games: list[dict], guild_id: int, parent_view):
        options = [
            discord.SelectOption(label=game["name"], value=game["name"])
            for game in games
        ]

        super().__init__(
            placeholder="Choose a game to remove...",
            options=options,
            min_values=1,
            max_values=1,
        )

        self.guild_id = guild_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]

        embed = discord.Embed(
            title="Remove Game?",
            description=(
                f"Are you sure you want to remove **{game_name}**?\n\n"
                "This will NOT delete feedback entries, just remove the game from the active list."
            ),
            color=Colors.YELLOW,
        )

        await interaction.response.send_message(
            embed=embed,
            view=FeedbackGameRemoveConfirmView(game_name, self.guild_id, self.parent_view),
            ephemeral=True,
        )


class FeedbackGameRemoveSelectView(AdminSettingsView):
    """View container for remove selection."""

    def __init__(self, games: list[dict], guild_id: int, parent_view):
        super().__init__(timeout=120)
        if games:
            self.add_item(FeedbackGameRemoveSelect(games, guild_id, parent_view))


class FeedbackGameRemoveConfirmView(AdminSettingsView):
    """Confirmation buttons for removing a game."""

    def __init__(self, game_name: str, guild_id: int, parent_view):
        super().__init__(timeout=60)
        self.game_name = game_name
        self.guild_id = guild_id
        self.parent_view = parent_view

    @discord.ui.button(label="Yes, remove", style=discord.ButtonStyle.danger)
    async def confirm_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await feedback_remove_game(self.guild_id, self.game_name)

            await interaction.response.send_message(
                f"Game **{self.game_name}** removed.",
                ephemeral=True,
            )

            await self.parent_view.refresh(interaction)

            try:
                feedback_cog = interaction.client.get_cog("Feedback")
                if feedback_cog:
                    await feedback_cog.refresh_feedback_panel(self.guild_id)
            except Exception:
                logger.exception("Could not refresh feedback panel after removing a game")

        except Exception:
            logger.exception("Error removing feedback game")
            await interaction.response.send_message(
                "Error removing game.",
                ephemeral=True,
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()


class FeedbackGameToggleSelect(discord.ui.Select):
    """Dropdown to toggle a game's active status."""

    def __init__(self, games: list[dict], guild_id: int, parent_view):
        options = [
            discord.SelectOption(
                label=f"{'Active' if game['active'] else 'Inactive'} - {game['name']}",
                value=game["name"],
            )
            for game in games
        ]

        super().__init__(
            placeholder="Choose a game to toggle...",
            options=options,
            min_values=1,
            max_values=1,
        )

        self.guild_id = guild_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]

        try:
            await feedback_toggle_game_active(self.guild_id, game_name)

            await interaction.response.send_message(
                f"Game **{game_name}** toggled.",
                ephemeral=True,
            )

            await self.parent_view.refresh(interaction)

            try:
                feedback_cog = interaction.client.get_cog("Feedback")
                if feedback_cog:
                    await feedback_cog.refresh_feedback_panel(self.guild_id)
            except Exception:
                logger.exception("Could not refresh feedback panel after toggling a game")

        except Exception:
            logger.exception("Error toggling feedback game")
            await interaction.response.send_message(
                "Error toggling game.",
                ephemeral=True,
            )


class FeedbackGameToggleSelectView(AdminSettingsView):
    """View container for toggle selection."""

    def __init__(self, games: list[dict], guild_id: int, parent_view):
        super().__init__(timeout=120)
        if games:
            self.add_item(FeedbackGameToggleSelect(games, guild_id, parent_view))


class FeedbackManagerRoleSelect(discord.ui.RoleSelect):
    """Role selector for feedback manager."""

    def __init__(self, guild_id: int, parent_view):
        super().__init__(
            placeholder="Choose feedback manager role...",
            min_values=1,
            max_values=1,
        )
        self.guild_id = guild_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]

        await guild_save_settings(
            self.guild_id,
            {
                "feedback_manager_role": role.name,
                "feedback_manager_role_id": role.id,
            },
        )

        await interaction.response.send_message(
            f"Manager role set to **{role.name}**",
            ephemeral=True,
        )

        await self.parent_view.refresh(interaction)


class FeedbackManagerRoleSelectView(AdminSettingsView):
    """View container for manager role selection."""

    def __init__(self, guild_id: int, parent_view):
        super().__init__(timeout=120)
        self.add_item(FeedbackManagerRoleSelect(guild_id, parent_view))


class FeedbackSection(Section):
    """Settings section for feedback configuration."""

    label = "Feedback"
    emoji = "📬"
    db_keys = [
        "feedback_channel",
        "feedback_manager_role",
        "feedback_manager_role_id",
        "feedback_anonymous_allowed",
    ]

    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        """Display current feedback configuration."""
        fb_channel = settings.get("feedback_channel")
        fb_role = settings.get("feedback_manager_role", "Not set")
        fb_anon = settings.get("feedback_anonymous_allowed", False)

        return [
            ("Feedback channel", f"<#{fb_channel}>" if fb_channel else "Not set"),
            ("Manager role", fb_role),
            ("Anonymous allowed", "Yes" if fb_anon else "No"),
        ]

    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        """Create a single button to open the feedback settings panel."""
        btn = discord.ui.Button(
            label="Feedback Settings",
            style=discord.ButtonStyle.primary,
            emoji="📬",
            row=1,
        )

        async def open_feedback_settings(interaction: discord.Interaction):
            panel = FeedbackSettingsPanel(guild_id)
            await panel.send(interaction)

        btn.callback = open_feedback_settings
        return [btn]
