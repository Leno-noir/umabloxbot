# Commands

Commands are synchronized per server type. The main guild is Uma Portal;
enabled allowlisted servers are observers; all other servers receive only the
Funsies commands.

## Uma Portal

- `/blacklist add`, `/blacklist remove`, `/blacklist info`, `/blacklist list`,
  `/blacklist history`, `/blacklist event-log`, `/blacklist panel`
- `/settings`
- `/feedback panel`, `/feedback send`, `/feedback list`
- `/networking project-post`, `/networking dev-post`, `/networking list`,
  `/networking my-posts`
- All Funsies commands below

Blacklist write/history/log/panel commands require `Ban Members` or the
configured blacklist-manager role. Feedback management uses `Ban Members` or
the configured feedback-manager role. `/settings` requires Administrator at
Discord and runtime level.

## Observer servers

- `/settings`
- All Funsies commands

Observer settings configure local alerts only; they never expose central
blacklist management.

## Servers outside the allowlist

- `/quote`
- `/fact`
- `/gacha`
- `/gacha-info`
- `/uma-list`
- `/uma-info`
- `/uma-inventory`
- `/choose-your-race-uma`
- `/race`
- `/leaderboard`

## Development-only command

`/rotector-test-view` is available only when both `BOT_ENV=development` and
`ROTECTOR_ENABLED=true` are set. It is synchronized only to Uma Portal.
