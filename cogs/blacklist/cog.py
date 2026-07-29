import discord
from discord import app_commands
from discord.ext import commands

from core import get_user_by_discord_id
from db import bl_history, bl_is_banned
from db.guild_configs import (
    guild_get_blacklist_panel_message,
    guild_set_blacklist_panel_message,
)
from .modals import BlacklistAddModal, BlacklistRemoveModal
from .utils import is_main_guild_only, is_manager, validate_discord_id
from .views import (
    BlacklistEventLogView,
    BlacklistHistoryView,
    BlacklistInfoView,
    BlacklistPanelView,
    ConfirmRemoveView,
)


class Blacklist(commands.Cog):
    blacklist_group = app_commands.Group(
        name="blacklist",
        description="Manage the blacklist",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot





    ## ADD USER TO BLACKLIST
    @blacklist_group.command(
        name="add", description="Add a user to the shared blacklist"
    )
    @app_commands.describe(
        discord_id="Add by Discord user ID or @mention if they are in the server"
    )
    
    @is_main_guild_only()
    @is_manager()
    @validate_discord_id()
    
    async def blacklist_add(
        self, interaction: discord.Interaction, formatted_discord_id: str
    ):
        
        discord_user_label = await get_user_by_discord_id(
            self.bot, formatted_discord_id
        )
        
        await interaction.response.send_modal(
            BlacklistAddModal(formatted_discord_id, discord_user_label, self.bot)
        )

    
    
    
    
    
    ## REMOVE USER FROM BLACKLIST
    @blacklist_group.command(
        name="remove", description="Remove a user from the blacklist"
    )
    @app_commands.describe(
        discord_id="Remove by Discord user ID or @mention if they are in the server"
    )
    
    @is_main_guild_only()
    @is_manager()
    @validate_discord_id()
    
    async def blacklist_remove(
        self, interaction: discord.Interaction, formatted_discord_id: str
    ):
        
        if not await bl_is_banned(formatted_discord_id):
            await interaction.response.send_message(
                "This Discord ID is not on the blacklist.", ephemeral=True
            )
            return

       
        discord_user_label = await get_user_by_discord_id(self.bot, formatted_discord_id)
        view = ConfirmRemoveView(formatted_discord_id, discord_user_label, self.bot)
        
        await interaction.response.send_message(
            f"Are you sure you want to remove **{discord_user_label}** from the blacklist?",
            view=view,
            ephemeral=True,
        )

 
 
 
    #SHOW INFO FROM SOMEONE ON THE BLACKLIST
    @blacklist_group.command(
        name="info", description="Look up a user's blacklist status"
    )
    @app_commands.describe(
        discord_id="Look up by Discord user ID or @mention if they are in the server"
    )
    
    @is_main_guild_only()
    @validate_discord_id()
    
    async def blacklist_info(
        self, interaction: discord.Interaction, formatted_discord_id: str
    ):
        
        await interaction.response.defer(ephemeral=True)
        
        discord_user_label = await get_user_by_discord_id(self.bot, formatted_discord_id)
        doc = await bl_history(formatted_discord_id)

        if not doc:
            await interaction.followup.send(
                "This Discord ID has no blacklist history.", ephemeral=True
            )
            return

        roblox_user = doc.get("roblox_user", "Unknown")
        roblox_id = doc.get("roblox_id")

        view = BlacklistInfoView(
            discord_id=formatted_discord_id,
            discord_user=discord_user_label,
            roblox_user=roblox_user,
            roblox_id=roblox_id,
            doc=doc,
        )
        
        await interaction.followup.send(view=view, ephemeral=True)

    
    
    
    
    ## SHOW ALL THE HISTORY OF A BLACKLISTED USER
    @blacklist_group.command(
        name="history",
        description="Show the full blacklist history for a user",
    )
    @app_commands.describe(discord_id="Look up by Discord user ID or @mention if they are in the server")
    
    @is_main_guild_only()
    @is_manager()
    @validate_discord_id()
    
    async def blacklist_history(
        self, interaction: discord.Interaction, formatted_discord_id: str
    ):
        
        await interaction.response.defer(ephemeral=True)

        doc = await bl_history(formatted_discord_id)
        
        if not doc:
            await interaction.followup.send(
                "This Discord ID has no blacklist history.", ephemeral=True
            )
            return

        discord_user_label = await get_user_by_discord_id(self.bot, formatted_discord_id)

        view = BlacklistHistoryView(
            discord_user=discord_user_label,
            discord_id=formatted_discord_id,
            roblox_user=doc["roblox_user"],
            roblox_id=doc["roblox_id"],
            doc=doc,
        )
        
        await view.send(interaction, ephemeral=True)

    
    
    
    
    ## SHOW LIST OF PEOPLE IN THE BLACKLIST
    @blacklist_group.command(
        name="list", description="List all currently banned users"
    )
    @app_commands.describe(page="See all banned users (5 per page)")
    
    @is_main_guild_only()
    
    async def blacklist_list(self, interaction: discord.Interaction, page: int = 1):
        view = BlacklistPanelView(self.bot, page=page)
        
        await view.send(interaction, ephemeral=True)

    
    
    
    
    ## SHOW THE FULL BLACKLIST EVENT LOG
    @blacklist_group.command(
        name="event-log", description="Show the full blacklist event log"
    )
    @app_commands.describe(
        page="See all actions taken on the blacklist (5 per page)"
    )
    
    @is_main_guild_only()
    @is_manager()
    
    async def blacklist_event_log(
        self, interaction: discord.Interaction, page: int = 1
    ):
        
        view = BlacklistEventLogView(page)
        
        await view.send(interaction, ephemeral=True)

    
    
    
    
    
    ## PUBLIC BLACKLIST PANEL WITH NAVIGATION
    @blacklist_group.command(
        name="panel",
        description="Send the blacklist panel with navigation buttons",
    )

    
    @is_main_guild_only()
    @is_manager()
    
    async def blacklist_panel(self, interaction: discord.Interaction):
        view = BlacklistPanelView(self.bot, page=1)
        
        await view.send(interaction, ephemeral=False)
        
        if view._message:
            await guild_set_blacklist_panel_message(
                interaction.guild_id,
                interaction.channel_id,
                view._message.id,
            )




    ### refresh the blacklist panel message if it exists
    async def refresh_blacklist_panel(self, guild_id: int):
        channel_id, message_id = await guild_get_blacklist_panel_message(guild_id)
        
        if not channel_id or not message_id:
            return

        
        guild = self.bot.get_guild(guild_id)
        
        if not guild:
            return

        
        channel = guild.get_channel(channel_id)
        
        if not channel:
            return

        
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return

        view = BlacklistPanelView(self.bot, page=1)
        
        await view._rebuild_layout()
        await message.edit(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))
