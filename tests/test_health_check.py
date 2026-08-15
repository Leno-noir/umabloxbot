import unittest
from unittest.mock import patch

from aiohttp.test_utils import make_mocked_request

import bot


class HealthCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_check_requires_discord_readiness(self):
        with patch.object(bot.bot, "is_ready", return_value=False):
            response = await bot.health_check(make_mocked_request("GET", "/health"))
        self.assertEqual(response.status, 503)
        self.assertEqual(response.body, b'{"status": "starting", "discord_ready": false}')

    async def test_health_check_returns_ok_when_discord_is_ready(self):
        with patch.object(bot.bot, "is_ready", return_value=True):
            response = await bot.health_check(make_mocked_request("GET", "/health"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, b'{"status": "ok", "discord_ready": true}')
