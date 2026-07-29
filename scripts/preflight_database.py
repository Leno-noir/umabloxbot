"""Read-only production preflight for every index that enforces uniqueness."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any

from core.config import MONGODB_URI
from db.connection import connect, disconnect, get_db


@dataclass(frozen=True)
class UniqueCheck:
    collection: str
    fields: tuple[str, ...]
    match: dict[str, Any] | None = None
    correctable: bool = False


UNIQUE_CHECKS = {
    "blacklist.discord_id": UniqueCheck("blacklist", ("discord_id",)),
    "guild_configs.guild_id": UniqueCheck("guild_configs", ("guild_id",)),
    "allowed_guilds.guild_id": UniqueCheck("allowed_guilds", ("guild_id",)),
    "feedback_games.guild_id_name": UniqueCheck("feedback_games", ("guild_id", "name")),
    "funsies_settings.guild_id": UniqueCheck("funsies_settings", ("guild_id",)),
    "user_uma_inventory.unique_owned_uma": UniqueCheck(
        "user_uma_inventory",
        ("guild_id", "user_id", "uma_id"),
        match={"uma_id": {"$type": "objectId"}},
        correctable=True,
    ),
    "user_race_settings.guild_id_user_id": UniqueCheck(
        "user_race_settings", ("guild_id", "user_id")
    ),
    "gacha_daily_usage.guild_id_user_id_date": UniqueCheck(
        "gacha_daily_usage", ("guild_id", "user_id", "date")
    ),
}


class PreflightError(RuntimeError):
    """Raised when uniqueness preconditions are not safe for a migration."""


async def duplicate_count(database, check: UniqueCheck) -> int:
    group_id = {field: f"${field}" for field in check.fields}
    pipeline: list[dict] = []
    if check.match:
        pipeline.append({"$match": check.match})
    pipeline.extend(
        [
            {"$group": {"_id": group_id, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$count": "duplicates"},
        ]
    )
    result = await database[check.collection].aggregate(pipeline).to_list(length=1)
    return result[0]["duplicates"] if result else 0


async def build_preflight_report(database=None) -> dict[str, int]:
    if database is None:
        database = get_db()
    return {
        name: await duplicate_count(database, check)
        for name, check in UNIQUE_CHECKS.items()
    }


def blocking_preflight_entries(report: dict[str, int], *, allow_correctable_inventory: bool) -> dict[str, int]:
    return {
        name: count
        for name, count in report.items()
        if count and not (allow_correctable_inventory and UNIQUE_CHECKS[name].correctable)
    }


async def assert_funsies_preflight_before_migration(database=None) -> dict[str, int]:
    report = await build_preflight_report(database)
    blocked = blocking_preflight_entries(report, allow_correctable_inventory=True)
    if blocked:
        raise PreflightError(f"Funsies migration blocked by duplicate records: {json.dumps(blocked, sort_keys=True)}")
    return report


async def assert_all_unique_preconditions(database=None) -> dict[str, int]:
    report = await build_preflight_report(database)
    blocked = blocking_preflight_entries(report, allow_correctable_inventory=False)
    if blocked:
        raise PreflightError(f"Unique indexes cannot be created: {json.dumps(blocked, sort_keys=True)}")
    return report


async def main() -> int:
    argparse.ArgumentParser(description="Check MongoDB uniqueness preconditions").parse_args()
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is required for database preflight.")
    await connect()
    try:
        report = await build_preflight_report()
        print(json.dumps(report, sort_keys=True))
        return 1 if any(report.values()) else 0
    finally:
        await disconnect()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
