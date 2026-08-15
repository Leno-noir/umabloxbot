"""Helpers for commands that can be installed on a Discord user account."""

from typing import TypeVar

from discord import app_commands


T = TypeVar("T")
APPLICATION_COMMAND_MARKER = "__uma_portal_application_command__"


def application_command(command: T) -> T:
    """Mark a slash command as globally available to user-installed apps.

    The marker is consumed by the command synchronizer, which publishes only
    these commands globally.  Guild command copies keep their current
    visibility rules while the global copy can be used in DMs and group DMs.
    """

    command = app_commands.allowed_contexts(
        guilds=True,
        dms=True,
        private_channels=True,
    )(command)
    command = app_commands.allowed_installs(guilds=True, users=True)(command)
    setattr(command, APPLICATION_COMMAND_MARKER, True)
    return command


def is_application_command(command: object) -> bool:
    """Return whether an app-command object was marked for global syncing."""

    callback = getattr(command, "callback", None)
    return bool(
        getattr(command, APPLICATION_COMMAND_MARKER, False)
        or getattr(callback, APPLICATION_COMMAND_MARKER, False)
    )
