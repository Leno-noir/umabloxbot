# UMABLOX Bot

Discord bot for the Umablox community.

## What This Project Is

UMABLOX Bot is a Discord bot for a multi-server network that keeps moderation, notifications, helps on promoting, feedback, devs networking and server-specific configuration in one place.

It is organized around 3 server roles:

- **Uma Portal**
  - main administration server
  - has the full blacklist workflow
  - has the full dev networking workflow
  - has the full dev feedback workflow
  - has the central `/settings` panel
  - manages allowed observer servers

- **Umablox Universe**
  - main promotion server
  - used for features like promotion and fun commands

- **Other connected servers**
  - can participate as observer servers when allowed by the main guild
  - can receive blacklist notifications through their own configured log channels
  - can use fun commands

The bot uses MongoDB as database.
the bot uses WIP as hosting

## Core Features

- Shared blacklist with add, remove, info, history, list, panel, and log commands
- Observer server allowlist and enable/disable control
- Per-server settings stored in MongoDB
- Join alerts for blacklisted users in observer servers
- Cogs for blacklist, settings, feedback, promotion, networking, and fun features

## How the Network Works

The bot treats the main guild as the control center.

- The main guild shows the full blacklist management experience.
- Allowed observer guilds receive a reduced `/settings` panel.
- Unknown guilds do not any access.
- Blacklist read commands are public in the main guild, while write commands are restricted. (some exceptions)
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
  - feature modules for blacklist, settings, feedback, promotion, networking, and funsies

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

### Umablox Universe

This is the guild for promotion functions

It has:

 - promotion function
 - fun commands

### Observer Servers

These are connected servers approved by the main guild. (in the allowlist)

They can:

- use the reduced `/settings` panel
- configure their local blacklist join alert channel
- receive blacklist alerts when configured
- use fun commands

### Other Servers / Unknown Servers

Servers that are not allowlisted do not participate in the network settings flow and do not receive observer-only features.

They will be able to use fun commands as their only function



## Environment Variables

### Required Variables

**`DISCORD_TOKEN`**
- Discord bot token
- Create it in the Discord Developer Portal
CAREFUL!! do not give this token to anyone (people can access your account through this)

**`MONGODB_URI`**
- MongoDB connection string
- Example format:
  `mongodb+srv://username:password@cluster.mongodb.net/?appName=appname`

**`MAIN_GUILD_ID`**
- The Discord server ID for `Uma Portal`
- This is the bot's main management guild


---

## Command Groups

The current command surface is split by purpose:

- **Blacklist**
  - `/blacklist-add`
  - `/blacklist-remove`
  - `/blacklist-info`
  - `/blacklist-list`
  - `/blacklist-panel`
  - `/blacklist-history`
  - `/blacklist-log`

- **Settings**
  - `/settings`

- **Future or placeholder modules**
  - promotion
  - networking
  - funsies

---

## Bot Permissions

When inviting the bot, grant at least: (WIP MIGHT NEED MORE PERMISSIONS)
- Send Messages
- Embed Links
- View Channels
- Read Message History

To join alerts work:
- make sure the bot can see and send messages in the configured observer alert channel

---
