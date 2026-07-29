from datetime import datetime

import discord
from discord.ext import commands

from core.ui import PaginatedLayoutView, UmaLayoutView, separator, text
from core.utils import get_user_by_discord_id
from db.feedback import feedback_list
from db.guild_configs import guild_get_feedback_anonymous_allowed
from .utils import (
    FEEDBACK_CATEGORY_OPTIONS,
    category_emoji,
    category_label,
)

## message shown in the feedback thread for new submissions
class FeedbackNotificationView(UmaLayoutView):

    def __init__(
        self,
        game_name: str,
        category: str,
        feedback_message: str,
        sender_name: str,
        sent_at: str,
    ):
        super().__init__(timeout=None)
       
       
        self.set_container(
            self.text("## :bulb: NEW FEEDBACK!!"),
            self.text("**Game**"),
            self.text(game_name),
            self.separator(),
            self.text("**Category**"),
            self.text(category),
            self.separator(),
            self.text("**Feedback Message**"),
            self.text(feedback_message),
            self.separator(),
            self.text("**Sent by**"),
            self.text(sender_name),
            self.text(sent_at),
            accent=discord.Colour(3447003),
        )





## public feedback panel with active game selection
class FeedbackPanelView(UmaLayoutView):

    def __init__(self, games: list[dict], bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.games_by_name = {game["name"]: game for game in games}

       
        sorted_games = sorted(games, key=lambda game: game["name"])
       
        game_select = self.select(
            "Select the game you want to submit feedback to",
            [
                discord.SelectOption(label=game["name"], value=game["name"])
                for game in sorted_games
            ],
            self._game_selected,
            custom_id="feedback_panel_game_select",
        )

        self.set_container(
            self.media("https://i.imgur.com/7uCKm3E.png"),
            self.text("Submit a feedback to a game below"),
            self.separator(),
            self.row(game_select),
            accent=discord.Colour(3447003),
        )





    async def _game_selected(self, interaction: discord.Interaction):
        
        selected_game_name = interaction.data["values"][0]
        game = self.games_by_name[selected_game_name]
        anonymous_allowed = await guild_get_feedback_anonymous_allowed(self.guild_id)

        await interaction.response.send_message(
            "Select a feedback category:",
            view=FeedbackCategorySelectView(
                game_name=game["name"],
                bot=self.bot,
                anonymous_allowed=anonymous_allowed,
            ),
            ephemeral=True,
        )





## feedback game selector used before opening the feedback list
class FeedbackGameSelectView(discord.ui.View):

    def __init__(
        self,
        games: list[dict],
        bot: commands.Bot,
        anonymous_allowed: bool,
    ):
        super().__init__(timeout=120)
        self.bot = bot
        self.anonymous_allowed = anonymous_allowed
        self.games_by_name = {game["name"]: game for game in games}

        game_select = discord.ui.Select(
            placeholder="Choose a game...",
            options=[
                discord.SelectOption(label=game["name"], value=game["name"])
                for game in games
            ],
            min_values=1,
            max_values=1,
        )
        game_select.callback = self._game_selected
        
        self.add_item(game_select)





    async def _game_selected(self, interaction: discord.Interaction):
       
        selected_game_name = interaction.data["values"][0]
        game = self.games_by_name[selected_game_name]

        await interaction.response.send_message(
            "Select a feedback category:",
            view=FeedbackCategorySelectView(
                game_name=game["name"],
                bot=self.bot,
                anonymous_allowed=self.anonymous_allowed,
            ),
            ephemeral=True,
        )





## feedback category selector that opens anonymous choice or the submit modal
class FeedbackCategorySelectView(discord.ui.View):

    def __init__(
        self,
        game_name: str,
        bot: commands.Bot,
        anonymous_allowed: bool,
    ):
        super().__init__(timeout=120)
        self.game_name = game_name
        self.bot = bot
        self.anonymous_allowed = anonymous_allowed

        category_select = discord.ui.Select(
            placeholder="Choose feedback category...",
            options=FEEDBACK_CATEGORY_OPTIONS,
            min_values=1,
            max_values=1,
        )
        category_select.callback = self._category_selected
        
        self.add_item(category_select)




    async def _category_selected(self, interaction: discord.Interaction):
        from .modals import FeedbackSubmitModal

        feedback_category = interaction.data["values"][0]

        if self.anonymous_allowed:
            await interaction.response.send_message(
                "Send feedback anonymously?",
                view=AnonSelectView(self.game_name, self.bot, feedback_category),
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            FeedbackSubmitModal(
                game_name=self.game_name,
                category=feedback_category,
                anonymous=False,
                bot=self.bot,
            )
        )






## confirmation view for anonymous submission choice
class AnonSelectView(discord.ui.View):

    def __init__(self, game_name: str, bot: commands.Bot, category: str = "suggestion"):
        super().__init__(timeout=60)
        self.game_name = game_name
        self.bot = bot
        self.category = category

  
  
    @discord.ui.button(label="Send", style=discord.ButtonStyle.green)
    async def send_attributed(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
       
        from .modals import FeedbackSubmitModal

        await interaction.response.send_modal(
            FeedbackSubmitModal(
                game_name=self.game_name,
                category=self.category,
                anonymous=False,
                bot=self.bot,
            )
        )

  
  
    @discord.ui.button(label="Send Anonymously", style=discord.ButtonStyle.grey)
    async def send_anonymous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
       
        from .modals import FeedbackSubmitModal

        await interaction.response.send_modal(
            FeedbackSubmitModal(
                game_name=self.game_name,
                category=self.category,
                anonymous=True,
                bot=self.bot,
            )
        )




    async def on_timeout(self):
        for component in self.children:
            component.disabled = True






## game selector used before opening the feedback list
class FeedbackListGameSelectView(discord.ui.View):

    def __init__(self, games: list[dict], bot: commands.Bot, guild_id: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.guild_id = guild_id

        game_select = discord.ui.Select(
            placeholder="Choose a game...",
            options=[
                discord.SelectOption(label=game["name"], value=game["name"])
                for game in games
            ],
            min_values=1,
            max_values=1,
        )
        game_select.callback = self._game_selected
        
        self.add_item(game_select)




    async def _game_selected(self, interaction: discord.Interaction):
       
        selected_game_name = interaction.data["values"][0]
        view = FeedbackListView(self.bot, self.guild_id, selected_game_name)
       
        await view.send(interaction, ephemeral=True)





## list of feedback for a specific game, with optional category filtering
class FeedbackListView(PaginatedLayoutView):

    def __init__(self, bot: commands.Bot, guild_id: int, game_name: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.game_name = game_name
        self.current_category: str | None = None
        self.all_feedback: list[dict] = []




    async def load_feedback(self):
        self.all_feedback = await feedback_list(
            self.guild_id,
            self.game_name,
            category=self.current_category,
        )




    async def _feedback_sender(self, feedback_entry: dict) -> str:
        if feedback_entry.get("anonymous", False):
            return "Anonymous"

        return await get_user_by_discord_id(self.bot, feedback_entry["sender_id"])




    def _feedback_timestamp(self, feedback_entry: dict) -> str:
        sent_at = feedback_entry.get("sent_at")
       
        if isinstance(sent_at, str):
            sent_at = datetime.fromisoformat(sent_at)

        return f"<t:{int(sent_at.timestamp())}:f>" if sent_at else "Unknown"




    async def _feedback_items(self, feedback_entry: dict) -> list[discord.ui.Item]:
        sender_label = await self._feedback_sender(feedback_entry)
        sent_at_text = self._feedback_timestamp(feedback_entry)
        feedback_category = feedback_entry.get("category", "suggestion")

        return [
            text(f"{category_label(feedback_category)} - **{sender_label}**"),
            text(feedback_entry["description"]),
            text(f"At: {sent_at_text}"),
            separator(),
        ]




    def _filter_row(self) -> discord.ui.ActionRow:
        all_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="All",
            emoji="🔸",
            custom_id="filter_all",
        )
       
        bug_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Bug",
            emoji=category_emoji("bug"),
            custom_id="filter_bug",
        )
       
        balancing_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Balancing",
            emoji=category_emoji("balancing"),
            custom_id="filter_balancing",
        )
       
        ux_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="UX",
            emoji=category_emoji("ux"),
            custom_id="filter_ux",
        )
      
        suggestion_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Suggestion",
            emoji=category_emoji("suggestion"),
            custom_id="filter_suggestion",
        )

      
        all_button.callback = lambda interaction: self._set_filter(interaction, None)
        bug_button.callback = lambda interaction: self._set_filter(interaction, "bug")
        balancing_button.callback = lambda interaction: self._set_filter(
            interaction,
            "balancing",
        )
        ux_button.callback = lambda interaction: self._set_filter(interaction, "ux")
        suggestion_button.callback = lambda interaction: self._set_filter(
            interaction,
            "suggestion",
        )

       
        return self.row(
            all_button,
            bug_button,
            balancing_button,
            ux_button,
            suggestion_button,
        )




    async def _rebuild_layout(self):
        await self.load_feedback()
      
        total_feedback = len(self.all_feedback)
        total_pages = self.clamp_page(total_feedback)
        page_feedback = self.page_items(self.all_feedback)

        items: list[discord.ui.Item] = [
            text(f"## **Feedback for __{self.game_name}__**"),
            separator(),
        ]

        if not page_feedback:
            items.append(text("No feedback yet."))
      
        else:
            for feedback_entry in page_feedback:
                items.extend(await self._feedback_items(feedback_entry))

      
        items.append(text(f"Page {self.page}/{total_pages} • Total: {total_feedback}"))
        items.append(self._filter_row())

        self.set_items(
            self.container(*items, accent=discord.Colour.blurple()),
            self.pagination_row(total_pages, "feedback"),
        )




    async def _set_filter(
        self,
        interaction: discord.Interaction,
        category: str | None,
    ):
        self.current_category = category
        self.page = 1
        await self.refresh(interaction)
