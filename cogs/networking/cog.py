import discord
from discord import app_commands
from discord.ext import commands

from db.networking import get_user_active_dev_post
from .utils import get_dev_role_options, get_networking_channel, networking_channel_is_configured
from .views import (
    DevRoleSelectView,
    MyPostsMenuView,
    NetworkingListView,
    ProjectRoleSelectView,
)


class Networking(commands.Cog):
    networking_group = app_commands.Group(
        name="networking",
        description="Developer networking commands",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot





    ## Helper methods for sending views and messages
    async def show_project_role_selector(self, interaction: discord.Interaction):
        if not await networking_channel_is_configured(interaction):
            return

        dev_role_options = await get_dev_role_options(interaction.guild_id)

        role_select_view = ProjectRoleSelectView(
            self.bot,
            dev_role_options,
        )

        await interaction.response.send_message(
            "Select the developer role your project needs.",
            view=role_select_view,
            ephemeral=True,
        )






    async def show_dev_role_selector(self, interaction: discord.Interaction):
        if not await networking_channel_is_configured(interaction):
            return

        dev_post = await get_user_active_dev_post(
            interaction.guild_id,
            interaction.user.id,
        )

        if dev_post:
            await interaction.response.send_message(
                "You already have a dev post. Use `/networking my-posts` to edit your existing post.",
                ephemeral=True,
            )
            return

        dev_role_options = await get_dev_role_options(interaction.guild_id)

        role_select_view = DevRoleSelectView(
            self.bot,
            dev_role_options,
        )

        await interaction.response.send_message(
            "Select your developer role.",
            view=role_select_view,
            ephemeral=True,
        )






    async def send_networking_list(self, interaction: discord.Interaction):
        view = NetworkingListView(interaction.guild_id, post_type="project")
        await view.send(interaction, ephemeral=True)





    async def send_my_posts_menu(self, interaction: discord.Interaction):
        view = MyPostsMenuView(self.bot, interaction.guild_id, interaction.user.id)
        await view.send(interaction)




    ## command to post a project looking for developers
    @networking_group.command(
        name="project-post",
        description="Create a project looking for developers post",
    )
    async def project_post(self, interaction: discord.Interaction):
        await self.show_project_role_selector(interaction)

    
    
    
    ## command to post a developer looking for work
    @networking_group.command(
        name="dev-post",
        description="Create a developer looking for work post",
    )
    async def dev_post(self, interaction: discord.Interaction):
        await self.show_dev_role_selector(interaction)

  
  
  
  
  ## command to show the list of networking posts
    @networking_group.command(
        name="list",
        description="Show networking posts",
    )
    async def list(self, interaction: discord.Interaction):
        await self.send_networking_list(interaction)

   
   
   
   
   ## command to manage your own networking posts
    @networking_group.command(
        name="my-posts",
        description="Manage your networking posts",
    )
    async def my_posts(self, interaction: discord.Interaction):
        await self.send_my_posts_menu(interaction)





async def setup(bot: commands.Bot):
    await bot.add_cog(Networking(bot))
