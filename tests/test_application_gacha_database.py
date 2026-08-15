import unittest
from unittest.mock import patch

from db.funsies import ensure_application_gacha_indexes


class FakeCollection:
    def __init__(self):
        self.calls = []

    async def create_index(self, keys, **kwargs):
        self.calls.append((keys, kwargs))


class FakeApplicationDatabase:
    def __init__(self):
        self.gacha_daily_usage = FakeCollection()
        self.user_uma_inventory = FakeCollection()


class ApplicationGachaDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_application_database_has_its_own_usage_and_inventory_indexes(self):
        database = FakeApplicationDatabase()
        with patch("db.funsies.get_application_db", return_value=database):
            await ensure_application_gacha_indexes()

        usage_keys, usage_options = database.gacha_daily_usage.calls[0]
        inventory_keys, inventory_options = database.user_uma_inventory.calls[0]
        self.assertEqual(usage_keys, [("user_id", 1), ("date", 1)])
        self.assertTrue(usage_options["unique"])
        self.assertEqual(inventory_keys, [("user_id", 1), ("uma_id", 1)])
        self.assertTrue(inventory_options["unique"])
