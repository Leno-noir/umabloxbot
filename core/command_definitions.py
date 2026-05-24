# Defines which commands belong to which feature/category and which guild types can access them.


# Command groups by feature/cog
COMMAND_GROUPS = {
    "blacklist": {
        "commands": [
            "blacklist-add",
            "blacklist-remove",
            "blacklist-info",
            "blacklist-list",
            "blacklist-history",
            "blacklist-log",
            "blacklist-panel",
        ],
        "manager_only": ["blacklist-add", "blacklist-remove", "blacklist-history", "blacklist-log", "blacklist-panel"],
    },
    "settings": {
        "commands": ["settings"],
        "manager_only": [],
    },
    "feedback": {
        "commands": ["feedback"],
        "manager_only": [],
    },
    "promotion": {
        "commands": ["promotion"],
        "manager_only": [],
    },
    "networking": {
        "commands": ["networking"],
        "manager_only": [],
    },
    "funsies": {
        "commands": ["fun"],
        "manager_only": [],
    },
}

# Guild type command access: which features are synced to each guild type
GUILD_TYPE_COMMANDS = {
    "main": {
        # Main guild receives everything
        "features": list(COMMAND_GROUPS.keys()),
    },
    "observer": {
        # Observer guilds only get settings (and eventually observer-specific commands)
        "features": ["settings"],
    },
    "promotion": {
        # Promotion guilds only get promotion commands (when implemented)
        "features": ["promotion"],
    },
}


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
