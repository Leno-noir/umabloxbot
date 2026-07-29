import discord
from discord.ext import commands

from db.networking import (
    create_dev_post,
    create_project_post,
    get_user_active_dev_post,
    update_networking_post,
)
from .utils import (
    format_dev_role,
    get_dev_role_options,
    get_networking_channel,
    send_dev_post_message,
    send_project_post_message,
    update_public_post,
)


def optional_text(input_field: discord.ui.TextInput | None) -> str | None:
    if not input_field:
        return None

    value = str(input_field.value).strip()

    if not value:
        return None

    return value


class ProjectPostModal(discord.ui.Modal):
    def __init__(
        self,
        bot: commands.Bot,
        dev_role: str,
        post: dict | None = None,
        management_view=None,
    ):
        title = "Edit Project Post" if post else "Project Post"
        super().__init__(title=title)

        self.bot = bot
        self.dev_role = dev_role
        self.post = post
        self.management_view = management_view

        self.project_name = discord.ui.TextInput(
            label="Project name",
            required=True,
            max_length=100,
            default=post.get("project_name") if post else None,
        )

        self.game_link = discord.ui.TextInput(
            label="Game link",
            required=False,
            max_length=200,
            default=post.get("game_link") if post else None,
        )

        self.discord_invite = discord.ui.TextInput(
            label="Discord invite",
            required=False,
            max_length=200,
            default=post.get("discord_invite") if post else None,
        )

        self.contact = discord.ui.TextInput(
            label="Contact",
            placeholder="Optional. Leave empty to use your mention.",
            required=False,
            max_length=100,
            default=post.get("contact") if post else None,
        )

        self.description = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000,
            default=post.get("description") if post else None,
        )

        self.add_item(self.project_name)
        self.add_item(self.game_link)
        self.add_item(self.discord_invite)
        self.add_item(self.contact)
        self.add_item(self.description)

    def project_name_value(self) -> str:
        return str(self.project_name.value).strip()

    def description_value(self) -> str:
        return str(self.description.value).strip()

    def contact_value(self, interaction: discord.Interaction) -> str:
        return optional_text(self.contact) or f"<@{interaction.user.id}>"

    def project_post_data(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> dict:
       
        return {
            "guild_id": interaction.guild_id,
            "author_id": interaction.user.id,
            "author_name": interaction.user.display_name,
            "message_id": None,
            "channel_id": channel.id,
            "post_type": "project",
            "dev_role": self.dev_role,
            "project_name": self.project_name_value(),
            "description": self.description_value(),
            "contact": self.contact_value(interaction),
            "portfolio_url": None,
            "discord_invite": optional_text(self.discord_invite),
            "game_link": optional_text(self.game_link),
            "status": "open",
            "active": True,
        }


    def update_data(self, interaction: discord.Interaction) -> dict:
        return {
            "post_type": "project",
            "dev_role": self.dev_role,
            "project_name": self.project_name_value(),
            "description": self.description_value(),
            "contact": self.contact_value(interaction),
            "portfolio_url": None,
            "discord_invite": optional_text(self.discord_invite),
            "game_link": optional_text(self.game_link),
            "author_name": interaction.user.display_name,
        }


    async def on_submit(self, interaction: discord.Interaction):
        if self.post:
            await self.update_project_post(interaction)
            return

        await self.create_project_post(interaction)


    async def create_project_post(self, interaction: discord.Interaction):
        channel = await get_networking_channel(interaction)

        if not channel:
            await interaction.response.send_message(
                "Networking channel is not configured. Set it in /settings first.",
                ephemeral=True,
            )
            return


        role_options = await get_dev_role_options(interaction.guild_id)
        post_data = self.project_post_data(interaction, channel)

        message = await send_project_post_message(
            channel,
            post_data,
            role_options,
        )

        await create_project_post(
            guild_id=interaction.guild_id,
            author_id=interaction.user.id,
            author_name=interaction.user.display_name,
            message_id=message.id,
            channel_id=channel.id,
            dev_role=self.dev_role,
            project_name=post_data["project_name"],
            description=post_data["description"],
            contact=post_data["contact"],
            discord_invite=post_data["discord_invite"],
            game_link=post_data["game_link"],
        )

        await interaction.response.send_message(
            f"Posted your project listing in {channel.mention}.",
            ephemeral=True,
        )


    async def update_project_post(self, interaction: discord.Interaction):
        updated_post = await update_networking_post(
            str(self.post["_id"]),
            interaction.guild_id,
            interaction.user.id,
            self.update_data(interaction),
        )

        if not updated_post:
            await interaction.response.send_message(
                "This project post could not be updated.",
                ephemeral=True,
            )
            return

        await update_public_post(self.bot, updated_post)

        await interaction.response.send_message(
            "Your project post was updated.",
            ephemeral=True,
        )






class DevPostModal(discord.ui.Modal):
    def __init__(
        self,
        bot: commands.Bot,
        dev_role: str,
        post: dict | None = None,
        management_view=None,
    ):
        title = "Edit Dev Post" if post else "Dev Post"
        super().__init__(title=title)

        self.bot = bot
        self.dev_role = dev_role
        self.post = post
        self.management_view = management_view

        self.description = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000,
            default=post.get("description") if post else None,
        )

        self.portfolio_url = discord.ui.TextInput(
            label="Portfolio URL",
            required=False,
            max_length=200,
            default=post.get("portfolio_url") if post else None,
        )

        self.contact = discord.ui.TextInput(
            label="Contact",
            placeholder="Optional. Leave empty to use your mention.",
            required=False,
            max_length=100,
            default=post.get("contact") if post else None,
        )

        self.add_item(self.description)
        self.add_item(self.portfolio_url)
        self.add_item(self.contact)


    def description_value(self) -> str:
        return str(self.description.value).strip()


    def contact_value(self, interaction: discord.Interaction) -> str:
        return optional_text(self.contact) or f"<@{interaction.user.id}>"


    def dev_post_data(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> dict:
        return {
            "guild_id": interaction.guild_id,
            "author_id": interaction.user.id,
            "author_name": interaction.user.display_name,
            "message_id": None,
            "channel_id": channel.id,
            "post_type": "dev",
            "dev_role": self.dev_role,
            "project_name": None,
            "description": self.description_value(),
            "contact": self.contact_value(interaction),
            "portfolio_url": optional_text(self.portfolio_url),
            "discord_invite": None,
            "game_link": None,
            "status": "open",
            "active": True,
        }


    def update_data(self, interaction: discord.Interaction) -> dict:
        return {
            "post_type": "dev",
            "dev_role": self.dev_role,
            "project_name": None,
            "description": self.description_value(),
            "contact": self.contact_value(interaction),
            "portfolio_url": optional_text(self.portfolio_url),
            "discord_invite": None,
            "game_link": None,
            "author_name": interaction.user.display_name,
        }


    async def on_submit(self, interaction: discord.Interaction):
        if self.post:
            await self.update_dev_post(interaction)
            return

        await self.create_dev_post(interaction)


    async def create_dev_post(self, interaction: discord.Interaction):
        existing_post = await get_user_active_dev_post(
            interaction.guild_id,
            interaction.user.id,
        )

        if existing_post:
            await interaction.response.send_message(
                "You already have a dev post. Use `/networking my-posts` to edit your existing post.",
                ephemeral=True,
            )
            return

        channel = await get_networking_channel(interaction)

        if not channel:
            await interaction.response.send_message(
                "Networking channel is not configured. Set it in /settings first.",
                ephemeral=True,
            )
            return

        role_options = await get_dev_role_options(interaction.guild_id)
        post_data = self.dev_post_data(interaction, channel)

        message = await send_dev_post_message(
            channel,
            post_data,
            role_options,
        )

        await create_dev_post(
            guild_id=interaction.guild_id,
            author_id=interaction.user.id,
            author_name=interaction.user.display_name,
            message_id=message.id,
            channel_id=channel.id,
            dev_role=self.dev_role,
            description=post_data["description"],
            contact=post_data["contact"],
            portfolio_url=post_data["portfolio_url"],
        )

        role_label = format_dev_role(self.dev_role, role_options)

        await interaction.response.send_message(
            f"Posted your {role_label} dev listing in {channel.mention}.",
            ephemeral=True,
        )


    async def update_dev_post(self, interaction: discord.Interaction):
        updated_post = await update_networking_post(
            str(self.post["_id"]),
            interaction.guild_id,
            interaction.user.id,
            self.update_data(interaction),
        )

        if not updated_post:
            await interaction.response.send_message(
                "This dev post could not be updated.",
                ephemeral=True,
            )
            return

        await update_public_post(self.bot, updated_post)

        await interaction.response.send_message(
            "Your dev post was updated.",
            ephemeral=True,
        )