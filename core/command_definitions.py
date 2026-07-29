# Defines which commands belong to which feature/category and which guild types can access them.

from .config import IS_DEVELOPMENT


# Command groups by feature/cog
COMMAND_GROUPS = {
    "blacklist": {
        "commands": ["blacklist"],
        "manager_only": [],
    },
    "settings": {
        "commands": ["settings"],
        "manager_only": [],
    },
    "feedback": {
        "commands": ["feedback"],
        "manager_only": [],
    },
    "networking": {
        "commands": ["networking"],
        "manager_only": [],
    },
    "funsies": {
        "commands": [
            "quote",
            "fact",
            "gacha",
            "gacha-info",
            "uma-list",
            "uma-info",
            "uma-inventory",
            "choose-your-race-uma",
            "race",
            "leaderboard",
        ],
        "manager_only": [],
    },
}

# Guild type command access: which features are synced to each guild type
GUILD_TYPE_COMMANDS = {
    "main": {
        "features": ["blacklist", "settings", "feedback", "networking", "funsies"],
    },
    "observer": {
        # Observer guilds get settings plus the light funsies commands.
        "features": ["settings", "funsies"],
    },
    "unknown": {
        "features": ["funsies"],
    },
}

if IS_DEVELOPMENT:
    COMMAND_GROUPS["rotector_test"] = {
        "commands": ["rotector-test-view"],
        "manager_only": [],
    }
    GUILD_TYPE_COMMANDS["main"]["features"].append("rotector_test")


def get_commands_for_guild_type(guild_type: str) -> list[str]:
    """Return all command names for a given guild type."""
    if guild_type not in GUILD_TYPE_COMMANDS:
        return []
    
    features = GUILD_TYPE_COMMANDS[guild_type]["features"]
    commands = []
    for feature in features:
        if feature in COMMAND_GROUPS:
            commands.extend(COMMAND_GROUPS[feature]["commands"])
    return commands


def get_manager_only_commands() -> list[str]:
    """Return all commands that require manager role."""
    manager_commands = []
    for group in COMMAND_GROUPS.values():
        manager_commands.extend(group["manager_only"])
    return manager_commands
