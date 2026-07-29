# UMABLOX Bot

Discord bot for the Umablox community.

## What This Project Is

UMABLOX Bot is a Discord bot for a multi-server network that keeps moderation, notifications, feedback, dev networking, and server-specific configuration in one place.

It is organized around 3 server roles:

- **Uma Portal**
  - main administration server
  - has the full blacklist workflow
  - has the full dev networking workflow
  - has the full dev feedback workflow
  - has the central `/settings` panel
  - manages allowed observer servers


- **Other connected servers**
  - can participate as observer servers when allowed by the main guild
  - can receive blacklist notifications through their own configured log channels
  - can use fun commands

The bot uses MongoDB as database.

Supported Python versions: **3.11 and 3.12**.

## Core Features

- Shared blacklist with add, remove, info, history, list, panel, and log commands
- Observer server allowlist and enable/disable control
- Per-server settings stored in MongoDB
- Join alerts for blacklisted users in observer servers

## How the Network Works

The bot treats the main guild as the control center.

- The main guild shows the full blacklist management experience.
- Allowed observer guilds receive a reduced `/settings` panel.
- Unknown guilds do not get access.
- Blacklist read commands are public in the main guild, while write commands are restricted.
- When a blacklisted user joins an enabled observer server, that server can receive a notification in its configured alert channel.

This means moderation data is shared across the network, but local notification channels remain configurable per guild. (every server configures their own channel for it)

## Main Modules

- `bot.py`
  - application entry point
  - loads the cogs
  - starts the bot
  - handles events like member joins and command errors

- `core/`
  - shared configuration, utilities, and command sync helpers

- `db/`
  - MongoDB connection and persistence helpers
  - blacklist data
  - guild configuration data
  - allowlist data for connected observer servers

- `cogs/`

## Server Roles

### Uma Portal

This is the main control guild.

It is responsible for:

- blacklist moderation
- blacklist logs
- dev networking function
- feedback function
- allowlist management for observer servers
- full settings administration
- fun commands

### Observer Servers

These are connected servers approved by the main guild.

They can:

- use the reduced `/settings` panel
- configure their local blacklist join alert channel
- receive blacklist alerts when configured
- use fun commands

### Other Servers / Unknown Servers

Servers that are not allowlisted do not participate in the network settings flow and do not receive observer-only features.
They will be able to use fun commands as their only function.



## Environment Variables

### Required Variables

**`DISCORD_TOKEN`**
- Discord bot token
- Create it in the Discord Developer Portal
CAREFUL!! do not give this token to anyone (people can access your account through this)

Start from `.env.example`; never commit the populated `.env` file.

**`MONGODB_URI`**
- MongoDB connection string
- Example format:
  `mongodb+srv://username:password@cluster.mongodb.net/?appName=appname`

**`MAIN_GUILD_ID`**
- The Discord server ID for `Uma Portal`
- This is the bot's main management guild

**`BOT_ENV`** (optional)
- Set to `development` only in a development deployment.
- Enables development-only commands, including `/rotector-test-view`, which is restricted to Uma Portal.

**`ROTECTOR_ENABLED`** (optional)
- Defaults to `false`, so Rotection does not start or call its API.
- Set to `true` to enable Rotection again.

Boolean environment variables accept `1`, `true`, `yes`, or `on` (case-insensitive).


---

## Commands

See [commands.md](commands.md) for the current command names and per-server visibility.

---

## Bot Permissions

See [bot-permissions.md](bot-permissions.md) for least-privilege invite URLs
and the required permissions for Uma Portal, observer servers, and unknown
servers.

## Deployment checklist

1. Install exact dependencies with `python -m pip install -r docs/requirements.txt`.
2. Set the required environment variables and keep `ROTECTOR_ENABLED=false` unless Rotection is intentionally enabled.
3. Stop the running bot and execute `python -m scripts.cleanup_global_commands --confirm-bot-stopped` once when migrating from a legacy global-command deployment.
4. Take and verify a MongoDB backup before a release that includes a data migration.
5. Run `python -m scripts.preflight_database` and resolve every reported duplicate before creating unique indexes in production.
6. Run `python -m scripts.migrate_funsies --backup-id <verified-backup-id> --confirm-backup <verified-backup-id>` during a maintenance window when required. Migrations never run during regular bot startup.
7. If migration fails, keep the bot stopped and restore the verified MongoDB backup before retrying.
8. Start the bot once; command synchronization happens during process initialization, not on every reconnect.
9. Confirm the GitHub Actions unit and MongoDB integration jobs are green before deployment.

`preflight_database` checks the core collections plus Funsies settings,
inventory ownership, race selections, and daily gacha usage. Inventory
duplicates are the only Funsies duplicates the migration may consolidate
automatically; all others must be resolved before the migration starts.

---
