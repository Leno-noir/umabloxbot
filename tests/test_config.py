import unittest
from unittest.mock import patch

from core import config


class ConfigTests(unittest.TestCase):
    def test_env_flag_accepts_documented_true_values(self):
        for value in ("1", "true", "YES", "on"):
            with patch.dict("os.environ", {"TEST_FLAG": value}, clear=False):
                self.assertTrue(config.env_flag("TEST_FLAG"))

    def test_env_flag_rejects_unknown_values(self):
        with patch.dict("os.environ", {"TEST_FLAG": "maybe"}, clear=False):
            self.assertFalse(config.env_flag("TEST_FLAG", default=True))

    def test_validate_runtime_config_rejects_missing_values(self):
        with patch.multiple(config, DISCORD_TOKEN=None, MONGODB_URI=None, MAIN_GUILD_ID=0):
            with self.assertRaisesRegex(RuntimeError, "DISCORD_TOKEN"):
                config.validate_runtime_config()

