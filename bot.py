import asyncio
import logging
import os

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands

from cogs.feedback.views import FeedbackPanelView
from core import (
    DISCORD_TOKEN,
    MAIN_GUILD_ID,
    sync_network_commands,
    validate_runtime_config,
)
from core.config import ROTECTOR_ENABLED
from db import allowed_guild_is_enabled
from db.indexes import ensure_core_indexes
from db.blacklist import bl_get
from db.connection import connect, disconnect
from db.feedback import feedback_get_games
from db.guild_configs import (
    guild_get_blacklist_panel_message,
    guild_get_blacklisted_users_join_alert_channel,
    guild_get_feedback_channel,
    guild_get_feedback_panel_message,
)
from cogs.blacklist.views import (
    BlacklistBanPromptView,
    BlacklistPanelView,
    build_blacklist_join_alert_embed,
)

logger = logging.getLogger(__name__)


async def health_check(_request: web.Request) -> web.Response:
    """Expose a readiness endpoint for the Render Web Service."""
    discord_ready = bot.is_ready()
    return web.json_response(
        {"status": "ok" if discord_ready else "starting", "discord_ready": discord_ready},
        status=200 if discord_ready else 503,
    )


async def start_health_server() -> web.AppRunner:
    """Start the lightweight server required by Render's free Web Service."""
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info("Health endpoint listening on port %s", port)
    return runner

#configure bot intents (permissions for reading guild events)
intents = discord.Intents.default()
intents.members = True

#list of all cogs (modules) to load on startup
COGS = [
    "cogs.blacklist",
    "cogs.settings",
    "cogs.feedback",
    "cogs.networking",
    "cogs.funsies",
]

if ROTECTOR_ENABLED:
    COGS.append("cogs.rotector")


class UmaPortalBot(commands.Bot):
    """Bot lifecycle that performs startup work exactly once per process."""

    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.commands_synced = False
        self.panels_rehydrated = False

    async def setup_hook(self):
        validate_runtime_config()
        await connect()
        await ensure_core_indexes()
        for extension in COGS:
            await self.load_extension(extension)
            logger.info("Loaded extension: %s", extension)

    async def close(self):
        await disconnect()
        await super().close()


#create the bot instance with command prefix and configured intents
bot = UmaPortalBot()

#expose sync helper so settings views can refresh command visibility after allowlist changes
bot.sync_network_commands = lambda: sync_network_commands(
    bot,
    MAIN_GUILD_ID,
)

#event triggered when the bot successfully connects and is ready
@bot.event
async def on_ready():
    logger.info("Bot online as %s (%s), connected to %s servers", bot.user, bot.user.id, len(bot.guilds))

    if not bot.commands_synced:
        try:
            await bot.sync_network_commands()
            bot.commands_synced = True
        except Exception:
            logger.exception("Initial command synchronization failed")
            return

    if bot.panels_rehydrated:
        return
    bot.panels_rehydrated = True

    logger.info("Rehydrating panels for main guild %s", MAIN_GUILD_ID)

    # Recupera IDs salvos
    blacklistChannel, blacklistPanelMessage = await guild_get_blacklist_panel_message(MAIN_GUILD_ID)
    feedbackChannel, feedbackPanelMessage = await guild_get_feedback_panel_message(MAIN_GUILD_ID)

    # Busca canais
    bChannel = bot.get_channel(blacklistChannel) if blacklistChannel else None
    fChannel = bot.get_channel(feedbackChannel) if feedbackChannel else None

    # --- Blacklist Panel ---
    if bChannel and blacklistPanelMessage:
        try:
            bmessage = await bChannel.fetch_message(blacklistPanelMessage)
            view = BlacklistPanelView(bot)
            await view._rebuild_layout()
            await bmessage.edit(view=view)
            logger.info("Blacklist panel rehydrated")
        except Exception:
            logger.exception("Failed to rehydrate blacklist panel")

    # --- Feedback Panel ---
    if fChannel and feedbackPanelMessage:
        try:
            fmessage = await fChannel.fetch_message(feedbackPanelMessage)
            feedbackgames = await feedback_get_games(MAIN_GUILD_ID)  # precisa ser async
            view = FeedbackPanelView(feedbackgames, bot, MAIN_GUILD_ID)
            await fmessage.edit(view=view)
            logger.info("Feedback panel rehydrated")
        except Exception:
            logger.exception("Failed to rehydrate feedback panel")





#event triggered when a user joins any server the bot is in
@bot.event
async def on_member_join(member: discord.Member):
    """Send join alerts only for enabled observer guilds with a local alert channel."""

    #the main guild does not need observer join alerts
    if member.guild.id == MAIN_GUILD_ID:
        return

    #ignore servers that are not enabled observer guilds
    if not await allowed_guild_is_enabled(member.guild.id):
        return

    #check if the user is on the blacklist
    record = await bl_get(str(member.id))
    if not record:
        return

    #get the local observer alert channel for this guild
    channel_id = await guild_get_blacklisted_users_join_alert_channel(member.guild.id)
    if not channel_id:
        return

    #fetch the configured channel from the observer guild
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    #create embed with blacklist join alert
    embed = build_blacklist_join_alert_embed(member, record)
    view = BlacklistBanPromptView(member.id, record["current_reason"])

    #send the alert to the local observer alert channel
    await channel.send(embed=embed, view=view)




#global error handler for all slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    #log the error to console
    original_error = getattr(error, "original", None)
    logger.error(
        "App command error: %s: %s",
        type(error).__name__,
        error,
        exc_info=original_error if isinstance(original_error, BaseException) else None,
    )

    #handle permission check failures (from @is_manager decorator)
    if isinstance(error, app_commands.CheckFailure):
        try:
            if interaction.response.is_done():
                await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "You do not have permission to use this command.",
                    ephemeral=True,
                )
        except discord.HTTPException:
            pass
        return

    #handle other command errors with generic error message
    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                "Something went wrong while running this command.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Something went wrong while running this command.",
                ephemeral=True,
            )
    except discord.HTTPException:
        pass



#main async function that initializes and starts the bot
async def main():
    health_server = await start_health_server()
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    finally:
        await health_server.cleanup()


#entry point for the script
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
