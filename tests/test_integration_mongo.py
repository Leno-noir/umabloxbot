"""MongoDB integration tests. Skipped locally unless MONGODB_TEST_URI is set."""

import os
import unittest

from motor.motor_asyncio import AsyncIOMotorClient

from db import connection
from db.allowed_guilds import allowed_guild_add, allowed_guild_is_enabled
from db.blacklist import bl_add, bl_get
from db.feedback import feedback_add_game, feedback_get_game
from db.funsies import fact_add, fact_list
from db.networking import create_dev_post, get_user_active_dev_post


@unittest.skipUnless(os.getenv("MONGODB_TEST_URI"), "MONGODB_TEST_URI is not configured")
class MongoIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncIOMotorClient(os.environ["MONGODB_TEST_URI"])
        await self.client.admin.command("ping")
        self.previous_client = connection._client
        connection._client = self.client
        self.database = connection.get_db()
        for collection in (
            "allowed_guilds", "blacklist", "feedback_games", "uma_facts", "networking_posts"
        ):
            await self.database.drop_collection(collection)

    async def asyncTearDown(self):
        for collection in (
            "allowed_guilds", "blacklist", "feedback_games", "uma_facts", "networking_posts"
        ):
            await self.database.drop_collection(collection)
        connection._client = self.previous_client
        self.client.close()

    async def test_feature_storage_round_trips(self):
        await allowed_guild_add(2, "Observer", "test")
        self.assertTrue(await allowed_guild_is_enabled(2))

        await bl_add("10", "20", "RobloxUser", "reason", "moderator")
        self.assertEqual((await bl_get("10"))["roblox_id"], "20")

        await feedback_add_game(1, "Game", "Role", 3, 4)
        self.assertIsNotNone(await feedback_get_game(1, "Game"))

        await fact_add(1, "A fact")
        self.assertEqual(len(await fact_list(1)), 1)

        await create_dev_post(1, 10, "Developer", 100, 200, "builder", "Available", None, None)
        self.assertIsNotNone(await get_user_active_dev_post(1, 10))
