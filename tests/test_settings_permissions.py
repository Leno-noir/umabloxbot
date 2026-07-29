import unittest

from cogs.settings.sections.base import AdminSettingsView


class FakeResponse:
    def __init__(self):
        self.messages = []

    def is_done(self):
        return False

    async def send_message(self, message, *, ephemeral):
        self.messages.append((message, ephemeral))


class FakeInteraction:
    def __init__(self, administrator):
        self.user = type("User", (), {"guild_permissions": type("Permissions", (), {"administrator": administrator})()})()
        self.response = FakeResponse()


class SettingsPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_admin_is_blocked_from_settings_callbacks(self):
        view = AdminSettingsView()
        interaction = FakeInteraction(administrator=False)
        self.assertFalse(await view.interaction_check(interaction))
        self.assertEqual(interaction.response.messages, [("Administrator permission is required.", True)])

    async def test_admin_is_allowed_to_use_settings_callbacks(self):
        view = AdminSettingsView()
        self.assertTrue(await view.interaction_check(FakeInteraction(administrator=True)))
