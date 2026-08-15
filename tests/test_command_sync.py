import unittest
from unittest.mock import AsyncMock, patch

from core.command_sync import sync_network_commands


class FakeTree:
    def __init__(self):
        self.cleared = []
        self.added = []
        self.global_commands = {
            "blacklist", "settings", "feedback", "networking", "quote", "fact",
            "gacha", "gacha-info", "uma-list", "uma-info", "uma-inventory",
            "choose-your-race-uma", "race", "leaderboard",
        }
        self.sync = AsyncMock(side_effect=lambda guild=None: [guild] if guild else [])
        self.fetch_commands = AsyncMock(return_value=["legacy-a", "legacy-b"])

    def clear_commands(self, *, guild=None):
        self.cleared.append(guild)
        if guild is None:
            self.global_commands.clear()

    def get_command(self, name):
        return name if name in self.global_commands else None

    def get_commands(self):
        return list(self.global_commands)

    def add_command(self, command, *, guild=None, override):
        if guild is None:
            self.global_commands.add(command)
        else:
            self.added.append((command, guild.id, override))


class FakeGuild:
    def __init__(self, guild_id, name):
        self.id = guild_id
        self.name = name


class FakeBot:
    def __init__(self):
        self.tree = FakeTree()
        self.guilds = [FakeGuild(1, "Main"), FakeGuild(2, "Observer"), FakeGuild(3, "Unknown")]


class CommandSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_cleanup_removes_globals_and_syncs_all_guild_types(self):
        bot = FakeBot()
        with patch(
            "core.command_sync.allowed_guild_list_enabled",
            AsyncMock(return_value=[{"guild_id": 2}]),
        ):
            report = await sync_network_commands(bot, 1, clear_global_commands=True)

        self.assertEqual(report["global_removed"], 2)
        self.assertEqual(report["main"], 1)
        self.assertEqual(report["observer:2"], 1)
        self.assertEqual(report["unknown:3"], 1)
        self.assertIn(None, bot.tree.cleared)

    async def test_normal_sync_rebuilds_only_the_global_application_command_tree(self):
        bot = FakeBot()
        with patch("core.command_sync.allowed_guild_list_enabled", AsyncMock(return_value=[])):
            await sync_network_commands(bot, 1)

        self.assertEqual(bot.tree.cleared.count(None), 2)
        bot.tree.fetch_commands.assert_not_awaited()
