import discord

from core import Colors, timestamp_to_discord
from db import bl_list_active
from .modals import BlacklistRemoveModal

# Some interfaces for different views of blacklist
# Like confirmation buttons before removing someone from the blacklist and
# a paginated panel to see the blacklist easier

# Confirmation buttons shown before removing a user.
# 2 buttons: Confirm and Cancel.
# Expires in 30 seconds, after that the buttons will be disabled and cant be used
class ConfirmRemoveView(discord.ui.View):
    """Confirmation buttons shown before removing a user."""

    def __init__(self, user_discord_id: str, user_discord_label: str, bot):
        super().__init__(timeout=30)
        self.user_discord_id = user_discord_id
        self.user_discord_label = user_discord_label
        self.bot = bot
        self.confirmed = False

    #Confirm button, if yes, marks as confirmed and returns
    @discord.ui.button(label="Yes, remove", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.send_modal(
            BlacklistRemoveModal(self.user_discord_id, self.user_discord_label, self.bot)
        )
        self.stop()

    #Cancel button, if no, cancels the action and disables the buttons
    #no need to set confirmed = false since its already set on init
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    #timeout function, disables the buttons after specified time (30 seconds in this case)
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class BlacklistBanPromptView(discord.ui.View):
    """Button that copy the ban command to ban a user that just joined and is on the blacklist."""
    
    def __init__(self, discord_id: int, reason: str):
        super().__init__(timeout=600)
        self.discord_id = discord_id
        self.reason = reason

    @discord.ui.button(label="Copy Ban Command", style=discord.ButtonStyle.primary)
    async def copy_ban_command(self, interaction: discord.Interaction, button: discord.ui.Button):
        command = f"/ban user:{self.discord_id} reason:{self.reason}"
        await interaction.response.send_message(
            f"Command copied to clipboard:\n```{command}```",
            ephemeral=True,
        )

#View to see the blacklist on a panel, with navigation buttons, next and previous pages
class BlacklistPanelView(discord.ui.View):
    """Public paginated panel for browsing the blacklist."""

    def __init__(self):    
        super().__init__(timeout=None) #no timeout, always active
        self.page = 1 #starts on page 1

    #builds the embed message panel
    #10 items per page, calculates how many pages there is
    async def build_embed(self) -> discord.Embed:
        Users_Blacklisted, total = await bl_list_active(skip=(self.page - 1) * 10, limit=10)
        total_pages = max(1, (total + 9) // 10)

        #creates the embed message
        embed = discord.Embed(
            title="Blacklist",
            description=f"**{total}** banned user(s) in total" if total else "The blacklist is currently empty.",
            color=Colors.RED,
        )

        #rest of the embed fields
        for user in Users_Blacklisted:
            added_ts = timestamp_to_discord(user["added_at"])
            embed.add_field(
                name=f"{user.get('roblox_user', '?')} | <@{user['discord_id']}>",
                value=f"Reason: {user['reason']}\nAdded: <t:{added_ts}:d> by {user['added_by']}",
                inline=False,
            )

        #footer with page numbers and buttons
        embed.set_footer(text=f"Page {self.page}/{total_pages}")
        self.prev_button.disabled = self.page <= 1 
        self.next_button.disabled = self.page >= total_pages
        return embed

    #the navigation buttons, previous and next page
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)
