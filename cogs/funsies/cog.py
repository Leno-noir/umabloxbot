from __future__ import annotations

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from core.application_commands import application_command
from db.funsies import (
    application_gacha_get_usage,
    application_gacha_increment_usage,
    application_inventory_add_copy,
    application_inventory_get_selected_or_best,
    application_inventory_has_copy,
    application_inventory_increment_win,
    application_inventory_list,
    application_race_get_leaderboard,
    application_race_save_result,
    fact_get_random_active,
    ensure_application_gacha_indexes,
    ensure_funsies_indexes,
    funsies_get_gacha_rarity_chances,
    funsies_get_gacha_rarity_names,
    funsies_get_settings,
    gacha_get_usage,
    gacha_increment_usage,
    inventory_add_copy,
    inventory_has_copy,
    inventory_get_selected_or_best,
    inventory_increment_win,
    inventory_list,
    quote_get_random_active,
    race_get_leaderboard,
    race_save_result,
    rarity_name_from_id,
    uma_get_random_by_rarity,
    uma_list_characters,
    uma_search_by_name,
)
from .utils import (
    build_race_score,
    build_race_time_ms,
    format_time_ms,
    race_margin_from_diff,
)
from .views import (
    AllUmasView,
    FactCardView,
    GachaResultView,
    GachaInfoView,
    InventoryView,
    LeaderboardView,
    LookUmaView,
    QuoteCardView,
    RaceSelectView,
    RaceResultView,
)


class Funsies(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _resolve_user_label(self, guild: discord.Guild, user_id: int) -> str:
        member = guild.get_member(user_id) if guild else None
        if member:
            return member.display_name

        user = self.bot.get_user(user_id)
        if user:
            return user.display_name if isinstance(user, discord.Member) else user.name

        try:
            fetched = await self.bot.fetch_user(user_id)
            return fetched.name
        except discord.HTTPException:
            return f"User {user_id}"

    async def _require_enabled(self, interaction: discord.Interaction, key: str, label: str) -> bool:
        settings = await funsies_get_settings(interaction.guild_id or 0)
        if settings.get(key, True):
            return True

        await interaction.response.send_message(
            f"{label} is disabled globally right now.",
            ephemeral=True,
        )
        return False

    def _build_gacha_rarity_pool(self, chances: dict[str, int]) -> list[int]:
        pool: list[int] = []
        for rarity, chance in chances.items():
            try:
                count = max(0, int(chance))
            except (TypeError, ValueError):
                continue
            try:
                rarity_id = int(rarity)
            except (TypeError, ValueError):
                continue
            pool.extend([rarity_id] * count)
        return pool

    def _rarity_label_from_items(
        self,
        rarity: int,
        items: list[dict],
        configured_names: dict[str, str],
    ) -> str:
        rarity_key = str(rarity)
        if configured_names.get(rarity_key):
            return configured_names[rarity_key]

        for item in items:
            if str(item.get("rarity")) == rarity_key:
                label = item.get("rarity_label") or item.get("rarity_name")
                if label and str(label) != rarity_key:
                    return str(label)
        return rarity_key

    def _gacha_config_from_settings(self, settings: dict) -> tuple[dict[str, int], dict[str, str]]:
        chances = settings.get("gacha_rarity_chances") or {}
        rarity_names = settings.get("gacha_rarity_names") or {}
        return chances, rarity_names

    @app_commands.command(name="quote", description="Show a random quote")
    @application_command
    async def quote(self, interaction: discord.Interaction):
        if not await self._require_enabled(interaction, "quote_enabled", "Quote"):
            return

        quote = await quote_get_random_active(interaction.guild_id)
        if not quote:
            await interaction.response.send_message(
                "No active quotes are available right now.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            view=QuoteCardView(quote["character"], quote["text"]),
            ephemeral=False,
        )

    @app_commands.command(name="fact", description="Show a random fact")
    @application_command
    async def fact(self, interaction: discord.Interaction):
        if not await self._require_enabled(interaction, "fact_enabled", "Fact"):
            return

        fact = await fact_get_random_active(interaction.guild_id)
        if not fact:
            await interaction.response.send_message(
                "No active facts are available right now.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            view=FactCardView(fact["text"]),
            ephemeral=False,
        )

    @app_commands.command(name="gacha", description="Roll a random Uma from the active collection")
    @application_command
    async def gacha(self, interaction: discord.Interaction):
        # A user integration is the application-installed command, including
        # when Discord lets that installation invoke it inside a guild.
        is_application_gacha = interaction.is_user_integration()
        await interaction.response.defer(thinking=True)
        if is_application_gacha:
            settings, usage_doc, active_umas = await asyncio.gather(
                funsies_get_settings(0),
                application_gacha_get_usage(interaction.user.id),
                uma_list_characters(0, active=True),
            )
        else:
            settings, usage_doc, active_umas = await asyncio.gather(
                funsies_get_settings(interaction.guild_id),
                gacha_get_usage(interaction.guild_id, interaction.user.id),
                uma_list_characters(interaction.guild_id, active=True),
            )
        chances, rarity_names = self._gacha_config_from_settings(settings)
        if not settings.get("uma_collection_enabled", True):
            await interaction.followup.send(
                "Uma collection is disabled globally right now.",
                ephemeral=True,
            )
            return

        limit = int(settings.get("daily_gacha_limit", 50))
        used = int(usage_doc.get("used", 0)) if usage_doc else 0
        if used >= limit:
            await interaction.followup.send(
                f"You already used {used}/{limit} gachas today.",
                ephemeral=True,
            )
            return

        if not active_umas:
            await interaction.followup.send(
                "No active Umas are available to roll.",
                ephemeral=True,
            )
            return

        rarity_pool = self._build_gacha_rarity_pool(chances)
        if not rarity_pool:
            await interaction.followup.send(
                "Gacha rarity chances are not configured correctly.",
                ephemeral=True,
            )
            return

        rarity = random.choice(rarity_pool)
        catalog_scope = 0 if is_application_gacha else interaction.guild_id
        picked = await uma_get_random_by_rarity(catalog_scope, rarity)
        if not picked:
            matching_active_umas = [uma for uma in active_umas if int(uma.get("rarity", 1) or 1) == rarity]
            if not matching_active_umas:
                await interaction.followup.send(
                    "No active Uma is available for the selected rarity.",
                    ephemeral=True,
                )
                return
            picked = random.choice(matching_active_umas)
        if int(picked.get("rarity", 1) or 1) != rarity:
            await interaction.followup.send(
                "Gacha selection failed to match the selected rarity.",
                ephemeral=True,
            )
            return
        if is_application_gacha:
            already_owned = await application_inventory_has_copy(
                interaction.user.id,
                picked["_id"],
            )
        else:
            already_owned = await inventory_has_copy(
                interaction.guild_id,
                interaction.user.id,
                picked["_id"],
            )
        if not already_owned:
            if is_application_gacha:
                await application_inventory_add_copy(interaction.user.id, picked)
            else:
                await inventory_add_copy(
                    interaction.guild_id,
                    interaction.user.id,
                    picked,
                )

        if is_application_gacha:
            await application_gacha_increment_usage(interaction.user.id, 1)
        else:
            await gacha_increment_usage(interaction.guild_id, interaction.user.id, 1)
        await interaction.followup.send(
            view=GachaResultView(picked, interaction.user.id, interaction.user.mention, rarity_names)
        )

    @app_commands.command(name="gacha-info", description="Show gacha rarity pool and current chances")
    @application_command
    async def gacha_info(self, interaction: discord.Interaction):
        scope = 0 if interaction.is_user_integration() else interaction.guild_id
        settings, active_umas = await asyncio.gather(
            funsies_get_settings(scope),
            uma_list_characters(scope, active=True),
        )
        chances, rarity_names = self._gacha_config_from_settings(settings)
        if not settings.get("uma_collection_enabled", True):
            await interaction.response.send_message(
                "Uma collection is disabled globally right now.",
                ephemeral=True,
            )
            return

        rarity_order = [4, 3, 2, 1]
        available_lines = []
        for rarity in rarity_order:
            count = sum(1 for uma in active_umas if uma["rarity"] == rarity)
            rarity_label = self._rarity_label_from_items(rarity, active_umas, rarity_names)
            available_lines.append(f"{rarity_label} - {count} Umas")

        rarity_lines = [
            f"{self._rarity_label_from_items(rarity, active_umas, rarity_names)} - {chances.get(str(rarity), 0)}%"
            for rarity in rarity_order
        ]

        view = GachaInfoView(
            active_umas_count=len(active_umas),
            available_lines=available_lines,
            rarity_lines=rarity_lines,
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(name="uma-list", description="Show every Uma in the collection")
    @application_command
    @app_commands.describe(rarity="Filter by rarity")
    async def allumas(self, interaction: discord.Interaction, rarity: str | None = None):
        scope = 0 if interaction.is_user_integration() else interaction.guild_id
        settings = await funsies_get_settings(scope)
        if not settings.get("uma_collection_enabled", True):
            await interaction.response.send_message(
                "Uma collection is disabled globally right now.",
                ephemeral=True,
            )
            return

        umas = await uma_list_characters(scope)
        if rarity is not None:
            rarity_filter = rarity.strip()
            if rarity_filter:
                rarity_names = await funsies_get_gacha_rarity_names(scope)
                rarity_ids = {
                    str(rarity_id)
                    for rarity_id, rarity_name in rarity_names.items()
                    if rarity_name.lower() == rarity_filter.lower() or str(rarity_id) == rarity_filter
                }
                rarity_ids.update(
                    str(uma["rarity"])
                    for uma in umas
                    if str(uma.get("rarity_label") or uma.get("rarity_name") or "").lower() == rarity_filter.lower()
                )
                if not rarity_ids:
                    await interaction.response.send_message(
                        f'Unknown rarity "{rarity}".',
                        ephemeral=True,
                    )
                    return
                umas = [uma for uma in umas if str(uma["rarity"]) in rarity_ids]
        if not umas:
            await interaction.response.send_message("No Umas are available yet.", ephemeral=True)
            return

        title = "All Umas"
        if rarity:
            rarity_names = await funsies_get_gacha_rarity_names(scope)
            rarity_label = rarity_names.get(rarity.strip(), rarity.strip())
            for uma in umas:
                label = uma.get("rarity_label") or uma.get("rarity_name")
                if str(uma.get("rarity")) == rarity.strip() and label:
                    rarity_label = str(label)
                    break
            title = f"All Umas - {rarity_label}"
        view = AllUmasView(umas, title=title)
        await view.send(interaction, ephemeral=True)

    @app_commands.command(name="uma-info", description="Search Umas by name")
    @app_commands.describe(name="Name or partial name to search")
    @application_command
    async def lookuma(self, interaction: discord.Interaction, name: str):
        scope = 0 if interaction.is_user_integration() else interaction.guild_id
        settings = await funsies_get_settings(scope)
        if not settings.get("uma_collection_enabled", True):
            await interaction.response.send_message(
                "Uma collection is disabled globally right now.",
                ephemeral=True,
            )
            return

        umas = await uma_search_by_name(scope, name)
        if not umas:
            await interaction.response.send_message(
                f'No Umas found matching "{name}".',
                ephemeral=True,
            )
            return

        view = LookUmaView(umas, name)
        await view.send(interaction, ephemeral=True)

    @app_commands.command(name="uma-inventory", description="Show a user's Uma inventory")
    @app_commands.describe(user="User to inspect", public_visibility="Make the inventory visible to everyone")
    @application_command
    async def umainventory(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        public_visibility: bool = False,
    ):
        is_application = interaction.is_user_integration()
        target = user or interaction.user
        items = (
            await application_inventory_list(target.id)
            if is_application
            else await inventory_list(interaction.guild_id, target.id)
        )
        if not items:
            await interaction.response.send_message(
                f"{target.display_name} does not have any Umas yet.",
                ephemeral=True,
            )
            return

        view = InventoryView(interaction.guild_id or 0, target, application=is_application)
        await view.send(interaction, ephemeral=not public_visibility)

    @app_commands.command(name="choose-your-race-uma", description="Choose which Uma will be used in races")
    @application_command
    async def uma_race_select(self, interaction: discord.Interaction):
        is_application = interaction.is_user_integration()
        scope = 0 if is_application else interaction.guild_id
        settings = await funsies_get_settings(scope)
        if not settings.get("uma_collection_enabled", True):
            await interaction.response.send_message(
                "Uma collection is disabled globally right now.",
                ephemeral=True,
            )
            return

        items = (
            await application_inventory_list(interaction.user.id)
            if is_application
            else await inventory_list(interaction.guild_id, interaction.user.id)
        )
        if not items:
            await interaction.response.send_message(
                "You do not have any Umas yet.",
                ephemeral=True,
            )
            return

        view = RaceSelectView(interaction.guild_id or 0, interaction.user.id, application=is_application)
        view.items = items
        await view.send(interaction, ephemeral=True)

    @app_commands.command(name="race", description="Race another user using your selected Uma")
    @app_commands.describe(opponent="User to race against", mention="Mention users in the result")
    @application_command
    async def race(self, interaction: discord.Interaction, opponent: discord.User, mention: bool = True):
        is_application = interaction.is_user_integration()
        scope = 0 if is_application else interaction.guild_id
        settings = await funsies_get_settings(scope)
        if not settings.get("uma_collection_enabled", True):
            await interaction.response.send_message(
                "Uma collection is disabled globally right now.",
                ephemeral=True,
            )
            return

        if opponent.bot:
            await interaction.response.send_message(
                "You cannot race a bot.",
                ephemeral=True,
            )
            return

        if opponent.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot race yourself.",
                ephemeral=True,
            )
            return

        if is_application:
            author_pick, opponent_pick = await asyncio.gather(
                application_inventory_get_selected_or_best(interaction.user.id),
                application_inventory_get_selected_or_best(opponent.id),
            )
        else:
            author_pick, opponent_pick = await asyncio.gather(
                inventory_get_selected_or_best(interaction.guild_id, interaction.user.id),
                inventory_get_selected_or_best(interaction.guild_id, opponent.id),
            )
        if not author_pick or not opponent_pick:
            await interaction.response.send_message(
                "Both users need at least one Uma in their inventory.",
                ephemeral=True,
            )
            return

        author_score = build_race_score(author_pick["overall"])
        opponent_score = build_race_score(opponent_pick["overall"])
        author_time = build_race_time_ms(author_score)
        opponent_time = build_race_time_ms(opponent_score)

        if author_time == opponent_time:
            if author_score == opponent_score:
                if random.choice([True, False]):
                    author_time -= 1
                else:
                    opponent_time -= 1
            elif author_score > opponent_score:
                author_time -= 1
            else:
                opponent_time -= 1

        if author_time < opponent_time:
            winner_user = interaction.user
            winner_pick = author_pick
            loser_user = opponent
            loser_pick = opponent_pick
            winner_time = author_time
            loser_time = opponent_time
        else:
            winner_user = opponent
            winner_pick = opponent_pick
            loser_user = interaction.user
            loser_pick = author_pick
            winner_time = opponent_time
            loser_time = author_time

        if is_application:
            await application_inventory_increment_win(winner_user.id, winner_pick["_id"])
        else:
            await inventory_increment_win(
                interaction.guild_id,
                winner_user.id,
                winner_pick["_id"],
            )
        winner_pick_after = winner_pick.get("wins", 0) + 1
        margin = race_margin_from_diff(abs(loser_time - winner_time))

        race_result = {
            "winner_user_id": winner_user.id,
            "loser_user_id": loser_user.id,
            "winner_uma_inventory_id": winner_pick["_id"],
            "winner_uma_name": winner_pick["uma_name"],
            "winner_uma_overall": winner_pick["overall"],
            "winner_uma_rarity": winner_pick["rarity"],
            "winner_time_ms": winner_time,
            "winner_uma_wins_after": winner_pick_after,
            "loser_uma_inventory_id": loser_pick["_id"],
            "loser_uma_name": loser_pick["uma_name"],
            "loser_uma_overall": loser_pick["overall"],
            "loser_uma_rarity": loser_pick["rarity"],
            "loser_time_ms": loser_time,
            "margin": margin,
        }
        if is_application:
            await application_race_save_result(race_result)
        else:
            await race_save_result({"guild_id": interaction.guild_id, **race_result})

        winner_label = winner_user.mention if mention else winner_user.display_name
        loser_label = loser_user.mention if mention else loser_user.display_name
        await interaction.response.send_message(
            view=RaceResultView(
                winner_user=winner_user,
                winner_label=winner_label,
                winner_pick=winner_pick,
                loser_user=loser_user,
                loser_label=loser_label,
                loser_pick=loser_pick,
                winner_time=winner_time,
                loser_time=loser_time,
                margin=margin,
            ),
            allowed_mentions=discord.AllowedMentions(users=mention),
        )

    @app_commands.command(name="leaderboard", description="Show the fastest Uma race times")
    @application_command
    async def leaderboard(self, interaction: discord.Interaction):
        is_application = interaction.is_user_integration()
        results = (
            await application_race_get_leaderboard(limit=50)
            if is_application
            else await race_get_leaderboard(interaction.guild_id, limit=50)
        )
        if not results:
            await interaction.response.send_message("No race results have been recorded yet.")
            return

        entries: list[dict] = []
        for index, result in enumerate(results, start=1):
            user_label = await self._resolve_user_label(interaction.guild, result["winner_user_id"])
            entries.append(
                {
                    "rank": index,
                    "user_label": user_label,
                    "uma_name": result["winner_uma_name"],
                    "time_ms": result["winner_time_ms"],
                    "wins": result["winner_uma_wins_after"],
                }
            )

        view = LeaderboardView(entries)
        await view.send(interaction, ephemeral=False)


async def setup(bot: commands.Bot):
    await ensure_funsies_indexes()
    await ensure_application_gacha_indexes()
    await bot.add_cog(Funsies(bot))
