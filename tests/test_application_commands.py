import unittest

from cogs.funsies.cog import Funsies
from core.application_commands import is_application_command


class ApplicationCommandTests(unittest.TestCase):
    def test_funsies_commands_are_marked_for_user_installation_and_dms(self):
        for name in ("quote", "fact", "gacha"):
            command = getattr(Funsies, name)
            self.assertTrue(is_application_command(command), name)
            self.assertTrue(command.allowed_contexts.guild, name)
            self.assertTrue(command.allowed_contexts.dm_channel, name)
            self.assertTrue(command.allowed_contexts.private_channel, name)
            self.assertTrue(command.allowed_installs.guild, name)
            self.assertTrue(command.allowed_installs.user, name)
