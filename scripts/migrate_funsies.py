"""Run Funsies data migrations during a planned maintenance window.

Take and verify a MongoDB backup first. This script refuses to run without a
human-supplied backup identifier so it cannot be started accidentally.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from core.config import MONGODB_URI
from db.connection import connect, disconnect
from db.funsies import run_funsies_migrations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run explicit Funsies migrations")
    parser.add_argument(
        "--backup-id",
        required=True,
        help="Identifier or timestamp of a verified MongoDB backup",
    )
    parser.add_argument(
        "--confirm-backup",
        required=True,
        help="Repeat the exact backup ID after verifying that backup can be restored",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.confirm_backup != args.backup_id:
        raise RuntimeError("--confirm-backup must exactly match --backup-id.")
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is required to run migrations.")

    logging.info("Starting Funsies migration using verified backup %s", args.backup_id)
    await connect()
    try:
        report = {
            "backup_id": args.backup_id,
            "migration": await run_funsies_migrations(),
        }
        logging.info("Funsies migration report: %s", json.dumps(report, sort_keys=True))
    finally:
        await disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
