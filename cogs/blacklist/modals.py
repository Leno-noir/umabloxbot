import discord
from discord.ext import commands

from core import Colors
from db import bl_add, bl_is_banned, bl_remove
from .utils import (
    send_blacklist_action_notification,
    send_blacklist_log_broadcast,
)

# Interactive forms for some functions


# Creates a modal to add a user to the blacklist
class BlacklistAddModal(discord.ui.Modal, title="Add user to blacklist"):
    roblox_id = discord.ui.TextInput(
        label="Roblox ID",
        placeholder="e.g. 123456789"
    )
    roblox_user = discord.ui.TextInput(
        label="Roblox username",
        placeholder="e.g. CoolDuck12345"
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
        self, user_discord_id: str,
        user_discord_label: str,
        bot: commands.Bot
    ):
        super().__init__()
        self.user_discord_id = user_discord_id
        self.user_discord_label = user_discord_label
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # if user is already blacklisted, send a message and dont add
        if await bl_is_banned(self.user_discord_id):
            await interaction.followup.send(
                f"{self.user_discord_label} is already on the blacklist.",
                ephemeral=True,
            )
            return

        # saves everything to database (mongodb for now)
        savetodatabase = await bl_add(
            discord_id=self.user_discord_id,
            roblox_id=self.roblox_id.value,
            roblox_user=self.roblox_user.value,
            reason=self.reason.value,
            added_by=str(interaction.user),
            evidence=self.evidence.value or None,
        )

        # creates the embed message to send on log channel
        embed = discord.Embed(
            title="User added to blacklist",
            color=Colors.RED,
            timestamp=savetodatabase["added_at"],
        )
        # rest of the fields of the embed
        embed.add_field(
            name="Discord user",
            value=self.user_discord_label,
            inline=False
        )
        embed.add_field(
            name="Roblox",
            value=f"{self.roblox_user.value} (`{self.roblox_id.value}`)",
            inline=False,
        )
        embed.add_field(
            name="Reason",
            value=self.reason.value,
            inline=False
        )
        
        if self.evidence.value:
            embed.add_field(
                name="Evidence",
                value=self.evidence.value,
                inline=False
        )
            
        embed.add_field(
            name="Added by",
            value=str(interaction.user),
            inline=False
        )
        
        embed.set_footer(text=f"Server: {interaction.guild.name}")

        await send_blacklist_action_notification(
            self.bot,
            interaction,
            embed,
            self.user_discord_label,
            "added"
        )

# 
# Creates a modal to remove a user from the blacklist
class BlacklistRemoveModal(discord.ui.Modal, title="Remove user from blacklist"):
    reason = discord.ui.TextInput(
        label="Reason for removal",
        placeholder="Why is this user being removed?",
        style=discord.TextStyle.paragraph,
    )

    def __init__(
        self, user_discord_id: str,
        user_discord_label: str,
        bot: commands.Bot
    ):
        super().__init__()
        self.user_discord_id = user_discord_id
        self.user_discord_label = user_discord_label
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        #remove someone from the blacklist database
        removed_database = await bl_remove(
            discord_id=self.user_discord_id,
            removed_by=str(interaction.user),
            reason=self.reason.value,
        )

        #if the user was not on the blacklist, send a message and dont do anything
        if not removed_database:
            await interaction.followup.send(
                f"{self.user_discord_label} is not on the blacklist.",
                ephemeral=True,
            )
            return

        # creates the embed message to send on log channel
        embed = discord.Embed(
            title="User removed from blacklist",
            color=Colors.GREEN,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Discord user",
            value=self.user_discord_label,
            inline=False
        )
        embed.add_field(
            name="Reason for removal",
            value=self.reason.value,
            inline=False
        )
        embed.add_field(
            name="Removed by",
            value=str(interaction.user),
            inline=False
        )
        embed.set_footer(text=f"Server: {interaction.guild.name}")

        # sends the embed message to the log channel
        await send_blacklist_action_notification(
            self.bot,
            interaction,
            embed,
            self.user_discord_label,
            "added"
        )
