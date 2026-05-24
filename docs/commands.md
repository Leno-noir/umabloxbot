# Commands

Command tracking for the bot.

## Command Reference

The bot does not shows the same commands in every server.
Commands that require discord ID can also work via mention (@User)

### Guild Visibility

- Main guild only: visible only in `Uma Portal`
- Observer guilds only: visible only in enabled allowed observer guilds (any server of umablox, game or community)
- Promotion guild only: visible only in `Umablox Universe` (WIP)
- Unknown guilds: Guilds that are not part of the ecosystem (if a random server adds the bot, they will not be able to use any commands)

- Shared settings: `/settings` exists in both `Uma Portal` and enabled observer guilds, but the panel  changes by guild type (uma portal gets an general settings for example, observer guild get only a channel configuration option)


### Blacklist Commands

All blacklist commands are main-guild-only (Uma Portal).

Type: Restricted -> Only admins on main guild (Uma Portal) can use the command
Type: Public -> Every person on that server can use that command with no restrictions

#### `/blacklist-add`

- Type: restricted
- Description: add a user to the blacklist
- Parameter: `discord_id` - Discord user ID
- Permissions required: `Ban Members`, or the configured blacklist manager role from main guild settings
- Flow:
	1. validate the Discord ID
	2. open the add to blacklist modal
	3. collect Roblox info, reason, and optional evidence
	4. save to database
	5. notify the main guild blacklist logs channel

#### `/blacklist-remove`

- Type: restricted
- Description: remove a user from the blacklist
- Parameter: `discord_id` - Discord user ID
- Permissions required: `Ban Members`, or the configured blacklist manager role from main guild settings
- Flow:
	1. validate the Discord ID
	2. confirm removal
	3. open the removal modal
	4. save removal reason
	5. notify the main guild blacklist logs channel

- Note: It does not totally remove the person from database, instead it makes the ban unactive, making so it saves the past entries from that blacklisted person

#### `/blacklist-info`

- Type: public inside main guild (Uma Portal)
- Description: look up the current blacklist status for a user
- Parameter: `discord_id` - Discord user ID
- Output:
	- current blacklist status
	- Roblox info
	- reason
	- evidence when available
	- date added
	- recent past entries

#### `/blacklist-list`

- Type: public inside main guild (Uma Portal)
- Description: list active blacklist entries
- Parameter: `page` - optional page number (if you want to load at page 2)

#### `/blacklist-history`

- Type: restricted
- Description: show the full blacklist history for a user
- Parameter: `discord_id` - Discord user ID
- Permissions required: `Ban Members`, or the configured blacklist manager role from main guild settings

#### `/blacklist-log`

- Type: restricted
- Description: show the global blacklist event log (every add/remove actions for tracking)
- Parameter: `page` - optional page number
- Permissions required: `Ban Members`, or the configured blacklist manager role from main guild settings

#### `/blacklist-panel`

- Type: public inside main guild
- Description: send the blacklist panel (can navigate between pages on this panel)

### Settings Command

#### `/settings`

- Type: administrator only
- Description: open the settings panel for the current guild type

##### In Main Guild

The full admin panel is shown.

In main guild, they are separated by 2 options

Main guild configs:

- configure blacklist settings
- configure promotion settings
- configure feedback settings
- configure networking settings

Allowed server configs:

- manage allowed observer servers (which servers are allowed to be an 'Observer Server')

##### In Observer Guilds

A reduced panel is shown.

Features:

- configure `blacklisted_users_join_alert_channel` (configures which channel the alert for blacklisted user joining is)

##### In Unknown Guilds

Access is denied.

### Placeholder Commands

These still exist as placeholders for future functions:

- `/funsies-ping`
- `/feedback-ping`
- `/networking-ping`
- `/promotion-ping`

### Permission Model

#### Public

- `/blacklist-info`
- `/blacklist-list`
- `/blacklist-panel`
- placeholder ping commands

#### Restricted Blacklist Management

- `/blacklist-add`
- `/blacklist-remove`
- `/blacklist-history`
- `/blacklist-log`

Requires:

- `Ban Members`
- or configured blacklist manager role

#### Administrator Only

- `/settings`

### Notes

- command visibility is synced by guild type (some need to be configured manually in server configs WIP)
- blacklist commands are blocked both by visibility and runtime checks
- observer guilds do not manage the blacklist
- observer guilds only receive join alerts for blacklisted users
