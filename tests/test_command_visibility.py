import unittest

from core.command_definitions import get_commands_for_guild_type


class CommandVisibilityTests(unittest.TestCase):
    def test_main_has_management_and_funsies_commands(self):
        commands = get_commands_for_guild_type("main")
        self.assertIn("blacklist", commands)
        self.assertIn("settings", commands)
        self.assertIn("choose-your-race-uma", commands)

    def test_observer_has_no_blacklist_management(self):
        commands = get_commands_for_guild_type("observer")
        self.assertNotIn("blacklist", commands)
        self.assertIn("quote", commands)

    def test_unknown_has_only_funsies_commands(self):
        self.assertEqual(
            get_commands_for_guild_type("unknown"),
            [
                "quote", "fact", "gacha", "gacha-info", "uma-list", "uma-info",
                "uma-inventory", "choose-your-race-uma", "race", "leaderboard",
            ],
        )
