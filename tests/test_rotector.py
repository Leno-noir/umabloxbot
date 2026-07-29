import unittest

from cogs.rotector import RotectorJoinAlertView


class RotectorViewTests(unittest.TestCase):
    def test_preview_supports_discord_id_without_cached_member(self):
        view = RotectorJoinAlertView(
            None,
            roblox_id="123",
            roblox_user="TestUser",
            payload={"flagType": 1, "reasons": ["test"]},
            discord_id=123456789,
            guild_name="Uma Portal",
        )
        self.assertEqual(view.discord_id, 123456789)
        self.assertEqual(view.timeout, 900)
