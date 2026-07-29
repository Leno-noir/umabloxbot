# Bot permissions by server type

Use the least-privilege invite URL for the server type. Replace
`CLIENT_ID` with the Discord application/client ID of this bot.

Every invite URL must include both scopes:

```text
scope=bot%20applications.commands
```

Channel overrides can still block the bot. Grant the listed permissions in
each channel where the bot must send or update a message.

## Uma Portal (main guild)

Required permissions:

- View Channels
- Send Messages
- Embed Links
- Read Message History
- Use Application Commands
- Manage Threads
- Create Private Threads
- Send Messages in Threads

These cover public blacklist/feedback panels, their rehydration after a
restart, and the private feedback threads created by the settings flow.

Invite URL:

```text
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot%20applications.commands&permissions=362924821504
```

Optional:

- Mention Everyone — only if feedback role mentions must work even when the
  selected role is not mentionable. Prefer making the relevant role
  mentionable instead.

The bot does **not** need Administrator, Manage Roles, Ban Members, Kick
Members, or Manage Messages. The `/ban` text shown by Rotection is only a
copyable suggestion; it does not ban users itself.

## Observer server

Required permissions:

- View Channels
- Send Messages
- Embed Links
- Use Application Commands

These are sufficient for `/settings`, Funsies, and configured blacklist or
Rotection alert channels. Rotection is disabled by default, but the alert
permissions are the same when it is enabled.

Invite URL:

```text
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot%20applications.commands&permissions=2147503104
```

Grant the same channel permissions directly to the selected alert channel;
server-level permissions alone do not override an explicit channel deny.

## Unknown server

Unknown servers receive only Funsies commands. Required permissions:

- View Channels
- Send Messages
- Embed Links
- Use Application Commands

Invite URL:

```text
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot%20applications.commands&permissions=2147503104
```

No moderation, settings, history, or thread permissions are required for this
server type.

## Gateway intents

The invite URL does not grant intents. The bot uses the **Server Members
Intent** for join alerts; enable it in the Discord Developer Portal before
using blacklist or Rotection join monitoring.
