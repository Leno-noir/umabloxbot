import unittest
from unittest.mock import AsyncMock, patch

from scripts.preflight_database import (
    PreflightError,
    APPLICATION_UNIQUE_CHECKS,
    UNIQUE_CHECKS,
    assert_funsies_preflight_before_migration,
    build_application_preflight_report,
    build_preflight_report,
)


class FakeCursor:
    def __init__(self, duplicates):
        self.duplicates = duplicates

    async def to_list(self, *, length):
        return [{"duplicates": self.duplicates}] if self.duplicates else []


class FakeCollection:
    def __init__(self, duplicates):
        self.duplicates = duplicates

    def aggregate(self, pipeline):
        return FakeCursor(self.duplicates)


class FakeDatabase:
    def __init__(self, duplicates_by_collection=None, checks=UNIQUE_CHECKS):
        duplicates_by_collection = duplicates_by_collection or {}
        self.collections = {
            check.collection: FakeCollection(duplicates_by_collection.get(name, 0))
            for name, check in checks.items()
        }

    def __getitem__(self, name):
        return self.collections[name]


class PreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_inventory_duplicates_are_reported_but_permitted_before_migration(self):
        database = FakeDatabase({"user_uma_inventory.unique_owned_uma": 2})
        report = await assert_funsies_preflight_before_migration(database)
        self.assertEqual(report["user_uma_inventory.unique_owned_uma"], 2)

    async def test_other_funsies_duplicates_abort_before_migration(self):
        database = FakeDatabase({"gacha_daily_usage.guild_id_user_id_date": 1})
        with self.assertRaises(PreflightError):
            await assert_funsies_preflight_before_migration(database)

    async def test_report_includes_every_unique_check(self):
        report = await build_preflight_report(FakeDatabase())
        self.assertEqual(set(report), set(UNIQUE_CHECKS))

    async def test_application_report_includes_every_application_unique_check(self):
        report = await build_application_preflight_report(
            FakeDatabase(checks=APPLICATION_UNIQUE_CHECKS)
        )
        self.assertEqual(set(report), set(APPLICATION_UNIQUE_CHECKS))
