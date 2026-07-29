import discord
from discord.ext import commands

from db import bl_add, bl_is_banned, bl_remove
from .utils import refresh_blacklist_panel, send_blacklist_action_notification
from .views import build_blacklist_added_embed, build_blacklist_removed_embed


class BlacklistAddModal(discord.ui.Modal, title="Add user to blacklist"):
    roblox_id = discord.ui.TextInput(
        label="Roblox ID",
        placeholder="e.g. 123456789",
    )
   
    roblox_user = discord.ui.TextInput(
        label="Roblox username",
        placeholder="e.g. CoolDuck12345",
    )
    
    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Why is this user being blacklisted?",
        style=discord.TextStyle.paragraph,
    )
   
    evidence = discord.ui.TextInput(
        label="Evidence (optional)",
        placeholder="Google Docs link with evidence",
        required=False,
    )




    def __init__(
        self,
        user_discord_id: str,
        user_discord_label: str,
        bot: commands.Bot,
    ):
        super().__init__()
        self.user_discord_id = user_discord_id
        self.user_discord_label = user_discord_label
        self.bot = bot




    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if await bl_is_banned(self.user_discord_id):
            await interaction.followup.send(
                f"{self.user_discord_label} is already on the blacklist.",
                ephemeral=True,
            )
            return


        created_entry = await bl_add(
            discord_id=self.user_discord_id,
            roblox_id=self.roblox_id.value,
            roblox_user=self.roblox_user.value,
            reason=self.reason.value,
            added_by=str(interaction.user),
            evidence=self.evidence.value or None,
        )

        view = build_blacklist_added_embed(
            discord_user_label=self.user_discord_label,
            roblox_user=self.roblox_user.value,
            roblox_id=self.roblox_id.value,
            reason=self.reason.value,
            added_by=str(interaction.user),
            timestamp=created_entry["added_at"],
            evidence=self.evidence.value or None,
        )

        await send_blacklist_action_notification(
            self.bot,
            interaction,
            view,
            self.user_discord_label,
            "added",
        )
       
        await refresh_blacklist_panel(self.bot, interaction.guild_id)






class BlacklistRemoveModal(discord.ui.Modal, title="Remove user from blacklist"):
    reason = discord.ui.TextInput(
        label="Reason for removal",
        placeholder="Why is this user being removed?",
        style=discord.TextStyle.paragraph,
    )

    def __init__(
        self,
        user_discord_id: str,
        user_discord_label: str,
        bot: commands.Bot,
    ):
        super().__init__()
        self.user_discord_id = user_discord_id
        self.user_discord_label = user_discord_label
        self.bot = bot




    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        was_removed = await bl_remove(
            discord_id=self.user_discord_id,
            removed_by=str(interaction.user),
            reason=self.reason.value,
        )

        if not was_removed:
            await interaction.followup.send(
                f"{self.user_discord_label} is not on the blacklist.",
                ephemeral=True,
            )
            return

        view = build_blacklist_removed_embed(
            discord_user_label=self.user_discord_label,
            reason=self.reason.value,
            removed_by=str(interaction.user),
        )

        await send_blacklist_action_notification(
            self.bot,
            interaction,
            view,
            self.user_discord_label,
            "removed",
        )
       
        await refresh_blacklist_panel(self.bot, interaction.guild_id)
