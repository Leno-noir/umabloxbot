import unittest
from unittest.mock import patch

from db.indexes import ensure_core_indexes


class FakeCollection:
    def __init__(self):
        self.calls = []

    async def create_index(self, keys, **kwargs):
        self.calls.append((keys, kwargs))


class FakeDatabase:
    def __init__(self):
        for name in (
            "blacklist",
            "guild_configs",
            "allowed_guilds",
            "feedback_games",
            "feedback_entries",
            "networking_posts",
        ):
            setattr(self, name, FakeCollection())


class DatabaseIndexTests(unittest.IsolatedAsyncioTestCase):
    async def test_core_indexes_cover_all_non_funsies_collections(self):
        database = FakeDatabase()
        with patch("db.indexes.get_db", return_value=database):
            await ensure_core_indexes()

        self.assertTrue(database.blacklist.calls[0][1]["unique"])
        self.assertTrue(database.guild_configs.calls[0][1]["unique"])
        self.assertTrue(database.allowed_guilds.calls[0][1]["unique"])
        self.assertTrue(database.feedback_games.calls[0][1]["unique"])
        self.assertEqual(len(database.feedback_entries.calls), 1)
        self.assertEqual(len(database.networking_posts.calls), 2)
