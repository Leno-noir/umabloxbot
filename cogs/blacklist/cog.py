import discord
from discord import app_commands
from discord.ext import commands

from core import get_user_by_discord_id
from db import bl_global_log, bl_history, bl_is_banned, bl_list_active
from .modals import BlacklistAddModal, BlacklistRemoveModal
from .utils import (
    build_blacklist_history_embed, build_blacklist_info_embed,
    build_blacklist_list_embed, build_blacklist_log_embed,
    is_main_guild_only, is_manager, validate_discord_id,
)
from .views import BlacklistPanelView, ConfirmRemoveView

#General commands from the blacklist

class Blacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #This command add a new user to the blacklist, it will ask for discord id and then send the blacklistaddmodal to the user.
    @app_commands.command(name="blacklist-add", description="Add a user to the shared blacklist")
    @app_commands.describe(discord_id="The Discord user ID to blacklist")
    @is_main_guild_only()
    @is_manager() #checks if person is manager
    @validate_discord_id()
    async def blacklist_add(self, interaction: discord.Interaction, formated_discord_id: str):

        discord_user_label = await get_user_by_discord_id(self.bot, formated_discord_id) #example of output: Leno#1234 (123456789)
        await interaction.response.send_modal(BlacklistAddModal(formated_discord_id, discord_user_label, self.bot))





    #Command for removing someone from the blacklist, will ask for discord id and send the confirmation view
    #if yes, sends to the blacklist remove modal, if no cancels the action
    @app_commands.command(name="blacklist-remove", description="Remove a user from the blacklist")
    @app_commands.describe(discord_id="The Discord user ID to remove")
    @is_main_guild_only()
    @is_manager()
    @validate_discord_id()
    async def blacklist_remove(self, interaction: discord.Interaction, formated_discord_id: str):

        if not await bl_is_banned(formated_discord_id):
            await interaction.response.send_message("This Discord ID is not on the blacklist.", ephemeral=True)
            return

        discord_user_label = await get_user_by_discord_id(self.bot, formated_discord_id)
        view = ConfirmRemoveView(formated_discord_id, discord_user_label, self.bot)
        await interaction.response.send_message(
            f"Are you sure you want to remove **{discord_user_label}** from the blacklist?",
            view=view,
            ephemeral=True,
        )

    
    
    
    
    
    #Command to look up a user status/info on the blacklist
    #Shows if the user is currently banned, the reason, who added them and when
    #and also shows the past entries if they have any (if they were removed from the blacklist before)
    @app_commands.command(name="blacklist-info", description="Look up a user's blacklist status")
    @app_commands.describe(discord_id="The Discord user ID to look up")
    @is_main_guild_only()
    @validate_discord_id()
    async def blacklist_info(self, interaction: discord.Interaction, formated_discord_id: str):

        await interaction.response.defer(ephemeral=True)

        #search for the user blacklist history
        #if no history, send a message saying that the user has no history on the blacklist
        history = await bl_history(formated_discord_id)
        if not history:
            await interaction.followup.send("This Discord ID has no blacklist history.", ephemeral=True)
            return

        discord_user_label = await get_user_by_discord_id(self.bot, formated_discord_id)
        embed, roblox_id = build_blacklist_info_embed(formated_discord_id, discord_user_label, history)

        #add a little button that links to the roblox profile of the user
        view = discord.ui.View()
        if roblox_id:
            view.add_item(discord.ui.Button(
                label="View Roblox profile",
                url=f"https://www.roblox.com/users/{roblox_id}/profile",
                style=discord.ButtonStyle.link,
            ))

        await interaction.followup.send(embed=embed, view=view, ephemeral=True) #private message to who used command






    #basically blacklist-info but all complete history info
    @app_commands.command(name="blacklist-history", description="Show the full blacklist history for a user")
    @app_commands.describe(discord_id="The Discord user ID to look up")
    @is_main_guild_only()
    @is_manager()
    @validate_discord_id()
    async def blacklist_history(self, interaction: discord.Interaction, formated_discord_id: str):

        await interaction.response.defer(ephemeral=True)

        #gets all data from this user on the blacklist, if no history send a message
        history = await bl_history(formated_discord_id)
        if not history:
            await interaction.followup.send("This Discord ID has no blacklist history.", ephemeral=True)
            return

        discord_user_label = await get_user_by_discord_id(self.bot, formated_discord_id)
        embed = build_blacklist_history_embed(formated_discord_id, discord_user_label, history)
        await interaction.followup.send(embed=embed, ephemeral=True)





#Command to list all currently banned users with pagination
#Shows 10 users per page with their roblox username, discord mention, reason and date added
    @app_commands.command(name="blacklist-list", description="List all currently banned users")
    @app_commands.describe(page="Page number (10 users per page)")
    @is_main_guild_only()
    async def blacklist_list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True)
        
        #gets active bans for the current page (10 per page)
        records, total = await bl_list_active(skip=(page - 1) * 10, limit=10)
        #if no records, send a message saying the blacklist is empty
        if not records:
            await interaction.followup.send("The blacklist is empty.", ephemeral=True)
            return

        embed = build_blacklist_list_embed(page, records, total)
        await interaction.followup.send(embed=embed, ephemeral=True)




    #Command to show the full blacklist event log with pagination (every action in the blacklist)
    #Shows all ban and removal events with 10 events per page
    #Restricted to managers only
    @app_commands.command(name="blacklist-log", description="Show the full blacklist event log")
    @app_commands.describe(page="Page number (10 events per page)")
    @is_main_guild_only()
    @is_manager()
    async def blacklist_log(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True)

        #gets global log events for the current page (10 per page)
        records, total = await bl_global_log(skip=(page - 1) * 10, limit=10)
        #if no events found, send a message
        if not records:
            await interaction.followup.send("No events on record.", ephemeral=True)
            return
        embed = build_blacklist_log_embed(page, records, total)
        await interaction.followup.send(embed=embed, ephemeral=True)




    #Command to send the blacklist panel with navigation buttons
    #Public command, no restrictions
    @app_commands.command(name="blacklist-panel", description="Send the blacklist panel with navigation buttons")
    @is_main_guild_only()
    @is_manager()
    async def blacklist_panel(self, interaction: discord.Interaction):
        view = BlacklistPanelView()
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))
