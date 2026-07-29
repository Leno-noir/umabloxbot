import unittest
from unittest.mock import AsyncMock, patch

from scripts.preflight_database import PreflightError
from db import funsies


class FunsiesMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_migration_aborts_before_writes_when_preflight_fails(self):
        with patch("db.funsies.get_db"), patch(
            "scripts.preflight_database.assert_funsies_preflight_before_migration",
            AsyncMock(side_effect=PreflightError("duplicates")),
        ), patch("db.funsies.funsies_migrate_global_settings", AsyncMock()) as migrate_settings:
            with self.assertRaises(PreflightError):
                await funsies.run_funsies_migrations()

        migrate_settings.assert_not_awaited()
