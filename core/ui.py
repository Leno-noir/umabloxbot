import discord


DEFAULT_ITEMS_PER_PAGE = 5


def text(content: str) -> discord.ui.TextDisplay:
    return discord.ui.TextDisplay(content=content)


def separator(
    *,
    visible: bool = True,
    spacing: discord.SeparatorSpacing = discord.SeparatorSpacing.small,
) -> discord.ui.Separator:
    return discord.ui.Separator(
        visible=visible,
        spacing=spacing,
    )


def media(*items_or_urls) -> discord.ui.MediaGallery:
    items = [
        item
        if isinstance(item, discord.MediaGalleryItem)
        else discord.MediaGalleryItem(media=item)
        for item in items_or_urls
    ]
    return discord.ui.MediaGallery(*items)


def row(*items: discord.ui.Item) -> discord.ui.ActionRow:
    return discord.ui.ActionRow(*items)


def link_button(
    label: str,
    url: str,
    *,
    emoji: str | discord.PartialEmoji | None = None,
    disabled: bool = False,
) -> discord.ui.Button:
    return discord.ui.Button(
        label=label,
        url=url,
        style=discord.ButtonStyle.link,
        emoji=emoji,
        disabled=disabled,
    )


def container(
    *items: discord.ui.Item,
    accent: discord.Colour | None = None,
) -> discord.ui.Container:
    if accent is None:
        return discord.ui.Container(*items)

    return discord.ui.Container(*items, accent_colour=accent)


def roblox_profile_button(roblox_id: int | str) -> discord.ui.ActionRow:
    return row(
        link_button(
            "View Roblox profile",
            f"https://www.roblox.com/users/{roblox_id}/profile",
        )
    )


async def edit_view(interaction: discord.Interaction, view: discord.ui.LayoutView):
    if interaction.response.is_done():
        await interaction.edit_original_response(view=view)
        return

    await interaction.response.edit_message(view=view)


class UmaLayoutView(discord.ui.LayoutView):
    def text(self, content: str) -> discord.ui.TextDisplay:
        return text(content)

    def separator(
        self,
        *,
        visible: bool = True,
        spacing: discord.SeparatorSpacing = discord.SeparatorSpacing.small,
    ) -> discord.ui.Separator:
        return separator(visible=visible, spacing=spacing)

    def media(self, *items_or_urls) -> discord.ui.MediaGallery:
        return media(*items_or_urls)

    def button(
        self,
        label: str,
        style: discord.ButtonStyle,
        callback,
        *,
        custom_id: str | None = None,
        emoji: str | discord.PartialEmoji | None = None,
        disabled: bool = False,
    ) -> discord.ui.Button:
        button = discord.ui.Button(
            label=label,
            style=style,
            custom_id=custom_id,
            emoji=emoji,
            disabled=disabled,
        )
        button.callback = callback
        return button

    def link_button(
        self,
        label: str,
        url: str,
        *,
        emoji: str | discord.PartialEmoji | None = None,
        disabled: bool = False,
    ) -> discord.ui.Button:
        return link_button(label, url, emoji=emoji, disabled=disabled)

    def select(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        callback,
        *,
        custom_id: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> discord.ui.Select:
        select = discord.ui.Select(
            custom_id=custom_id,
            placeholder=placeholder,
            options=options,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
        )
        select.callback = callback
        return select

    def row(self, *items: discord.ui.Item) -> discord.ui.ActionRow:
        return row(*items)

    def container(
        self,
        *items: discord.ui.Item,
        accent: discord.Colour | None = None,
    ) -> discord.ui.Container:
        return container(*items, accent=accent)

    def set_items(self, *items: discord.ui.Item):
        self.clear_items()
        for item in items:
            self.add_item(item)

    def set_container(
        self,
        *items: discord.ui.Item,
        accent: discord.Colour | None = None,
    ):
        self.set_items(self.container(*items, accent=accent))

    async def edit_view(self, interaction: discord.Interaction):
        await edit_view(interaction, self)


class PaginatedLayoutView(UmaLayoutView):
    items_per_page = DEFAULT_ITEMS_PER_PAGE

    def __init__(self, *, page: int = 1, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.page = max(1, page)
        self._message: discord.Message | None = None

    def total_pages(self, total_items: int) -> int:
        return max(1, (total_items + self.items_per_page - 1) // self.items_per_page)

    def clamp_page(self, total_items: int) -> int:
        total_pages = self.total_pages(total_items)
        self.page = min(self.page, total_pages)
        return total_pages

    def page_offset(self) -> int:
        return (self.page - 1) * self.items_per_page

    def page_items(self, items: list):
        start = self.page_offset()
        return items[start : start + self.items_per_page]

    def pagination_row(self, total_pages: int, custom_id_prefix: str) -> discord.ui.ActionRow:
        previous_button = self.button(
            "Previous",
            discord.ButtonStyle.secondary,
            self._prev_page,
            custom_id=f"{custom_id_prefix}_prev_page",
            disabled=self.page <= 1,
        )
        next_button = self.button(
            "Next",
            discord.ButtonStyle.secondary,
            self._next_page,
            custom_id=f"{custom_id_prefix}_next_page",
            disabled=self.page >= total_pages,
        )
        return self.row(previous_button, next_button)

    async def send(self, interaction: discord.Interaction, ephemeral: bool = False):
        await self._rebuild_layout()
        if interaction.response.is_done():
            await interaction.followup.send(view=self, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(view=self, ephemeral=ephemeral)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction):
        await self._rebuild_layout()
        if interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.edit_message(view=self)

    async def _prev_page(self, interaction: discord.Interaction):
        self.page = max(1, self.page - 1)
        await self.refresh(interaction)

    async def _next_page(self, interaction: discord.Interaction):
        self.page += 1
        await self.refresh(interaction)
