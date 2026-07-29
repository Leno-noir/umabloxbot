"""One-time maintenance command for migrating legacy global slash commands.

Stop the production bot first. This utility connects as the bot, clears only
global commands, and then rebuilds every guild's scoped command set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from discord.ext import commands

from bot import COGS, intents
from core import DISCORD_TOKEN, MAIN_GUILD_ID, sync_network_commands, validate_runtime_config
from db.connection import connect, disconnect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove legacy global Discord commands once")
    parser.add_argument(
        "--confirm-bot-stopped",
        action="store_true",
        help="Required acknowledgement that the normal production bot is stopped",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if not args.confirm_bot_stopped:
        raise RuntimeError("Refusing to run: stop the production bot and pass --confirm-bot-stopped.")

    maintenance_bot = commands.Bot(command_prefix="!", intents=intents)
    connection_task: asyncio.Task | None = None
    try:
        validate_runtime_config()
        await connect()
        for extension in COGS:
            await maintenance_bot.load_extension(extension)
        await maintenance_bot.login(DISCORD_TOKEN)
        connection_task = asyncio.create_task(maintenance_bot.connect())
        await maintenance_bot.wait_until_ready()
        report = await sync_network_commands(
            maintenance_bot,
            MAIN_GUILD_ID,
            clear_global_commands=True,
        )
        logging.info("Command cleanup report: %s", json.dumps(report, sort_keys=True))
    finally:
        await maintenance_bot.close()
        if connection_task:
            await asyncio.gather(connection_task, return_exceptions=True)
        await disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
