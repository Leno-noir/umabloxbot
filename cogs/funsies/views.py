from __future__ import annotations

import random

import discord
from bson import ObjectId

from core.config import Colors
from core.ui import PaginatedLayoutView, UmaLayoutView
from db.funsies import (
    fact_add,
    fact_delete,
    fact_list,
    fact_toggle_active,
    funsies_get_gacha_rarity_names,
    funsies_get_settings,
    funsies_save_settings,
    funsies_set_gacha_rarity_names,
    funsies_toggle_setting,
    funsies_set_gacha_rarity_chances,
    inventory_get_selected,
    inventory_list,
    inventory_set_selected,
    quote_add,
    quote_delete,
    quote_list,
    quote_toggle_active,
    uma_add_character,
    uma_character_exists_name_overall,
    uma_delete_character,
    uma_list_characters,
    uma_list_rarities,
    uma_search_by_name,
    uma_toggle_active,
    uma_update_character,
    rarity_id_from_value,
    rarity_name_from_id,
)
from .utils import build_inventory_line, build_uma_summary_label, format_time_ms


def _format_bool(value: bool) -> str:
    return "Yes" if value else "No"


def _format_status(value: bool) -> str:
    return "Active" if value else "Inactive"


def _object_id(value: str | ObjectId) -> ObjectId:
    return value if isinstance(value, ObjectId) else ObjectId(str(value))


class FunsiesTextModal(discord.ui.Modal):
    def __init__(self, *, title: str, guild_id: int, parent_view):
        super().__init__(title=title)
        self.guild_id = guild_id
        self.parent_view = parent_view


class QuoteAddModal(FunsiesTextModal, title="Add Quote"):
    character = discord.ui.TextInput(label="Character", placeholder="Kitasan Black", max_length=100)
    text = discord.ui.TextInput(
        label="Quote Text",
        placeholder="Harikitte ikou!",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(self, guild_id: int, parent_view):
        super().__init__(title="Add Quote", guild_id=guild_id, parent_view=parent_view)

    async def on_submit(self, interaction: discord.Interaction):
        await quote_add(
            self.guild_id,
            self.character.value.strip(),
            self.text.value.strip(),
            active=True,
        )
        await interaction.response.send_message("Quote added.", ephemeral=True)
        await self.parent_view.refresh(interaction)


class FactAddModal(FunsiesTextModal, title="Add Fact"):
    text = discord.ui.TextInput(
        label="Fact Text",
        placeholder="Daiwa Scarlet has never ended a race lower than 2nd",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )
    category = discord.ui.TextInput(
        label="Category",
        placeholder="Racing",
        required=False,
        max_length=100,
    )

    def __init__(self, guild_id: int, parent_view):
        super().__init__(title="Add Fact", guild_id=guild_id, parent_view=parent_view)

    async def on_submit(self, interaction: discord.Interaction):
        category_value = self.category.value.strip() or None
        await fact_add(
            self.guild_id,
            self.text.value.strip(),
            category=category_value,
            active=True,
        )
        await interaction.response.send_message("Fact added.", ephemeral=True)
        await self.parent_view.refresh(interaction)


class UmaAddModal(FunsiesTextModal, title="Add Uma"):
    name = discord.ui.TextInput(label="Name", placeholder="Kitasan Black", max_length=100)
    rarity = discord.ui.TextInput(label="Rarity ID", placeholder="1", max_length=2)
    image_url = discord.ui.TextInput(
        label="Image URL",
        placeholder="https://...",
        required=False,
        max_length=500,
    )
    overall = discord.ui.TextInput(label="Overall", placeholder="91", max_length=3)

    def __init__(self, guild_id: int, parent_view, *, current_rarities: list[str] | None = None):
        super().__init__(title="Add Uma", guild_id=guild_id, parent_view=parent_view)
        rarities = ", ".join(str(r) for r in current_rarities or []) or "1, 2, 3, 4"
        self.rarity.placeholder = f"Use 1, 2, 3, or 4. Current: {rarities}"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            overall_value = int(self.overall.value.strip())
            rarity_value = rarity_id_from_value(self.rarity.value.strip())
        except ValueError:
            await interaction.response.send_message("Overall must be a number.", ephemeral=True)
            return

        if rarity_value is None:
            await interaction.response.send_message("Rarity must be 1, 2, 3, or 4.", ephemeral=True)
            return

        if overall_value < 0:
            await interaction.response.send_message("Overall must be zero or greater.", ephemeral=True)
            return

        duplicate_exists = await uma_character_exists_name_overall(self.name.value.strip(), overall_value)
        if duplicate_exists:
            await interaction.response.send_message(
                "An Uma with this same name and overall already exists.",
                ephemeral=True,
            )
            return

        await uma_add_character(
            self.guild_id,
            self.name.value.strip(),
            rarity_value,
            self.image_url.value.strip() or None,
            overall_value,
            active=True,
        )
        await interaction.response.send_message("Uma added.", ephemeral=True)
        await self.parent_view.refresh(interaction)


class UmaEditModal(FunsiesTextModal, title="Edit Uma"):
    name = discord.ui.TextInput(label="Name", max_length=100)
    rarity = discord.ui.TextInput(label="Rarity ID", max_length=2)
    image_url = discord.ui.TextInput(label="Image URL", required=False, max_length=500)
    overall = discord.ui.TextInput(label="Overall", max_length=3)

    def __init__(self, guild_id: int, parent_view, uma: dict):
        super().__init__(title="Edit Uma", guild_id=guild_id, parent_view=parent_view)
        self.uma_id = uma["_id"]
        self.name.default = str(uma.get("name", ""))
        self.rarity.default = str(uma.get("rarity", ""))
        self.image_url.default = str(uma.get("image_url") or "")
        self.overall.default = str(uma.get("overall", ""))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            overall_value = int(self.overall.value.strip())
            rarity_value = rarity_id_from_value(self.rarity.value.strip())
        except ValueError:
            await interaction.response.send_message("Overall must be a number.", ephemeral=True)
            return

        if rarity_value is None:
            await interaction.response.send_message("Rarity must be a numeric ID.", ephemeral=True)
            return
        if overall_value < 0:
            await interaction.response.send_message("Overall must be zero or greater.", ephemeral=True)
            return

        name = self.name.value.strip()
        if await uma_character_exists_name_overall(name, overall_value, exclude_id=self.uma_id):
            await interaction.response.send_message(
                "Another Uma already has this same name and overall.",
                ephemeral=True,
            )
            return

        updated = await uma_update_character(
            self.guild_id,
            self.uma_id,
            name=name,
            rarity=rarity_value,
            image_url=self.image_url.value.strip() or None,
            overall=overall_value,
        )
        if not updated:
            await interaction.response.send_message("That Uma no longer exists.", ephemeral=True)
            return

        await interaction.response.send_message("Uma updated.", ephemeral=True)
        self.parent_view.items = await uma_list_characters(self.guild_id)
        await self.parent_view._rebuild_layout()
        if self.parent_view._message is not None:
            await self.parent_view._message.edit(view=self.parent_view)
        if self.parent_view.parent_view:
            await self.parent_view.parent_view.refresh(interaction)


class DailyLimitModal(FunsiesTextModal, title="Daily Gacha Limit"):
    limit = discord.ui.TextInput(label="Limit", placeholder="50", max_length=3)

    def __init__(self, guild_id: int, parent_view):
        super().__init__(title="Daily Gacha Limit", guild_id=guild_id, parent_view=parent_view)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit_value = int(self.limit.value.strip())
        except ValueError:
            await interaction.response.send_message("Limit must be a number.", ephemeral=True)
            return

        if limit_value < 1:
            await interaction.response.send_message("Limit must be at least 1.", ephemeral=True)
            return

        await funsies_save_settings(self.guild_id, {"daily_gacha_limit": limit_value})
        saved_settings = await funsies_get_settings(self.guild_id)
        saved_limit = int(saved_settings.get("daily_gacha_limit", limit_value))
        await interaction.response.send_message(
            f"Global daily gacha limit updated to {saved_limit}.",
            ephemeral=True,
        )
        await self.parent_view.refresh(interaction)


class GachaRarityChancesModal(FunsiesTextModal, title="Gacha Rarity Chances"):
    rarity1 = discord.ui.TextInput(label="Rarity 1 %", placeholder="60", max_length=3)
    rarity2 = discord.ui.TextInput(label="Rarity 2 %", placeholder="25", max_length=3)
    rarity3 = discord.ui.TextInput(label="Rarity 3 %", placeholder="15", max_length=3)
    rarity4 = discord.ui.TextInput(label="Rarity 4 %", placeholder="1", max_length=3)

    def __init__(self, guild_id: int, parent_view):
        super().__init__(title="Gacha Rarity Chances", guild_id=guild_id, parent_view=parent_view)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            chances = {
                "1": max(0, int(self.rarity1.value.strip())),
                "2": max(0, int(self.rarity2.value.strip())),
                "3": max(0, int(self.rarity3.value.strip())),
                "4": max(0, int(self.rarity4.value.strip())),
            }
        except ValueError:
            await interaction.response.send_message("All chance fields must be numbers.", ephemeral=True)
            return

        if sum(chances.values()) <= 0:
            await interaction.response.send_message("At least one rarity chance must be greater than zero.", ephemeral=True)
            return

        await funsies_set_gacha_rarity_chances(self.guild_id, chances)
        await interaction.response.send_message("Global gacha rarity chances updated.", ephemeral=True)
        await self.parent_view.refresh(interaction)


class GachaRarityNamesModal(FunsiesTextModal, title="Gacha Rarity Names"):
    rarity1 = discord.ui.TextInput(label="Rarity 1 name", placeholder="Name stored in MongoDB", max_length=30)
    rarity2 = discord.ui.TextInput(label="Rarity 2 name", placeholder="Name stored in MongoDB", max_length=30)
    rarity3 = discord.ui.TextInput(label="Rarity 3 name", placeholder="Name stored in MongoDB", max_length=30)
    rarity4 = discord.ui.TextInput(label="Rarity 4 name", placeholder="Name stored in MongoDB", max_length=30)

    def __init__(self, guild_id: int, parent_view):
        super().__init__(title="Gacha Rarity Names", guild_id=guild_id, parent_view=parent_view)

    async def on_submit(self, interaction: discord.Interaction):
        names = {
            "1": self.rarity1.value.strip(),
            "2": self.rarity2.value.strip(),
            "3": self.rarity3.value.strip(),
            "4": self.rarity4.value.strip(),
        }
        await funsies_set_gacha_rarity_names(self.guild_id, names)
        await interaction.response.send_message("Global gacha rarity names updated.", ephemeral=True)
        await self.parent_view.refresh(interaction)


class GachaInfoView(UmaLayoutView):
    def __init__(
        self,
        *,
        active_umas_count: int,
        available_lines: list[str],
        rarity_lines: list[str],
    ):
        super().__init__(timeout=None)
        rarity_text = "\n".join(rarity_lines) if rarity_lines else "None"
        available_text = "\n".join(available_lines) if available_lines else "None"
        self.set_container(
            self.text("## Gacha Pool Info"),
            self.text(f"Available Umas: {active_umas_count}"),
            self.separator(),
            self.text("**Rarity Chances:**"),
            self.text(rarity_text),
            self.separator(),
            self.text("**Available in Pool:**"),
            self.text(available_text),
            accent=discord.Colour.blue(),
        )


class QuoteCardView(UmaLayoutView):
    def __init__(self, character: str, text_value: str):
        super().__init__(timeout=None)
        self.set_container(
            self.text(f"## :speech_balloon:    {character}"),
            self.text(text_value),
            accent=discord.Colour.blurple(),
        )


class FactCardView(UmaLayoutView):
    def __init__(self, text_value: str, category: str | None = None):
        super().__init__(timeout=None)
        title = "Uma Fact"
        self.set_container(
            self.text(f"## :book:    {title}"),
            self.text(text_value),
            self.text(f"> *{category}*") if category else None,
            accent=discord.Colour.green(),
        )


class GachaResultView(UmaLayoutView):
    def __init__(self, uma: dict, user_id: int, user_mention: str, rarity_names: dict[str, str] | None = None):
        super().__init__(timeout=None)
        rarity_id = int(uma.get("rarity", 1) or 1)
        rarity_label = str(
            rarity_name_from_id(rarity_id, rarity_names)
            or uma.get("rarity_label")
            or uma.get("rarity_name")
            or rarity_id
        )
        accent_map = {
            4: discord.Colour(9437439),
            3: discord.Colour(15277667),
            2: discord.Colour(15844367),
            1: discord.Colour(10070709),
        }
        title_map = {
            4: [
                f"🌟 A LEGEND STEPS ONTO THE TRACK! Trainer {user_mention} is speechless!",
                "🏇 THE STARTING GATES HAVE OPENED FOR A TRUE LEGEND!",
                "👑 A NEW STAR SHINES OVER THE TRACEN ACADEMY!",
                "🏆 A FUTURE URA CHAMPION HAS ARRIVED!",
                f"🌈 DESTINY HAS CHOSEN {user_mention}! An extraordinary Uma joins the team!",
                f"💎 AN EXTRAORDINARY UMA JOINS {user_mention}'S TEAM!",
                "🏅 THE NEXT RACE JUST GOT A LOT MORE EXCITING!",
                "🌟 A TRUE STAR OF THE TRACK HAS ARRIVED!",
            ],
            3: [
                f"AN ELITE UMA HAS ARRIVED! Trainer {user_mention} is in shambles!",
                f"JACKPOT!!! {user_mention} hit the jackpot and pulled an...",
                f"THE ACADEMY IS SHAKING! {user_mention} just pulled...",
                f"INCREDIBLE LUCK! {user_mention} just recruited...",
                f"WHAT A PULL! {user_mention} just got {rarity_label}!",
            ],
            2: [
                f"A fearsome uma has joined {user_mention}'s team!",
                f"Heya, nice pull {user_mention}!",
                f"WOAH! This uma looks promising! Good job {user_mention}!",
            ],
            1: [
                f"A new trainee has joined {user_mention}'s team!",
                f"Congrats {user_mention}! you pulled a new uma!",
                f"Welcome to the team! {user_mention} pulled",
            ],
        }
        accent = accent_map.get(rarity_id, discord.Colour.blue())
        title = random.choice(title_map.get(rarity_id, [f"{user_mention} pulled a new Uma!"]))
        image_url = uma.get("image_url")
        parts: list[discord.ui.Item] = [
            self.text(f"# {title}"),
            self.separator(),
        ]
        if image_url:
            parts.append(self.media(image_url))
        parts.extend(
            [
                self.text(f"## {':star2:' if rarity_id == 4 else ':star:' * rarity_id} **__{rarity_label}__**"),
                self.text(f"### {uma.get('name', 'Unknown')}"),
                self.text(f"### Overall • {uma.get('overall', 'Unknown')}"),
            ]
        )
        self.set_container(*parts, accent=accent)


class GachaResultsView(UmaLayoutView):
    def __init__(self, results: list[dict], user_id: int, user_mention: str, rarity_names: dict[str, str] | None = None):
        super().__init__(timeout=None)
        accent_map = {
            3: discord.Colour(15277667),
            2: discord.Colour(15844367),
            1: discord.Colour(10070709),
        }
        title_map = {
            3: [
                f"JACKPOT!!! {user_mention} hit the jackpot and pulled {len(results)} elite umas!",
                f"THE ACADEMY IS SHAKING! {user_mention} just pulled a premium batch!",
                f"INCREDIBLE LUCK! {user_mention} just recruited {len(results)} elite umas!",
            ],
            2: [
                f"A fearsome batch has joined {user_mention}'s team!",
                f"Heya, nice multi-pull {user_mention}!",
                f"WOAH! {user_mention} pulled a promising batch!",
            ],
            1: [
                f"A new batch of trainees joined {user_mention}'s team!",
                f"Congrats {user_mention}! you pulled new umas!",
                f"Welcome to the team! {user_mention} got a fresh batch.",
            ],
        }
        highest_rarity = max((int(result["uma"].get("rarity", 1) or 1) for result in results), default=1)
        accent = accent_map.get(highest_rarity, discord.Colour.blue())
        title = random.choice(title_map.get(highest_rarity, [f"{user_mention} pulled new umas!"]))
        parts: list[discord.ui.Item] = [
            self.text(f"# {title}"),
            self.separator(),
            self.text(f"### {len(results)} pull{'s' if len(results) != 1 else ''}"),
        ]
        for index, result in enumerate(results, start=1):
            uma = result["uma"]
            rarity_label = str(
                rarity_name_from_id(uma["rarity"], rarity_names)
                or uma.get("rarity_label")
                or uma.get("rarity_name")
                or uma["rarity"]
            )
            parts.append(self.text(f"## {index}. {rarity_label} - {uma.get('name', 'Unknown')}"))
            parts.append(self.text(f"### Overall • {uma.get('overall', 'Unknown')}"))
            if index != len(results):
                parts.append(self.separator())
        self.set_container(*parts, accent=accent)


class RaceResultView(UmaLayoutView):
    def __init__(
        self,
        *,
        winner_user: discord.Member | discord.User,
        winner_label: str,
        winner_pick: dict,
        loser_user: discord.Member | discord.User,
        loser_label: str,
        loser_pick: dict,
        winner_time: int,
        loser_time: int,
        margin: str,
    ):
        super().__init__(timeout=None)
        winner_display = winner_label
        loser_display = loser_label
        time_diff = abs(loser_time - winner_time)
        short_margin_titles = [
            "PHOTO FINISH!",
            "THAT WAS INCREDIBLY CLOSE!",
            "EVERY MILLISECOND COUNTED!",
            "WHAT A THRILLING FINISH!",
            "A RACE TO REMEMBER!",
        ]

        player_titles = [
            f"{winner_display} TAKES THE WIN!",
            f"{winner_display} CROSSES THE FINISH LINE FIRST!",
            f"{winner_display}'S UMA WAS UNSTOPPABLE!",
            f"{loser_display} PUT UP A GREAT FIGHT!",
            f"{winner_display} CLAIMS ANOTHER VICTORY!",
        ]
        large_margin_titles = [
            "VICTORY!",
            "WHAT A PERFORMANCE!",
            "AN AMAZING RACE!",
            "WHAT A FINISH!",
            "THE CROWD GOES WILD!",
            "AN UNFORGETTABLE VICTORY!",
        ]
        if time_diff <= 250:
            headline = random.choice(short_margin_titles)
        elif time_diff <= 1200:
            headline = random.choice(player_titles)
        else:
            headline = random.choice(large_margin_titles)
        margin_line = f"***Margin:** {margin}*"
        media_items = []
        if winner_pick.get("image_url"):
            media_items.append(winner_pick["image_url"])
        if loser_pick.get("image_url"):
            media_items.append(loser_pick["image_url"])
        media_block = self.media(*media_items) if media_items else None
        parts: list[discord.ui.Item] = [
            self.text(f"# **🏁 RACE BETWEEN {winner_display} and {loser_display}!!**"),
            self.separator(),
            self.text(f"## 🥇 **{headline}**"),
        ]
        if media_block:
            parts.append(media_block)
            parts.extend(
                [
                    self.separator(),
                    self.text(f"### **🥇Victory • {winner_display} - __{winner_pick['uma_name']} ({winner_pick['overall']})__**"),
                    self.text(f"Time: {format_time_ms(winner_time)}"),
                    self.text(f"### **🥈 Defeat • {loser_display} - __{loser_pick['uma_name']} ({loser_pick['overall']})__**"),
                    self.text(f"Time: {format_time_ms(loser_time)}"),
                    self.text(margin_line),
                ]
            )
        parts.append(self.text(f"**__{winner_pick['uma_name']}__** has gained **+1 Wins**"))
        self.set_container(*parts, accent=discord.Colour.yellow())


class FunsiesPagedChoiceView(PaginatedLayoutView):
    items_per_page = 10
    title_text = "Choose an item"
    empty_text_text = "Nothing here yet."
    accent_color = discord.Colour.blurple()

    def __init__(self, guild_id: int, parent_view=None, *, page: int = 1, timeout: float | None = 180):
        super().__init__(page=page, timeout=timeout)
        self.guild_id = guild_id
        self.parent_view = parent_view
        self._message: discord.Message | None = None
        self._select: discord.ui.Select | None = None
        self.items: list[dict] = []

    def build_line(self, item: dict, index: int) -> str:
        return f"{index}. {item.get('name', 'Unknown')}"

    def build_option(self, item: dict, index: int) -> discord.SelectOption:
        return discord.SelectOption(
            label=str(item.get("name", "Unknown"))[:100],
            value=str(item["_id"]),
            description=None,
        )

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        raise NotImplementedError

    async def _handle_select(self, interaction: discord.Interaction):
        if not self._select or not self._select.values:
            await interaction.response.defer()
            return

        picked_id = _object_id(self._select.values[0])
        item = next((entry for entry in self.items if entry["_id"] == picked_id), None)
        if not item:
            await interaction.response.send_message("That item is no longer available.", ephemeral=True)
            return

        await self.on_pick(interaction, item)

    async def _rebuild_layout(self):
        total_pages = self.clamp_page(len(self.items))
        page_items = self.page_items(self.items)

        body_lines = [f"## {self.title_text}"]

        if not page_items:
            body_lines.append(self.empty_text_text)
            self.set_container(self.text("\n\n".join(body_lines)), accent=self.accent_color)
            return

        self._select = discord.ui.Select(
            placeholder="Choose an item...",
            options=[self.build_option(item, index) for index, item in enumerate(page_items, start=1)],
            min_values=1,
            max_values=1,
        )
        self._select.callback = self._handle_select

        for index, item in enumerate(page_items, start=self.page_offset() + 1):
            body_lines.append(self.build_line(item, index))

        components: list[discord.ui.Item] = [
            self.container(self.text("\n\n".join(body_lines)), accent=self.accent_color),
            self.row(self._select),
        ]
        if total_pages > 1:
            components.append(self.pagination_row(total_pages, self.__class__.__name__.lower()))

        self.set_items(*components)

    async def send(self, interaction: discord.Interaction, ephemeral: bool = True):
        await self._rebuild_layout()
        if interaction.response.is_done():
            await interaction.followup.send(view=self, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(view=self, ephemeral=ephemeral)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        await self._rebuild_layout()
        if interaction is not None and not interaction.response.is_done() and interaction.message is not None:
            await interaction.response.edit_message(view=self)
        elif interaction is not None and interaction.message is not None:
            await interaction.message.edit(view=self)
        elif interaction is not None and interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        elif self._message is not None:
            await self._message.edit(view=self)


class QuoteRemoveView(FunsiesPagedChoiceView):
    title_text = "Remove Quote"
    empty_text_text = "No quotes configured yet."

    def build_line(self, item: dict, index: int) -> str:
        status = _format_status(item.get("active", True))
        return f"{index}. {item['character']} | {status}"

    def build_option(self, item: dict, index: int) -> discord.SelectOption:
        status = "Active" if item.get("active", True) else "Inactive"
        return discord.SelectOption(
            label=f"{item['character']} - {status}"[:100],
            value=str(item["_id"]),
        )

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await quote_delete(self.guild_id, item["_id"])
        await interaction.response.send_message("Quote removed.", ephemeral=True)
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self.refresh(interaction)


class QuoteToggleView(QuoteRemoveView):
    title_text = "Toggle Quote Status"
    empty_text_text = "No quotes configured yet."

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await quote_toggle_active(self.guild_id, item["_id"])
        await interaction.response.send_message("Quote updated.", ephemeral=True)
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self.refresh(interaction)


class FactRemoveView(FunsiesPagedChoiceView):
    title_text = "Remove Fact"
    empty_text_text = "No facts configured yet."

    def build_line(self, item: dict, index: int) -> str:
        status = _format_status(item.get("active", True))
        return f"{index}. {item['text'][:60]} | {status}"

    def build_option(self, item: dict, index: int) -> discord.SelectOption:
        status = "Active" if item.get("active", True) else "Inactive"
        return discord.SelectOption(
            label=f"Fact {index} - {status}"[:100],
            value=str(item["_id"]),
        )

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await fact_delete(self.guild_id, item["_id"])
        await interaction.response.send_message("Fact removed.", ephemeral=True)
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self.refresh(interaction)


class FactToggleView(FactRemoveView):
    title_text = "Toggle Fact Status"

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await fact_toggle_active(self.guild_id, item["_id"])
        await interaction.response.send_message("Fact updated.", ephemeral=True)
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self.refresh(interaction)


class UmaToggleView(FunsiesPagedChoiceView):
    title_text = "Toggle Uma Status"
    empty_text_text = "No Umas configured yet."

    def build_line(self, item: dict, index: int) -> str:
        status = _format_status(item.get("active", True))
        return f"{index}. {build_uma_summary_label(item)} | {status}"

    def build_option(self, item: dict, index: int) -> discord.SelectOption:
        status = "Active" if item.get("active", True) else "Inactive"
        return discord.SelectOption(
            label=f"{item['name']} - {status}"[:100],
            value=str(item["_id"]),
        )

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await uma_toggle_active(self.guild_id, item["_id"])
        await interaction.response.send_message("Uma status updated.", ephemeral=True)
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self.refresh(interaction)


class UmaEditView(UmaToggleView):
    title_text = "Edit Uma"

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await interaction.response.send_modal(UmaEditModal(self.guild_id, self, item))


class UmaRemoveView(UmaToggleView):
    title_text = "Remove Uma"

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        removed = await uma_delete_character(self.guild_id, item["_id"])
        if not removed:
            await interaction.response.send_message(
                "This Uma belongs to at least one player and cannot be removed. Disable it instead.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Uma removed.", ephemeral=True)
        self.items = await uma_list_characters(self.guild_id)
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self.refresh(interaction)


class RaceSelectView(FunsiesPagedChoiceView):
    title_text = "Select your Race Uma"
    empty_text_text = "You do not have any Umas yet."

    def __init__(self, guild_id: int, user_id: int, parent_view=None, *, page: int = 1):
        super().__init__(guild_id, parent_view, page=page, timeout=180)
        self.user_id = user_id

    def build_line(self, item: dict, index: int) -> str:
        selected = item.get("_id") == getattr(self, "_selected_id", None)
        rarity_label = item.get("rarity_label") or item.get("rarity_name") or str(item.get("rarity", ""))
        stars = ":star:" * max(1, int(item.get("rarity", 1) or 1))
        name = f"__{item['uma_name']}__" if selected else item["uma_name"]
        return f"{index}. {name} | {stars} {rarity_label} | Overall {item['overall']}"

    def build_option(self, item: dict, index: int) -> discord.SelectOption:
        selected = item.get("_id") == getattr(self, "_selected_id", None)
        stars = ":star:" * max(1, int(item.get("rarity", 1) or 1))
        label = f"{'Selected - ' if selected else ''}{item['uma_name']}"
        return discord.SelectOption(
            label=label[:100],
            value=str(item["_id"]),
            description=f"{stars} {item.get('rarity_label') or item.get('rarity_name') or item['rarity']} | Overall {item['overall']}"[:100],
        )

    async def _rebuild_layout(self):
        selected_doc = await inventory_get_selected(self.guild_id, self.user_id)
        self._selected_id = selected_doc.get("selected_inventory_uma_id") if selected_doc else None
        await super()._rebuild_layout()

    async def on_pick(self, interaction: discord.Interaction, item: dict):
        await inventory_set_selected(self.guild_id, self.user_id, item["_id"])
        await interaction.response.send_message(
            f"{item['uma_name']} is now your selected Uma for races.",
            ephemeral=True,
        )
        if self.parent_view:
            await self.parent_view.refresh(interaction)
        await self._rebuild_layout()
        if self._message is not None:
            await self._message.edit(view=self)


class InventoryView(PaginatedLayoutView):
    items_per_page = 5
    title_text = "Inventory"

    def __init__(self, guild_id: int, user: discord.Member | discord.User, *, page: int = 1):
        super().__init__(page=page, timeout=180)
        self.guild_id = guild_id
        self.user = user
        self.items: list[dict] = []
        self._message: discord.Message | None = None

    async def _rebuild_layout(self):
        self.items = await inventory_list(self.guild_id, self.user.id)
        total_pages = self.clamp_page(len(self.items))
        page_items = self.page_items(self.items)

        body_lines: list[str] = []
        avatar_url = self.user.display_avatar.url

        if not page_items:
            self.set_container(
                self.media(avatar_url),
                self.text(f"**Inventory - {self.user.display_name}**"),
                self.text("No Umas found in this inventory yet."),
                accent=discord.Colour.greyple(),
            )
            return

        for index, item in enumerate(page_items, start=self.page_offset() + 1):
            body_lines.append(build_inventory_line(item, index))

        components: list[discord.ui.Item] = [
            self.container(
                self.media(avatar_url),
                self.text(f"**Inventory - {self.user.display_name}**"),
                self.text("\n\n".join(body_lines)),
                accent=Colors.BLUE,
            ),
        ]
        if total_pages > 1:
            components.append(self.pagination_row(total_pages, "inventory"))
        self.set_items(*components)

    async def send(self, interaction: discord.Interaction, ephemeral: bool = True):
        await self._rebuild_layout()
        if interaction.response.is_done():
            await interaction.followup.send(view=self, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(view=self, ephemeral=ephemeral)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        await self._rebuild_layout()
        if interaction is not None and not interaction.response.is_done() and interaction.message is not None:
            await interaction.response.edit_message(view=self)
        elif interaction is not None and interaction.message is not None:
            await interaction.message.edit(view=self)
        elif interaction is not None and interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        elif self._message is not None:
            await self._message.edit(view=self)


class LeaderboardView(PaginatedLayoutView):
    items_per_page = 10

    def __init__(self, entries: list[dict], *, page: int = 1):
        super().__init__(page=page, timeout=180)
        self.entries = entries
        self._message: discord.Message | None = None

    def _rank_label(self, rank: int) -> str:
        if rank == 1:
            return "1st"
        if rank == 2:
            return "2nd"
        if rank == 3:
            return "3rd"
        return f"{rank}th"

    async def _rebuild_layout(self):
        total_pages = self.clamp_page(len(self.entries))
        page_entries = self.page_items(self.entries)

        if not page_entries:
            self.set_container(
                self.text("## Uma Race Leaderboard"),
                self.text("No race results yet."),
                accent=Colors.YELLOW,
            )
            return

        leader = self.entries[0]
        page_label = f"Page {self.page}/{total_pages}" if total_pages > 1 else "Top race records"
        body_lines = [
            "## Uma Race Leaderboard",
            f"**Record:** {leader['user_label']} with **{leader['uma_name']}**",
            f"**Best time:** {format_time_ms(leader['time_ms'])}",
            f"*{page_label}*",
        ]

        podium_lines: list[str] = []
        table_lines: list[str] = []
        for entry in page_entries:
            line = (
                f"**{self._rank_label(entry['rank'])}** | {entry['user_label']} | "
                f"{entry['uma_name']} | `{format_time_ms(entry['time_ms'])}` | "
                f"{entry['wins']} win{'s' if entry['wins'] != 1 else ''}"
            )
            if entry["rank"] <= 3:
                podium_lines.append(line)
            else:
                table_lines.append(line)

        if podium_lines:
            body_lines.append("### Podium")
            body_lines.extend(podium_lines)
        if table_lines:
            body_lines.append("### Chase Pack")
            body_lines.extend(table_lines)

        components: list[discord.ui.Item] = [
            self.container(self.text("\n\n".join(body_lines)), accent=Colors.YELLOW),
        ]
        if total_pages > 1:
            components.append(self.pagination_row(total_pages, "leaderboard"))
        self.set_items(*components)

    async def send(self, interaction: discord.Interaction, ephemeral: bool = False):
        await self._rebuild_layout()
        if interaction.response.is_done():
            await interaction.followup.send(view=self, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(view=self, ephemeral=ephemeral)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        await self._rebuild_layout()
        if interaction is not None and not interaction.response.is_done() and interaction.message is not None:
            await interaction.response.edit_message(view=self)
        elif interaction is not None and interaction.message is not None:
            await interaction.message.edit(view=self)
        elif interaction is not None and interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        elif self._message is not None:
            await self._message.edit(view=self)


class AllUmasView(PaginatedLayoutView):
    items_per_page = 10
    title_text = "All Umas"
    accent_color = Colors.BLUE

    def __init__(self, umas: list[dict], *, page: int = 1, title: str = "All Umas"):
        super().__init__(page=page, timeout=180)
        self.umas = umas
        self.title_text = title
        self._message: discord.Message | None = None

    def _stars_for_rarity(self, rarity: int | str | None) -> str:
        rarity_id = int(rarity or 1)
        if rarity_id == 4:
            return ":star2:"
        return ":star:" * max(1, rarity_id)

    async def _rebuild_layout(self):
        total_pages = self.clamp_page(len(self.umas))
        page_items = self.page_items(self.umas)

        body_lines = [f"## {self.title_text}"]
        if not page_items:
            body_lines.append("No Umas found.")
            self.set_container(self.text("\n\n".join(body_lines)), accent=self.accent_color)
            return

        for index, item in enumerate(page_items, start=self.page_offset() + 1):
            body_lines.append(
                f"{index}. {item['name']}\n"
                f"{self._stars_for_rarity(item.get('rarity'))} {item.get('rarity_label') or item.get('rarity_name') or item['rarity']} | Overall {item['overall']}"
            )

        components: list[discord.ui.Item] = [
            self.container(self.text("\n\n".join(body_lines)), accent=self.accent_color),
        ]
        if total_pages > 1:
            components.append(self.pagination_row(total_pages, "allumas"))
        self.set_items(*components)

    async def send(self, interaction: discord.Interaction, ephemeral: bool = True):
        await self._rebuild_layout()
        if interaction.response.is_done():
            await interaction.followup.send(view=self, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(view=self, ephemeral=ephemeral)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        await self._rebuild_layout()
        if interaction is not None and not interaction.response.is_done() and interaction.message is not None:
            await interaction.response.edit_message(view=self)
        elif interaction is not None and interaction.message is not None:
            await interaction.message.edit(view=self)
        elif interaction is not None and interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        elif self._message is not None:
            await self._message.edit(view=self)


class LookUmaView(AllUmasView):
    def __init__(self, umas: list[dict], query: str, *, page: int = 1):
        super().__init__(umas, page=page, title=f"Look Uma - {query}")
        self.query = query

    def build_line(self, item: dict, index: int) -> str:
        rarity_label = item.get("rarity_label") or item.get("rarity_name") or str(item.get("rarity", ""))
        stars = self._stars_for_rarity(item.get("rarity"))
        return f"{index}. {item['name']}\n{stars} {rarity_label} | Overall {item['overall']}"

    def build_option(self, item: dict, index: int) -> discord.SelectOption:
        stars = self._stars_for_rarity(item.get("rarity"))
        return discord.SelectOption(
            label=str(item.get("name", "Unknown"))[:100],
            value=str(item["_id"]),
            description=f"{stars} {item.get('rarity_label') or item.get('rarity_name') or item['rarity']} | Overall {item['overall']}"[:100],
        )


class FunsiesSettingsPanel(UmaLayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        permissions = getattr(interaction.user, "guild_permissions", None)
        if permissions and permissions.administrator:
            return True
        await interaction.response.send_message(
            "Administrator permission is required.",
            ephemeral=True,
        )
        return False

    async def _rebuild_layout(self):
        settings = await funsies_get_settings(self.guild_id)
        quotes = await quote_list(self.guild_id)
        facts = await fact_list(self.guild_id)
        umas = await uma_list_characters(self.guild_id)
        gacha_names = await funsies_get_gacha_rarity_names(self.guild_id)

        quote_enabled = settings.get("quote_enabled", True)
        fact_enabled = settings.get("fact_enabled", True)
        collection_enabled = settings.get("uma_collection_enabled", True)
        daily_limit = settings.get("daily_gacha_limit", 50)

        toggle_quote_btn = self.button(
            f"Quote: {_format_bool(quote_enabled)}",
            discord.ButtonStyle.secondary,
            self._toggle_quote,
            custom_id="funsies_toggle_quote",
        )
        toggle_fact_btn = self.button(
            f"Fact: {_format_bool(fact_enabled)}",
            discord.ButtonStyle.secondary,
            self._toggle_fact,
            custom_id="funsies_toggle_fact",
        )
        toggle_collection_btn = self.button(
            f"Collection: {_format_bool(collection_enabled)}",
            discord.ButtonStyle.secondary,
            self._toggle_collection,
            custom_id="funsies_toggle_collection",
        )
        limit_btn = self.button(
            f"Daily limit: {daily_limit}",
            discord.ButtonStyle.primary,
            self._set_daily_limit,
            custom_id="funsies_daily_limit",
        )
        chances_btn = self.button(
            "Gacha chances",
            discord.ButtonStyle.primary,
            self._set_gacha_chances,
            custom_id="funsies_gacha_chances",
        )
        names_btn = self.button(
            "Rarity names",
            discord.ButtonStyle.primary,
            self._set_gacha_names,
            custom_id="funsies_gacha_names",
        )

        add_quote_btn = self.button(
            "Add Quote",
            discord.ButtonStyle.success,
            self._add_quote,
            custom_id="funsies_add_quote",
        )
        remove_quote_btn = self.button(
            "Remove Quote",
            discord.ButtonStyle.danger,
            self._remove_quote,
            custom_id="funsies_remove_quote",
        )
        toggle_quote_list_btn = self.button(
            "Toggle Quote",
            discord.ButtonStyle.secondary,
            self._toggle_quote_item,
            custom_id="funsies_toggle_quote_item",
        )

        add_fact_btn = self.button(
            "Add Fact",
            discord.ButtonStyle.success,
            self._add_fact,
            custom_id="funsies_add_fact",
        )
        remove_fact_btn = self.button(
            "Remove Fact",
            discord.ButtonStyle.danger,
            self._remove_fact,
            custom_id="funsies_remove_fact",
        )
        toggle_fact_list_btn = self.button(
            "Toggle Fact",
            discord.ButtonStyle.secondary,
            self._toggle_fact_item,
            custom_id="funsies_toggle_fact_item",
        )

        add_uma_btn = self.button(
            "Add Uma",
            discord.ButtonStyle.success,
            self._add_uma,
            custom_id="funsies_add_uma",
        )
        toggle_uma_btn = self.button(
            "Enable/Disable Uma",
            discord.ButtonStyle.secondary,
            self._toggle_uma_item,
            custom_id="funsies_toggle_uma",
        )
        edit_uma_btn = self.button(
            "Edit Uma",
            discord.ButtonStyle.primary,
            self._edit_uma_item,
            custom_id="funsies_edit_uma",
        )
        remove_uma_btn = self.button(
            "Remove Uma",
            discord.ButtonStyle.danger,
            self._remove_uma_item,
            custom_id="funsies_remove_uma",
        )
        self.set_container(
            self.text("## Funsies settings"),
            self.text("Manage global quotes, facts, Uma collection, and daily gacha limits."),
            self.separator(),
            self.text(f"Quotes: {len(quotes)} total"),
            self.text(f"Facts: {len(facts)} total"),
            self.text(f"Umas: {len(umas)} total"),
            self.separator(),
            self.text(f"Quote enabled: {_format_bool(quote_enabled)}"),
            self.text(f"Fact enabled: {_format_bool(fact_enabled)}"),
            self.text(f"Uma collection enabled: {_format_bool(collection_enabled)}"),
            self.text(f"Daily gacha limit: {daily_limit}"),
            self.text(
                "Rarity labels: "
                f"1={gacha_names.get('1', '1')}, "
                f"2={gacha_names.get('2', '2')}, "
                f"3={gacha_names.get('3', '3')}, "
                f"4={gacha_names.get('4', '4')}"
            ),
            self.separator(),
            self.text("**Uma management**"),
            self.row(add_uma_btn, edit_uma_btn, toggle_uma_btn, remove_uma_btn),
            self.separator(),
            self.row(toggle_quote_btn, toggle_fact_btn, toggle_collection_btn),
            self.row(add_quote_btn, add_fact_btn),
            self.row(remove_quote_btn, remove_fact_btn, toggle_quote_list_btn, toggle_fact_list_btn),
            self.row(limit_btn, chances_btn, names_btn),
            accent=discord.Colour.blurple(),
        )

    async def send(self, interaction: discord.Interaction):
        await self._rebuild_layout()
        await interaction.response.send_message(view=self, ephemeral=True)
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        if self._message is None:
            return
        await self._rebuild_layout()
        await self._message.edit(view=self)

    async def _toggle_quote(self, interaction: discord.Interaction):
        new_value = await funsies_toggle_setting(self.guild_id, "quote_enabled")
        await interaction.response.send_message(
            f"Quote command is now {'enabled' if new_value else 'disabled'} globally.",
            ephemeral=True,
        )
        await self.refresh(interaction)

    async def _toggle_fact(self, interaction: discord.Interaction):
        new_value = await funsies_toggle_setting(self.guild_id, "fact_enabled")
        await interaction.response.send_message(
            f"Fact command is now {'enabled' if new_value else 'disabled'} globally.",
            ephemeral=True,
        )
        await self.refresh(interaction)

    async def _toggle_collection(self, interaction: discord.Interaction):
        new_value = await funsies_toggle_setting(self.guild_id, "uma_collection_enabled")
        await interaction.response.send_message(
            f"Uma collection is now {'enabled' if new_value else 'disabled'} globally.",
            ephemeral=True,
        )
        await self.refresh(interaction)

    async def _set_daily_limit(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DailyLimitModal(self.guild_id, self))

    async def _set_gacha_chances(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GachaRarityChancesModal(self.guild_id, self))

    async def _set_gacha_names(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GachaRarityNamesModal(self.guild_id, self))

    async def _add_quote(self, interaction: discord.Interaction):
        await interaction.response.send_modal(QuoteAddModal(self.guild_id, self))

    async def _remove_quote(self, interaction: discord.Interaction):
        items = await quote_list(self.guild_id)
        view = QuoteRemoveView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

    async def _toggle_quote_item(self, interaction: discord.Interaction):
        items = await quote_list(self.guild_id)
        view = QuoteToggleView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

    async def _add_fact(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FactAddModal(self.guild_id, self))

    async def _remove_fact(self, interaction: discord.Interaction):
        items = await fact_list(self.guild_id)
        view = FactRemoveView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

    async def _toggle_fact_item(self, interaction: discord.Interaction):
        items = await fact_list(self.guild_id)
        view = FactToggleView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

    async def _add_uma(self, interaction: discord.Interaction):
        current_rarities = await uma_list_rarities(self.guild_id)
        await interaction.response.send_modal(
            UmaAddModal(self.guild_id, self, current_rarities=current_rarities)
        )

    async def _toggle_uma_item(self, interaction: discord.Interaction):
        items = await uma_list_characters(self.guild_id)
        view = UmaToggleView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

    async def _edit_uma_item(self, interaction: discord.Interaction):
        items = await uma_list_characters(self.guild_id)
        view = UmaEditView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

    async def _remove_uma_item(self, interaction: discord.Interaction):
        items = await uma_list_characters(self.guild_id)
        view = UmaRemoveView(self.guild_id, self, page=1)
        view.items = items
        await view.send(interaction)

