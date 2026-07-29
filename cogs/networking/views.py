import discord

from core.ui import PaginatedLayoutView, UmaLayoutView, separator, text
from db.guild_configs import guild_save_settings
from db.networking import (
    delete_networking_post,
    get_networking_posts,
    get_user_active_dev_post,
    get_user_networking_post,
    get_user_project_posts,
    set_post_status,
)
from .utils import (
    DEFAULT_DEV_ROLE_OPTIONS,
    delete_public_post,
    dev_role_value,
    format_dev_role,
    format_post_status,
    get_dev_role_options,
    is_project_post,
    next_post_status,
    post_created_timestamp,
    project_display_name,
    serialize_dev_role_options,
    short_post_id,
    update_public_post,
)





def role_select_options(role_options: list[tuple[str, str]]) -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=label, value=value)
        for label, value in role_options[:25]
    ]






def role_filter_options(role_options: list[tuple[str, str]]) -> list[discord.SelectOption]:
    options = [discord.SelectOption(label="All roles", value="all")]

    for label, value in role_options[:24]:
        options.append(discord.SelectOption(label=label, value=value))

    return options






async def owner_can_manage(interaction: discord.Interaction, user_id: int) -> bool:
    if interaction.user.id == user_id:
        return True

    await interaction.response.send_message(
        "You can only manage your own networking posts.",
        ephemeral=True,
    )
    return False






def project_post_select_options(project_posts: list[dict]) -> list[discord.SelectOption]:
    options: list[discord.SelectOption] = []

    for post in project_posts[:25]:
        label = project_display_name(post)
        status = format_post_status(post.get("status"))
        created = post_created_timestamp(post)
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=str(post["_id"]),
                description=f"{status} | {created} | ID {short_post_id(post)}"[:100],
            )
        )

    return options






class ProjectRoleSelectView(discord.ui.View):
    def __init__(self, bot, dev_role_options: list[tuple[str, str]]):
        super().__init__(timeout=120)
        self.bot = bot

        project_role_select = discord.ui.Select(
            placeholder="Choose the role your project needs...",
            options=role_select_options(dev_role_options),
            min_values=1,
            max_values=1,
        )

        project_role_select.callback = self.open_project_post_modal
        self.add_item(project_role_select)

    async def open_project_post_modal(self, interaction: discord.Interaction):
        from .modals import ProjectPostModal

        selected_role = interaction.data["values"][0]

        await interaction.response.send_modal(
            ProjectPostModal(self.bot, selected_role)
        )





class DevRoleSelectView(discord.ui.View):
    def __init__(self, bot, dev_role_options: list[tuple[str, str]]):
        super().__init__(timeout=120)
        self.bot = bot

        dev_role_select = discord.ui.Select(
            placeholder="Choose your developer role...",
            options=role_select_options(dev_role_options),
            min_values=1,
            max_values=1,
        )

        dev_role_select.callback = self.open_dev_post_modal
        self.add_item(dev_role_select)


    async def open_dev_post_modal(self, interaction: discord.Interaction):
        from .modals import DevPostModal

        selected_role = interaction.data["values"][0]

        await interaction.response.send_modal(
            DevPostModal(self.bot, selected_role)
        )






class NetworkingListView(PaginatedLayoutView):
    items_per_page = 5

    def __init__(self, guild_id: int, post_type: str = "project"):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.post_type = post_type
        self.dev_role: str | None = None



    def list_title(self) -> str:
        if self.post_type == "dev":
            return "Developers Looking for Work"

        return "Projects Looking for Developers"


    def current_filter_text(self, role_options: list[tuple[str, str]]) -> str:
        if self.dev_role:
            return format_dev_role(self.dev_role, role_options)

        return "All roles"


    def post_contact_text(self, post: dict) -> str:
        contact = post.get("contact")

        if contact:
            return contact

        return f"<@{post['author_id']}>"


    def post_title_text(
        self,
        post: dict,
        role_options: list[tuple[str, str]],
    ) -> str:
        role_label = format_dev_role(post["dev_role"], role_options)

        if is_project_post(post):
            project_name = project_display_name(post)
            return f"**{project_name}** needs **{role_label}**"

        author_name = post.get("author_name", "Developer")
        return f"**{author_name}** - **{role_label}**"


    def add_post_to_items(
        self,
        items: list[discord.ui.Item],
        post: dict,
        role_options: list[tuple[str, str]],
    ):
        items.append(text(self.post_title_text(post, role_options)))
        items.append(text(post["description"]))
        items.append(text(f"Contact: {self.post_contact_text(post)}"))
        items.append(text(f"Posted: {post_created_timestamp(post)}"))
        items.append(separator())


    def make_role_filter_select(
        self,
        role_options: list[tuple[str, str]],
    ) -> discord.ui.Select:
        return self.select(
            "Filter by role...",
            role_filter_options(role_options),
            self.filter_by_role,
        )


    def make_post_type_buttons(self):
        project_button = self.button(
            "Project Posts",
            discord.ButtonStyle.primary,
            self.show_projects,
        )

        dev_button = self.button(
            "Dev Posts",
            discord.ButtonStyle.primary,
            self.show_devs,
        )

        return project_button, dev_button


    async def _rebuild_layout(self):
        role_options = await get_dev_role_options(self.guild_id)

        posts = await get_networking_posts(
            self.guild_id,
            self.post_type,
            dev_role=self.dev_role,
        )

        total_pages = self.clamp_page(len(posts))
        page_posts = self.page_items(posts)

        role_select = self.make_role_filter_select(role_options)
        project_button, dev_button = self.make_post_type_buttons()

        items: list[discord.ui.Item] = [
            text(f"## {self.list_title()}"),
            separator(),
        ]

        if not page_posts:
            items.append(text("No open posts found."))
        else:
            for post in page_posts:
                self.add_post_to_items(items, post, role_options)

        items.append(text(f"Filter: {self.current_filter_text(role_options)}"))
        items.append(self.row(role_select))
        items.append(self.row(project_button, dev_button))

        self.set_items(
            self.container(*items, accent=discord.Colour.blurple()),
            self.pagination_row(total_pages, "networking_list"),
        )


    async def filter_by_role(self, interaction: discord.Interaction):
        selected_role = interaction.data["values"][0]

        if selected_role == "all":
            self.dev_role = None
        else:
            self.dev_role = selected_role

        self.page = 1
        await self.refresh(interaction)


    async def show_projects(self, interaction: discord.Interaction):
        self.post_type = "project"
        self.page = 1
        await self.refresh(interaction)


    async def show_devs(self, interaction: discord.Interaction):
        self.post_type = "dev"
        self.page = 1
        await self.refresh(interaction)





class MyPostsMenuView(UmaLayoutView):
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id


    async def send(self, interaction: discord.Interaction):
        await self.build_layout()
        await interaction.response.send_message(view=self, ephemeral=True)


    async def show(self, interaction: discord.Interaction):
        await self.build_layout()
        await self.edit_view(interaction)


    def make_dev_post_button(self):
        return self.button(
            "Dev Post",
            discord.ButtonStyle.primary,
            self.open_dev_post,
        )


    def make_project_posts_button(self):
        return self.button(
            "Project Posts",
            discord.ButtonStyle.primary,
            self.open_project_posts,
        )


    async def build_layout(self):
        dev_button = self.make_dev_post_button()
        projects_button = self.make_project_posts_button()

        self.set_container(
            self.text("## Manage Your Posts"),
            self.separator(),
            self.row(dev_button, projects_button),
            accent=discord.Colour.blurple(),
        )


    async def open_dev_post(self, interaction: discord.Interaction):
        if not await owner_can_manage(interaction, self.user_id):
            return

        post = await get_user_active_dev_post(
            self.guild_id,
            self.user_id,
        )

        if not post:
            message_view = MyPostsMessageView(
                self.bot,
                self.guild_id,
                self.user_id,
                "You do not have an active developer post.",
            )

            await message_view.show(interaction)
            return

        post_management_view = PostManagementView(
            self.bot,
            self.guild_id,
            self.user_id,
            str(post["_id"]),
        )

        await post_management_view.show_post(interaction, post)


    async def open_project_posts(self, interaction: discord.Interaction):
        if not await owner_can_manage(interaction, self.user_id):
            return

        project_posts_view = ProjectPostsSelectView(
            self.bot,
            self.guild_id,
            self.user_id,
        )

        await project_posts_view.show(interaction)






class MyPostsMessageView(UmaLayoutView):
    def __init__(self, bot, guild_id: int, user_id: int, message: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.message = message


    def make_back_button(self):
        return self.button(
            "Back",
            discord.ButtonStyle.secondary,
            self.go_back,
        )


    async def show(self, interaction: discord.Interaction):
        back_button = self.make_back_button()

        self.set_container(
            self.text("## Manage Your Posts"),
            self.text(self.message),
            self.separator(),
            self.row(back_button),
            accent=discord.Colour.blurple(),
        )

        await self.edit_view(interaction)


    async def go_back(self, interaction: discord.Interaction):
        if not await owner_can_manage(interaction, self.user_id):
            return

        menu_view = MyPostsMenuView(
            self.bot,
            self.guild_id,
            self.user_id,
        )

        await menu_view.show(interaction)






class ProjectPostsSelectView(UmaLayoutView):
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id


    async def show(self, interaction: discord.Interaction):
        project_posts = await get_user_project_posts(
            self.guild_id,
            self.user_id,
        )

        if not project_posts:
            message_view = MyPostsMessageView(
                self.bot,
                self.guild_id,
                self.user_id,
                "You do not have any project posts yet.",
            )

            await message_view.show(interaction)
            return

        project_select = self.make_project_select(project_posts)
        back_button = self.make_back_button()

        self.set_container(
            self.text("## Manage Project Posts"),
            self.separator(),
            self.row(project_select),
            self.row(back_button),
            accent=discord.Colour.blurple(),
        )

        await self.edit_view(interaction)


    def make_project_select(self, project_posts: list[dict]):
        return self.select(
            "Choose a project post...",
            project_post_select_options(project_posts),
            self.open_project_post,
        )


    def make_back_button(self):
        return self.button(
            "Back",
            discord.ButtonStyle.secondary,
            self.go_back,
        )


    async def open_project_post(self, interaction: discord.Interaction):
        if not await owner_can_manage(interaction, self.user_id):
            return

        post_id = interaction.data["values"][0]

        post = await get_user_networking_post(
            post_id,
            self.guild_id,
            self.user_id,
        )

        if not is_project_post(post):
            message_view = MyPostsMessageView(
                self.bot,
                self.guild_id,
                self.user_id,
                "That project post could not be found.",
            )

            await message_view.show(interaction)
            return

        post_management_view = PostManagementView(
            self.bot,
            self.guild_id,
            self.user_id,
            post_id,
        )

        await post_management_view.show_post(interaction, post)


    async def go_back(self, interaction: discord.Interaction):
        if not await owner_can_manage(interaction, self.user_id):
            return

        menu_view = MyPostsMenuView(
            self.bot,
            self.guild_id,
            self.user_id,
        )

        await menu_view.show(interaction)






class PostManagementView(UmaLayoutView):
    def __init__(self, bot, guild_id: int, user_id: int, post_id: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.post_id = post_id


    async def get_current_post(self, post: dict | None = None):
        if post:
            return post

        return await get_user_networking_post(
            self.post_id,
            self.guild_id,
            self.user_id,
        )


    async def get_post_from_interaction_user(self, interaction: discord.Interaction):
        return await get_user_networking_post(
            self.post_id,
            self.guild_id,
            interaction.user.id,
        )


    def post_management_title(self, post: dict) -> str:
        if is_project_post(post):
            return "Manage Project Post"

        return "Manage Dev Post"


    def make_edit_button(self):
        return self.button(
            "Edit",
            discord.ButtonStyle.primary,
            self.edit_post,
        )


    def make_status_button(self, status: str):
        if status == "closed":
            label = "Reopen"
            style = discord.ButtonStyle.success
        else:
            label = "Close"
            style = discord.ButtonStyle.secondary

        return self.button(label, style, self.toggle_status)


    def make_delete_button(self):
        return self.button(
            "Delete",
            discord.ButtonStyle.danger,
            self.confirm_delete,
        )


    def make_back_button(self):
        return self.button(
            "Back",
            discord.ButtonStyle.secondary,
            self.go_back,
        )


    def make_buttons_row(self, status: str):
        return self.row(
            self.make_edit_button(),
            self.make_status_button(status),
            self.make_delete_button(),
            self.make_back_button(),
        )


    async def post_content_items(self, post: dict):
        role_options = await get_dev_role_options(self.guild_id)
        role_label = format_dev_role(post["dev_role"], role_options)
        status = post.get("status", "open")

        items: list[discord.ui.Item] = [
            self.text(f"## {self.post_management_title(post)}"),
            self.text(f"Status: {format_post_status(status)}"),
            self.separator(),
        ]

        if is_project_post(post):
            items.append(
                self.text(f"Project: {project_display_name(post)}")
            )

        items.extend(
            [
                self.text(f"Role: {role_label}"),
                self.text(f"Created: {post_created_timestamp(post)}"),
                self.text(post["description"]),
            ]
        )

        if is_project_post(post):
            if post.get("game_link"):
                items.append(self.text(f"Game: {post['game_link']}"))

            if post.get("discord_invite"):
                items.append(self.text(f"Discord: {post['discord_invite']}"))

        elif post.get("portfolio_url"):
            items.append(self.text(f"Portfolio: {post['portfolio_url']}"))

        return items


    async def show_post(
        self,
        interaction: discord.Interaction,
        post: dict | None = None,
    ):
        if not await owner_can_manage(interaction, self.user_id):
            return

        current_post = await self.get_current_post(post)

        if not current_post:
            message_view = MyPostsMessageView(
                self.bot,
                self.guild_id,
                self.user_id,
                "That post could not be found.",
            )

            await message_view.show(interaction)
            return

        self.post_id = str(current_post["_id"])

        status = current_post.get("status", "open")
        items = await self.post_content_items(current_post)

        items.append(self.separator())
        items.append(self.make_buttons_row(status))

        colour = discord.Colour.green() if status == "open" else discord.Colour.red()

        self.set_container(*items, accent=colour)

        await self.edit_view(interaction)


    async def edit_post(self, interaction: discord.Interaction):
        from .modals import DevPostModal, ProjectPostModal

        post = await self.get_post_from_interaction_user(interaction)

        if not post:
            await interaction.response.send_message(
                "This post could not be found or is not yours.",
                ephemeral=True,
            )
            return

        if is_project_post(post):
            await interaction.response.send_modal(
                ProjectPostModal(
                    self.bot,
                    post["dev_role"],
                    post=post,
                    management_view=self,
                )
            )
            return

        await interaction.response.send_modal(
            DevPostModal(
                self.bot,
                post["dev_role"],
                post=post,
                management_view=self,
            )
        )


    async def toggle_status(self, interaction: discord.Interaction):
        post = await self.get_post_from_interaction_user(interaction)

        if not post:
            await interaction.response.send_message(
                "This post could not be found or is not yours.",
                ephemeral=True,
            )
            return

        updated_post = await set_post_status(
            self.post_id,
            self.guild_id,
            interaction.user.id,
            next_post_status(post),
        )

        if not updated_post:
            await interaction.response.send_message(
                "This post could not be updated.",
                ephemeral=True,
            )
            return

        await update_public_post(self.bot, updated_post)
        await self.show_post(interaction, updated_post)


    async def confirm_delete(self, interaction: discord.Interaction):
        post = await self.get_post_from_interaction_user(interaction)

        if not post:
            await interaction.response.send_message(
                "This post could not be found or is not yours.",
                ephemeral=True,
            )
            return

        delete_view = DeletePostConfirmView(
            self.bot,
            self.guild_id,
            self.user_id,
            self.post_id,
            is_project_post(post),
        )

        await delete_view.show(interaction)


    async def go_back(self, interaction: discord.Interaction):
        post = await self.get_post_from_interaction_user(interaction)

        if is_project_post(post):
            project_posts_view = ProjectPostsSelectView(
                self.bot,
                self.guild_id,
                self.user_id,
            )

            await project_posts_view.show(interaction)
            return

        menu_view = MyPostsMenuView(
            self.bot,
            self.guild_id,
            self.user_id,
        )

        await menu_view.show(interaction)






class DeletePostConfirmView(UmaLayoutView):
    def __init__(
        self,
        bot,
        guild_id: int,
        user_id: int,
        post_id: str,
        is_project: bool,
    ):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.post_id = post_id
        self.is_project = is_project


    def make_confirm_button(self):
        return self.button(
            "Confirm Delete",
            discord.ButtonStyle.danger,
            self.delete_post,
        )


    def make_cancel_button(self):
        return self.button(
            "Cancel",
            discord.ButtonStyle.secondary,
            self.cancel,
        )


    async def show(self, interaction: discord.Interaction):
        confirm_button = self.make_confirm_button()
        cancel_button = self.make_cancel_button()

        self.set_container(
            self.text("## Delete Post"),
            self.text("Are you sure you want to delete this post?"),
            self.separator(),
            self.row(confirm_button, cancel_button),
            accent=discord.Colour.red(),
        )

        await self.edit_view(interaction)


    async def delete_post(self, interaction: discord.Interaction):
        if not await owner_can_manage(interaction, self.user_id):
            return

        deleted_post = await delete_networking_post(
            self.post_id,
            self.guild_id,
            interaction.user.id,
        )

        if not deleted_post:
            await interaction.response.send_message(
                "This post could not be deleted. It may already be gone.",
                ephemeral=True,
            )
            return

        await delete_public_post(self.bot, deleted_post)

        if self.is_project:
            project_posts_view = ProjectPostsSelectView(
                self.bot,
                self.guild_id,
                self.user_id,
            )

            await project_posts_view.show(interaction)
            return

        message_view = MyPostsMessageView(
            self.bot,
            self.guild_id,
            self.user_id,
            "Your developer post was deleted.",
        )

        await message_view.show(interaction)


    async def cancel(self, interaction: discord.Interaction):
        post = await get_user_networking_post(
            self.post_id,
            self.guild_id,
            interaction.user.id,
        )

        post_management_view = PostManagementView(
            self.bot,
            self.guild_id,
            self.user_id,
            self.post_id,
        )

        await post_management_view.show_post(interaction, post)






class AddDevRoleModal(discord.ui.Modal):
    def __init__(self, guild_id: int, parent_view):
        super().__init__(title="Add dev role")
        self.guild_id = guild_id
        self.parent_view = parent_view

        self.role_name = discord.ui.TextInput(
            label="Role name",
            placeholder="Example: UI Designer",
            max_length=50,
        )

        self.add_item(self.role_name)


    def role_already_exists(
        self,
        role_options: list[tuple[str, str]],
        role_value: str,
    ) -> bool:
        for _, existing_value in role_options:
            if existing_value == role_value:
                return True

        return False


    async def send_error(
        self,
        interaction: discord.Interaction,
        message: str,
    ):
        await interaction.response.send_message(
            message,
            ephemeral=True,
        )


    async def on_submit(self, interaction: discord.Interaction):
        role_label = str(self.role_name.value).strip()
        role_value = dev_role_value(role_label)

        if not role_label or not role_value:
            await self.send_error(
                interaction,
                "Please provide a valid role name.",
            )
            return

        role_options = await get_dev_role_options(self.guild_id)

        if len(role_options) >= 25:
            await self.send_error(
                interaction,
                "Discord select menus can have up to 25 role options.",
            )
            return

        if self.role_already_exists(role_options, role_value):
            await self.send_error(
                interaction,
                f"`{role_label}` is already configured.",
            )
            return

        role_options.append((role_label, role_value))

        await guild_save_settings(
            self.guild_id,
            {
                "networking_dev_roles": serialize_dev_role_options(role_options),
            },
        )

        await self.parent_view.refresh()

        await interaction.response.send_message(
            f"`{role_label}` was added to networking dev roles.",
            ephemeral=True,
        )






class RemoveDevRoleSelect(discord.ui.Select):
    def __init__(
        self,
        guild_id: int,
        parent_view,
        role_options: list[tuple[str, str]],
    ):
        self.guild_id = guild_id
        self.parent_view = parent_view

        super().__init__(
            placeholder="Choose a dev role to remove...",
            options=role_select_options(role_options),
            min_values=1,
            max_values=1,
        )


    def remaining_roles(
        self,
        role_options: list[tuple[str, str]],
        removed_role: str,
    ) -> list[tuple[str, str]]:
        remaining = []

        for label, value in role_options:
            if value != removed_role:
                remaining.append((label, value))

        return remaining


    async def callback(self, interaction: discord.Interaction):
        selected_role = self.values[0]

        role_options = await get_dev_role_options(self.guild_id)

        if len(role_options) <= 1:
            await interaction.response.send_message(
                "Keep at least one dev role configured.",
                ephemeral=True,
            )
            return

        updated_roles = self.remaining_roles(
            role_options,
            selected_role,
        )

        removed_role = format_dev_role(
            selected_role,
            role_options,
        )

        await guild_save_settings(
            self.guild_id,
            {
                "networking_dev_roles": serialize_dev_role_options(updated_roles),
            },
        )

        await self.parent_view.refresh()

        await interaction.response.send_message(
            f"`{removed_role}` was removed from networking dev roles.",
            ephemeral=True,
        )






class NetworkingConfigureAvailableRolesView(UmaLayoutView):
    def __init__(self, guild_id: int, settings_view=None):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.settings_view = settings_view
        self.message: discord.Message | None = None


    async def send(self, interaction: discord.Interaction):
        await self.build_layout()
        await interaction.response.send_message(view=self, ephemeral=True)
        self.message = await interaction.original_response()


    async def refresh(self):
        if self.settings_view:
            await self.settings_view.refresh()

        if not self.message:
            return

        await self.build_layout()
        await self.message.edit(view=self)


    def role_lines(self, role_options: list[tuple[str, str]]) -> str:
        return "\n".join(
            f"- **{label}** (`{value}`)"
            for label, value in role_options
        )


    def make_add_button(self):
        return self.button(
            "Add role",
            discord.ButtonStyle.success,
            self.open_add_role_modal,
        )


    def make_remove_button(self):
        return self.button(
            "Remove role",
            discord.ButtonStyle.danger,
            self.open_remove_role_select,
        )


    def make_reset_button(self):
        return self.button(
            "Reset defaults",
            discord.ButtonStyle.secondary,
            self.reset_default_roles,
        )


    async def build_layout(self):
        role_options = await get_dev_role_options(self.guild_id)

        add_button = self.make_add_button()
        remove_button = self.make_remove_button()
        reset_button = self.make_reset_button()

        self.set_container(
            self.text("## Networking dev roles"),
            self.separator(),
            self.text(self.role_lines(role_options)),
            self.separator(),
            self.row(add_button, remove_button, reset_button),
            accent=discord.Colour.green(),
        )


    async def open_add_role_modal(self, interaction: discord.Interaction):
        add_role_modal = AddDevRoleModal(
            self.guild_id,
            self,
        )

        await interaction.response.send_modal(add_role_modal)


    async def open_remove_role_select(self, interaction: discord.Interaction):
        role_options = await get_dev_role_options(self.guild_id)

        if len(role_options) <= 1:
            await interaction.response.send_message(
                "Keep at least one dev role configured.",
                ephemeral=True,
            )
            return

        remove_role_view = discord.ui.View(timeout=120)
        remove_role_view.add_item(
            RemoveDevRoleSelect(
                self.guild_id,
                self,
                role_options,
            )
        )

        await interaction.response.send_message(
            "Choose which dev role to remove:",
            view=remove_role_view,
            ephemeral=True,
        )


    async def reset_default_roles(self, interaction: discord.Interaction):
        await guild_save_settings(
            self.guild_id,
            {
                "networking_dev_roles": serialize_dev_role_options(
                    DEFAULT_DEV_ROLE_OPTIONS
                ),
            },
        )

        await self.refresh()

        await interaction.response.send_message(
            "Networking dev roles were reset to defaults.",
            ephemeral=True,
        )
