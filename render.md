# Deploying on Render

The bot is hosted as a free **Web Service** and kept active by an external
monitor. It exposes only `GET /health`; it does not provide a web dashboard or
public API.

> Render does not offer free Background Workers. The `render.yaml` file uses a
> free Web Service, which spins down after 15 minutes without inbound HTTP
> traffic.

## Before deployment

1. Push this repository to GitHub without the `.env` file.
2. Create and verify a MongoDB backup.
3. In the Discord Developer Portal, enable **Server Members Intent** under
   *Bot > Privileged Gateway Intents*.
4. Invite the bot with the `bot` and `applications.commands` scopes. See
   [docs/bot-permissions.md](docs/bot-permissions.md) for permissions by server type.
5. Confirm that GitHub Actions is passing. The Blueprint deploys only after
   those checks pass.

## Create the service from the Blueprint

1. In the Render dashboard, select **New + > Blueprint** and connect the
   repository.
2. Render detects [render.yaml](render.yaml) and creates `uma-portal-bot` as a
   free Web Service.
3. Set the environment variables below. Never commit tokens, MongoDB URIs, or
   other secrets to Git.
4. Create the service and follow the logs until `Bot online as ...` appears.

The Blueprint installs the pinned dependencies from `docs/requirements.txt`
and runs `python bot.py`. The bot serves `GET /health` on Render's automatically
provided `PORT`, uses Python 3.12, and keeps Rotection disabled in production.

## Environment variables

| Variable | Required | Production value |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | The bot token from the Discord Developer Portal. |
| `MONGODB_URI` | Yes | MongoDB/Atlas connection string, with access from Render enabled. |
| `MAIN_GUILD_ID` | Yes | Numeric Discord ID of the Uma Portal server. |
| `BOT_ENV` | No | `production` (already set by the Blueprint). |
| `ROTECTOR_ENABLED` | No | `false` (already set by the Blueprint). |
| `ROTECTOR_API_KEY` | Only if Rotection is enabled | Rotection service key. |
| `ROTECTOR_API_BASE_URL` | No | Change only if Rotection's default URL changes. |

If your Atlas cluster uses an IP access list, allow connections originating
from Render according to your cluster network policy. Prefer a dedicated
MongoDB user with access only to the database the bot needs.

## Monitor to keep the service active

After the first deployment, copy the public Render URL, for example:

```text
https://uma-portal-bot.onrender.com/health
```

Configure an external monitor to send an **HTTP GET** request to this URL every
5 to 10 minutes. UptimeRobot, Better Stack, or an equivalent service can be
used. Do not use `/robots.txt`: while the service is suspended, Render responds
to that path without starting the application.

The monitor does not guarantee availability: if it stops, the bot spins down
after 15 minutes and only returns after a new request. The endpoint returns
`200` with `discord_ready: true` after the bot finishes connecting to Discord.

## First deployment and legacy commands

If an older version of the bot used global commands, complete this step **once**
with the production service stopped. Run it on a trusted machine with the same
three required environment variables configured:

```powershell
python -m scripts.cleanup_global_commands --confirm-bot-stopped
```

Then start or redeploy the service on Render. Do not run this script as a build,
start, or pre-deploy command.

## Data migrations

Migrations do not run during startup. When a release requires one, schedule a
maintenance window, stop the service, and follow the procedure in
[docs/readme.md](docs/readme.md#deployment-checklist): preflight, verified
backup, manual migration, and validation before starting the bot again.

## Operations

- To update: push a commit to the connected branch; Render deploys after CI
  passes.
- To change a secret: update it under **Environment** in Render, then redeploy.
  You do not need to edit `render.yaml`.
- To stop the bot: suspend the Web Service in Render. This is required before
  maintenance tasks that require the bot to be stopped.
- Data remains in MongoDB; Render's filesystem is not used for persistence.
