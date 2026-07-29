from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from cogs.blacklist.views import BlacklistLogView
from core.config import (
    Colors,
    IS_DEVELOPMENT,
    MAIN_GUILD_ID,
    ROTECTOR_API_BASE_URL,
    ROTECTOR_API_KEY,
)
from db.allowed_guilds import allowed_guild_is_enabled
from db.blacklist import bl_history
from db.guild_configs import (
    guild_get_rotector_alert_channel,
    guild_get_rotector_enabled,
)

ACTIONABLE_FLAG_TYPES = {1, 2}
ACTIONABLE_FLAG_TYPES_LABEL = "Only flag types 1 and 2 (confirmed) trigger alerts."
FLAG_TYPE_NAMES = {
    0: "Unflagged",
    1: "Flagged",
    2: "Confirmed",
    3: "Queued",
    4: "Provisional Flag",
    5: "Mixed",
    6: "Past Offender",
    8: "Redacted",
}
ROTECTOR_TEST_FLAG_CHOICES = [
    app_commands.Choice(name=f"{flag_type} - {label}", value=flag_type)
    for flag_type, label in FLAG_TYPE_NAMES.items()
]
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RotectorCheck:
    member_id: int
    guild_id: int
    roblox_id: str
    roblox_user: str


def _flag_type_from_payload(payload: dict[str, Any]) -> int | None:
    for key in ("flagType", "flag_type", "flag", "status"):
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def _reasons_from_payload(payload: dict[str, Any]) -> str:
    raw_reasons = payload.get("reasons") or payload.get("reason") or payload.get("violations")
    if isinstance(raw_reasons, list):
        reasons = [str(reason) for reason in raw_reasons if reason]
        return ", ".join(reasons) if reasons else "No public reason provided."
    if raw_reasons:
        return str(raw_reasons)
    return "No public reason provided."


class RotectorJoinAlertView(BlacklistLogView):
    def __init__(
        self,
        member: discord.Member | None,
        roblox_id: str,
        roblox_user: str,
        payload: dict[str, Any],
        *,
        discord_id: int | None = None,
        guild_name: str | None = None,
    ):
        flag_type = _flag_type_from_payload(payload)
        flag_label = FLAG_TYPE_NAMES.get(flag_type, f"Unknown ({flag_type})")
        if member is None and discord_id is None:
            raise ValueError("Rotector alert requires a Discord member or Discord ID.")
        self.discord_id = discord_id if discord_id is not None else member.id
        self.reason = _reasons_from_payload(payload)
        member_label = member.mention if member else f"<@{self.discord_id}>"
        super().__init__(
            "Rotector Alert!",
            discord.Colour(Colors.YELLOW),
            [
                ("Discord user", f"{member_label} (`{self.discord_id}`)"),
                ("Roblox", f"{roblox_user} (`{roblox_id}`)"),
                ("Rotector flag", flag_label),
                ("Alert rule", ACTIONABLE_FLAG_TYPES_LABEL),
                ("Reason", self.reason),
                ("Server", guild_name or member.guild.name),
                ("Time", discord.utils.format_dt(discord.utils.utcnow(), style="f")),
            ],
        )
        # Alerts are operational messages, not persistent controls. This avoids
        # dead component callbacks after a bot restart.
        self.timeout = 900
        button = self.button(
            "Copy Ban Command",
            discord.ButtonStyle.primary,
            self.copy_ban_command,
            custom_id=f"rotector_copy_ban_{self.discord_id}",
        )
        self.add_item(self.row(button))

    async def copy_ban_command(self, interaction: discord.Interaction):
        command = f"/ban user:{self.discord_id} reason:{self.reason}"
        await interaction.response.send_message(
            f"You can copy the command from here:\n```{command}```",
            ephemeral=True,
        )


class Rotector(commands.Cog):
    """Checks observer joins against Rotector with a small API queue."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue: asyncio.Queue[RotectorCheck] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        self.worker_task = asyncio.create_task(self._worker())

    async def cog_unload(self):
        if self.worker_task:
            self.worker_task.cancel()
        if self.session:
            await self.session.close()

    @app_commands.command(
        name="rotector-test-view",
        description="Development only: preview a Rotector alert card",
    )
    @app_commands.choices(flag_type=ROTECTOR_TEST_FLAG_CHOICES)
    @app_commands.describe(discord_id="Optional Discord user ID to show in the alert")
    async def test_rotector_view(
        self,
        interaction: discord.Interaction,
        flag_type: app_commands.Choice[int],
        discord_id: str | None = None,
    ):
        """Render Rotector alert views without querying the API."""
        if not IS_DEVELOPMENT or interaction.guild_id != MAIN_GUILD_ID:
            await interaction.response.send_message("This development command is unavailable.", ephemeral=True)
            return

        if discord_id is not None and (not discord_id.isdecimal() or int(discord_id) <= 0):
            await interaction.response.send_message("Provide a valid positive Discord user ID.", ephemeral=True)
            return

        target_id = int(discord_id) if discord_id else interaction.user.id
        target_member = interaction.guild.get_member(target_id) if interaction.guild else None

        payload = {
            "flagType": flag_type.value,
            "reasons": ["Development preview - no Rotector API request was made."],
        }
        view = RotectorJoinAlertView(
            target_member,
            roblox_id="123456789",
            roblox_user="RotectorTestUser",
            payload=payload,
            discord_id=target_id,
            guild_name=interaction.guild.name if interaction.guild else "Uma Portal",
        )
        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id == MAIN_GUILD_ID:
            return
        if not await allowed_guild_is_enabled(member.guild.id):
            return
        if not await guild_get_rotector_enabled(member.guild.id):
            return
        if not await guild_get_rotector_alert_channel(member.guild.id):
            return

        record = await bl_history(str(member.id))
        if not record or not record.get("roblox_id"):
            return

        await self.queue.put(
            RotectorCheck(
                member_id=member.id,
                guild_id=member.guild.id,
                roblox_id=str(record["roblox_id"]),
                roblox_user=str(record.get("roblox_user") or "Unknown"),
            )
        )

    async def _worker(self):
        while True:
            check = await self.queue.get()
            try:
                await self._process_check(check)
            except Exception:
                logger.exception("Rotector check failed for Roblox user %s", check.roblox_id)
            finally:
                self.queue.task_done()
                await asyncio.sleep(0.25)

    async def _process_check(self, check: RotectorCheck):
        guild = self.bot.get_guild(check.guild_id)
        if guild is None:
            return

        member = guild.get_member(check.member_id)
        if member is None:
            return

        payload = await self._fetch_rotector_user(check.roblox_id)
        flag_type = _flag_type_from_payload(payload)
        # Only confirmed Rotector flag types should create a moderation alert.
        if flag_type not in ACTIONABLE_FLAG_TYPES:
            return

        channel_id = await guild_get_rotector_alert_channel(check.guild_id)
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if not channel:
            return

        view = RotectorJoinAlertView(member, check.roblox_id, check.roblox_user, payload)
        await channel.send(view=view)

    async def _fetch_rotector_user(self, roblox_id: str) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("Rotector HTTP session is not ready.")

        base_url = ROTECTOR_API_BASE_URL.rstrip("/")
        url = f"{base_url}/users/{roblox_id}"
        headers = {"Accept": "application/json"}
        if ROTECTOR_API_KEY:
            headers["Authorization"] = f"Bearer {ROTECTOR_API_KEY}"

        async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            data = await response.json()

        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"]
        if isinstance(data, dict):
            return data
        raise ValueError("Unexpected Rotector response format.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Rotector(bot))
