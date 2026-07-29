import discord

from .base import Section


class FunsiesSection(Section):
    label = "Funsies"
    emoji = "Dice"
    db_keys = [
        "quote_enabled",
        "fact_enabled",
        "uma_collection_enabled",
        "daily_gacha_limit",
        "gacha_rarity_chances",
        "gacha_rarity_names",
    ]

    async def get_fields(settings: dict) -> list[tuple[str, str]]:
        quote_enabled = settings.get("quote_enabled", True)
        fact_enabled = settings.get("fact_enabled", True)
        collection_enabled = settings.get("uma_collection_enabled", True)
        daily_limit = settings.get("daily_gacha_limit", 50)
        chances = settings.get("gacha_rarity_chances") or {}
        names = settings.get("gacha_rarity_names") or {}
        chances_text = ", ".join(
            f"{names.get(rarity, rarity)} {chance}%"
            for rarity, chance in sorted(chances.items(), key=lambda item: int(item[0]))
        ) or "Default"
        return [
            ("Quote", "Enabled" if quote_enabled else "Disabled"),
            ("Fact", "Enabled" if fact_enabled else "Disabled"),
            ("Uma collection", "Enabled" if collection_enabled else "Disabled"),
            ("Daily gacha limit", str(daily_limit)),
            ("Gacha chances", chances_text),
        ]

    def get_buttons(guild_id: int, parent_view) -> list[discord.ui.Button]:
        button = discord.ui.Button(
            label="Funsies Settings",
            style=discord.ButtonStyle.primary,
            row=0,
        )

        async def open_funsies_settings(interaction: discord.Interaction):
            from cogs.funsies.views import FunsiesSettingsPanel

            panel = FunsiesSettingsPanel(guild_id)
            await panel.send(interaction)

        button.callback = open_funsies_settings
        return [button]
