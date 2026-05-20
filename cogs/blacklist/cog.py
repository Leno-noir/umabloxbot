from datetime import timezone

import discord
from discord import app_commands
from discord.ext import commands

from core import Colors, format_discord_id, timestamp_to_discord, pagination_text, get_user_by_discord_id
from db import bl_global_log, bl_history, bl_is_banned, bl_list_active
from .modals import BlacklistAddModal, BlacklistRemoveModal
from .utils import get_active_blacklist_entry, get_past_blacklist_entries, is_manager, validate_discord_id
from .views import BlacklistPanelView, ConfirmRemoveView

#General commands from the blacklist

class Blacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #This command add a new user to the blacklist, it will ask for discord id and then send the blacklistaddmodal to the user.
    @app_commands.command(name="blacklist-add", description="Add a user to the shared blacklist")
    @app_commands.describe(discord_id="The Discord user ID to blacklist")
    @is_manager() #checks if person is manager
    @validate_discord_id()
    async def blacklist_add(self, interaction: discord.Interaction, formated_discord_id: str):

        discord_user_label = await get_user_by_discord_id(self.bot, formated_discord_id) #example of output: Leno#1234 (123456789)
        await interaction.response.send_modal(BlacklistAddModal(formated_discord_id, discord_user_label, self.bot))





    #Command for removing someone from the blacklist, will ask for discord id and send the confirmation view
    #if yes, sends to the blacklist remove modal, if no cancels the action
    @app_commands.command(name="blacklist-remove", description="Remove a user from the blacklist")
    @app_commands.describe(discord_id="The Discord user ID to remove")
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
        
        #wait for user confirmation
        await view.wait()
        
        #if confirmed, show the removal modal
        if view.confirmed:
            await interaction.followup.send_modal(BlacklistRemoveModal(formated_discord_id, discord_user_label, self.bot))

    
    
    
    
    
    #Command to look up a user status/info on the blacklist
    #Shows if the user is currently banned, the reason, who added them and when
    #and also shows the past entries if they have any (if they were removed from the blacklist before)
    @app_commands.command(name="blacklist-info", description="Look up a user's blacklist status")
    @app_commands.describe(discord_id="The Discord user ID to look up")
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
        
        # get the current active ban entry if it exists
        active = get_active_blacklist_entry(history)
        
        # creates the embed message
        embed = discord.Embed(
            title=f"Blacklist info - {discord_user_label}",
            description="CURRENTLY BANNED" if active else "No active ban",
            color=Colors.RED if active else Colors.GRAY,
        )

        #if there is a ban is active, shows the ban information
        if active:
            added_ts = timestamp_to_discord(active["added_at"])
            embed.add_field(name="Discord ID", value=formated_discord_id, inline=False)
            embed.add_field(name="Roblox", value=f"{active['roblox_user']} (`{active['roblox_id']}`)", inline=False)
            embed.add_field(name="Reason", value=active["reason"], inline=False)
            if active.get("evidence"):
                embed.add_field(name="Evidence", value=active["evidence"], inline=False)
            embed.add_field(name="Added by", value=active["added_by"], inline=False)
            embed.add_field(name="Date", value=f"<t:{added_ts}:F>", inline=False)

        #if there is any past ban entrys, show then too (regardless if there is a ban active or not)
        past = get_past_blacklist_entries(history)
        if past:
            lines = [
                f"- <t:{timestamp_to_discord(record['added_at'])}:d> - {record['reason']} (removed by {record.get('removed_by', '?')})"
                for record in past[:5]
            ]
            embed.add_field(name=f"Past entries ({len(past)})", value="\n".join(lines), inline=False)

        #add a little button that links to the roblox profile of the user
        roblox_id = active["roblox_id"] if active else history[0].get("roblox_id")
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
    @is_manager()
    @validate_discord_id()
    async def blacklist_history(self, interaction: discord.Interaction, formated_discord_id: str):

        await interaction.response.defer(ephemeral=True)

        #gets all data from this user on the blacklist, if no history send a message
        history = await bl_history(formated_discord_id)
        if not history:
            await interaction.followup.send("This Discord ID has no blacklist history.", ephemeral=True)
            return

        #embed creation
        discord_user_label = await get_user_by_discord_id(self.bot, formated_discord_id)
        embed = discord.Embed(
            title=f"Blacklist history - {discord_user_label}",
            description=f"{len(history)} event(s) on record",
            color=Colors.BLUE,
        )

        #loop through all records and format them based on whether they are active or removed
        for record in history:
            added_ts = timestamp_to_discord(record["added_at"])
            
            #if record is active (currently banned)
            if record["active"]:
                lines = [
                    f"**Discord ID:** {formated_discord_id}",
                    f"**Reason:** {record['reason']}",
                    f"**Roblox:** {record.get('roblox_user', '?')} (`{record['roblox_id']}`)",
                    f"**Added by:** {record['added_by']}",
                ]
                #add evidence field if it exists
                if record.get("evidence"):
                    lines.insert(3, f"**Evidence:** {record['evidence']}")
                embed.add_field(name=f"Banned - <t:{added_ts}:d>", value="\n".join(lines), inline=False)
           
           #if record is inactive (removed ban)
            else:
                removed_ts = timestamp_to_discord(record["removed_at"]) if record.get("removed_at") else None
                lines = [
                    f"**Discord ID:** {formated_discord_id}",
                    f"**Ban reason:** {record['reason']}",
                ]
                 #add removal information if available
                if removed_ts:
                    lines += [
                        f"**Removed by:** {record.get('removed_by', '?')} on <t:{removed_ts}:d>",
                        f"**Removal reason:** {record.get('remove_reason', '?')}",
                    ]
                embed.add_field(name=f"Unbanned - added <t:{added_ts}:d>", value="\n".join(lines), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)





#Command to list all currently banned users with pagination
#Shows 10 users per page with their roblox username, discord mention, reason and date added
    @app_commands.command(name="blacklist-list", description="List all currently banned users")
    @app_commands.describe(page="Page number (10 users per page)")
    async def blacklist_list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True)
        
        #gets active bans for the current page (10 per page)
        records, total = await bl_list_active(skip=(page - 1) * 10, limit=10)
        #if no records, send a message saying the blacklist is empty
        if not records:
            await interaction.followup.send("The blacklist is empty.", ephemeral=True)
            return

        #creates the embed message with pagination info
        embed = discord.Embed(
            title=f"Blacklist - Page {page}",
            description=f"**{total}** banned user(s) in total",
            color=Colors.RED,
        )
        
        #loop through each banned user and add to embed
        for record in records:
            added_ts = timestamp_to_discord(record["added_at"])
            embed.add_field(
                name=f"{record.get('roblox_user', '?')} | <@{record['discord_id']}>",
                value=f"Reason: {record['reason']}\nAdded: <t:{added_ts}:d> by {record['added_by']}",
                inline=False,
            )
            
        #add pagination footer
        embed.set_footer(text=pagination_text(page, total))
        await interaction.followup.send(embed=embed, ephemeral=True)




    #Command to show the full blacklist event log with pagination (every action in the blacklist)
    #Shows all ban and removal events with 10 events per page
    #Restricted to managers only
    @app_commands.command(name="blacklist-log", description="Show the full blacklist event log")
    @app_commands.describe(page="Page number (10 events per page)")
    @is_manager()
    async def blacklist_log(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True)

        #gets global log events for the current page (10 per page)
        records, total = await bl_global_log(skip=(page - 1) * 10, limit=10)
        #if no events found, send a message
        if not records:
            await interaction.followup.send("No events on record.", ephemeral=True)
            return
        
        #creates the embed message with pagination info
        embed = discord.Embed(
            title=f"Blacklist event log - Page {page}",
            description=f"**{total}** event(s) in total",
            color=Colors.BLUE,
        )
        
        #loop through each event and format based on whether it's a ban or removal
        for record in records:
            added_ts = timestamp_to_discord(record["added_at"])
            user_tag = f"<@{record['discord_id']}> ({record.get('roblox_user', '?')})"
            
            #if record is an active ban event
            if record["active"]:
                embed.add_field(
                    name=f"Banned <t:{added_ts}:d>",
                    value=f"{user_tag}\n**Reason:** {record['reason']}\n**By:** {record['added_by']}",
                    inline=False,
                )
                
            #if record is a removal event
            else:
                removed_ts = timestamp_to_discord(record["removed_at"]) if record.get("removed_at") else None
                removed_line = f"\n**Removed:** <t:{removed_ts}:d> by {record.get('removed_by', '?')}" if removed_ts else ""
                embed.add_field(
                    name=f"Unbanned (banned <t:{added_ts}:d>)",
                    value=f"{user_tag}\n**Ban reason:** {record['reason']}{removed_line}",
                    inline=False,
                )
                
        #add pagination footer
        embed.set_footer(text=pagination_text(page, total))
        await interaction.followup.send(embed=embed, ephemeral=True)




    #Command to send the blacklist panel with navigation buttons
    #Public command, no restrictions
    @app_commands.command(name="blacklist-panel", description="Send the blacklist panel with navigation buttons")
    async def blacklist_panel(self, interaction: discord.Interaction):
        view = BlacklistPanelView()
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))