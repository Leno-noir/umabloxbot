from __future__ import annotations

import discord

from core import MAIN_GUILD_ID, format_guild_id, pagination_text
from db import (
    allowed_guild_add, allowed_guild_exists, allowed_guild_list,
    allowed_guild_remove, allowed_guild_set_enabled,
)


async def sync_commands_after_allowlist_change(interaction: discord.Interaction):
    """Re-sync guild commands after allowlist changes when the bot supports it."""
    sync_handler = getattr(interaction.client, "sync_network_commands", None)
    if sync_handler is not None:
        await sync_handler()


class AddAllowedServerModal(discord.ui.Modal, title="Add allowed server"):
    """Modal used in the main guild to add an observer server by guild ID."""

    #guild id
    guild_id_input = discord.ui.TextInput(
        label="Guild ID",
        placeholder="Paste the server ID here",
    )
    
    #guild name (cant get name from id, only if bot is there)
    guild_name_input = discord.ui.TextInput(
        label="Guild Name",
        placeholder="Type the server name here",
    )

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = format_guild_id(self.guild_id_input.value)
        if not guild_id:
            await interaction.response.send_message("Provide a valid guild ID.", ephemeral=True)
            return

        if guild_id == MAIN_GUILD_ID:
            await interaction.response.send_message(
                "The main guild should not be added to the observer allowlist.",
                ephemeral=True,
            )
            return

        if await allowed_guild_exists(guild_id):
            await interaction.response.send_message(
                "This guild is already in the allowlist.",
                ephemeral=True,
            )
            return

        guild_name = self.guild_name_input.value.strip()
        if not guild_name:
            guild_name = f"Unknown guild ({guild_id})"

        await allowed_guild_add(
            guild_id=guild_id,
            guild_name=guild_name,
            added_by=str(interaction.user),
            server_type="observer",
        )
        await interaction.response.send_message(
            f"Allowed server added: **{guild_name}** (`{guild_id}`).",
            ephemeral=True,
        )
        await sync_commands_after_allowlist_change(interaction)
        await self.parent_view.refresh(interaction)


class RemoveAllowedServerModal(discord.ui.Modal, title="Remove allowed server"):
    """Modal used to remove an observer guild from the allowlist."""

    guild_id_input = discord.ui.TextInput(
        label="Guild ID",
        placeholder="Paste the server ID here",
    )

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = format_guild_id(self.guild_id_input.value)
        if not guild_id:
            await interaction.response.send_message("Provide a valid guild ID.", ephemeral=True)
            return

        removed = await allowed_guild_remove(guild_id)
        if not removed:
            await interaction.response.send_message(
                "That guild was not found in the allowlist.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Removed guild `{guild_id}` from the allowlist.",
            ephemeral=True,
        )
        await sync_commands_after_allowlist_change(interaction)
        await self.parent_view.refresh(interaction)


class ToggleAllowedServerModal(discord.ui.Modal, title="Toggle allowed server"):
    """Modal used to enable or disable an allowed observer guild."""

    guild_id_input = discord.ui.TextInput(
        label="Guild ID",
        placeholder="Paste the server ID here",
    )
    enabled_input = discord.ui.TextInput(
        label="Enabled?",
        placeholder="Type true or false",
    )

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = format_guild_id(self.guild_id_input.value)
        if not guild_id:
            await interaction.response.send_message("Provide a valid guild ID.", ephemeral=True)
            return

        raw_enabled = self.enabled_input.value.strip().lower()
        if raw_enabled not in {"true", "false"}:
            await interaction.response.send_message(
                "Enabled must be `true` or `false`.",
                ephemeral=True,
            )
            return

        enabled = raw_enabled == "true"
        updated = await allowed_guild_set_enabled(guild_id, enabled)
        if not updated:
            await interaction.response.send_message(
                "That guild was not found or already had that status.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Guild `{guild_id}` enabled status set to `{enabled}`.",
            ephemeral=True,
        )
        await sync_commands_after_allowlist_change(interaction)
        await self.parent_view.refresh(interaction)


class AllowedServersView(discord.ui.View):
    """Paginated allowlist management panel shown only in the main guild."""

    def __init__(self):
        super().__init__(timeout=180)
        self.page = 1
        self._message: discord.Message | None = None

    async def build_embed(self) -> discord.Embed:
        """Build the current allowlist page embed."""
        records, total = await allowed_guild_list(skip=(self.page - 1) * 10, limit=10)

        embed = discord.Embed(
            title="Allowed Servers",
            description="Observer servers approved to participate in the network.",
            color=0x5865F2,
        )

        if not records:
            embed.add_field(
                name="Servers",
                value="No allowed observer servers configured.",
                inline=False,
            )
        else:
            for record in records:
                status = "Enabled" if record.get("enabled") else "Disabled"
                embed.add_field(
                    name=record.get("guild_name", "Unknown guild"),
                    value=(
                        f"**Guild ID:** `{record['guild_id']}`\n"
                        f"**Type:** {record.get('server_type', 'observer')}\n"
                        f"**Status:** {status}"
                    ),
                    inline=False,
                )

        embed.set_footer(text=pagination_text(self.page, total))
        return embed

    async def send(self, interaction: discord.Interaction):
        """Send the allowlist management panel."""
        await self._sync_buttons()
        embed = await self.build_embed()
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        """Refresh the allowlist panel after a database change."""
        if self._message is None:
            return

        await self._sync_buttons()
        embed = await self.build_embed()
        await self._message.edit(embed=embed, view=self)

    async def _sync_buttons(self):
        """Enable or disable pagination buttons based on the current page."""
        _, total = await allowed_guild_list(skip=0, limit=1)
        total_pages = max(1, (total + 9) // 10)
        self.prev_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= total_pages

    @discord.ui.button(label="Add server", style=discord.ButtonStyle.success, row=0)
    async def add_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddAllowedServerModal(self))

    @discord.ui.button(label="Remove server", style=discord.ButtonStyle.danger, row=0)
    async def remove_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveAllowedServerModal(self))

    @discord.ui.button(label="Toggle enabled", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_enabled(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ToggleAllowedServerModal(self))

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await interaction.response.defer()
        await self.refresh(interaction)
