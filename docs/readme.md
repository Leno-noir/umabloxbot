# UMABLOX Bot - Blacklist Module

Shared blacklist management bot for Discord servers using Roblox integration.

## Quick Start

### Prerequisites
- Python 3.10+
- Discord Bot Token
- MongoDB Atlas account (free tier available)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/umabloxbot.git
   cd umabloxbot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and fill in your credentials
   # (See instructions below)
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

---

## Environment Variables (`.env`)

**⚠️ IMPORTANT:** Never commit `.env` to Git. Use `.env.example` as a template.

### Required Variables

**`DISCORD_TOKEN`** (string)
- Discord bot token
- Get it from: https://discord.com/developers/applications

**`MONGODB_URI`** (string)
- MongoDB connection string
- Format: `mongodb+srv://username:password@cluster.mongodb.net/?appName=appname`

**`MAIN_GUILD_ID`** (integer)
- Main Discord server ID (Uma Portal)
- Enable Developer Mode in Discord settings
- Right-click server name → "Copy Server ID"
- Example: `1504205705245102172`

### Optional Variables

Currently all settings are managed via the `/settings` command, which stores configuration in MongoDB. No additional `.env` variables needed.


---

## Bot Permissions

When inviting the bot to servers, grant these permissions:
- ✅ Send Messages
- ✅ Embed Links
- ✅ View Channels
- ✅ Read Message History

---

## Commands

See [commands.md](commands.md) for a complete list of all available commands.

### Quick Reference

| Command | Description | Permission |
|---|---|---|
| `/blacklist-add` | Add a user to the blacklist | Ban Members or Blacklist Manager role |
| `/blacklist-remove` | Remove a user from the blacklist | Ban Members or Blacklist Manager role |
| `/blacklist-info` | Check a user's blacklist status | Public |
| `/blacklist-list` | List all banned users (paginated) | Public |
| `/blacklist-history` | Show complete history for a user | Ban Members or Blacklist Manager role |
| `/blacklist-log` | Show global event log | Ban Members or Blacklist Manager role |
| `/blacklist-panel` | Send navigation panel | Public |
| `/settings` | Configure bot settings | Server Administrator |

---

## Project Structure

```
.
├── bot.py                          # Main bot entry point
├── .env                            # Local credentials (gitignored)
├── .gitignore                      # Git ignore rules
│
├── core/                           # Core configuration and utilities
│   ├── __init__.py
│   ├── config.py                   # Configuration loader
│   └── utils.py                    # Global utility functions
│
├── db/                             # Database layer
│   ├── __init__.py
│   ├── connection.py               # MongoDB connection
│   ├── guild_configs.py            # Guild settings
│   └── blacklist.py                # Blacklist operations
│
├── cogs/                           # Discord command modules
│   ├── blacklist/                  # Blacklist management
│   ├── settings/                   # Server settings UI
│   ├── feedback/                   # Feedback system (WIP)
│   ├── promotion/                  # Promotion features (WIP)
│   ├── networking/                 # Networking features (WIP)
│   └── funsies/                    # Fun commands (WIP)
│
└── docs/                           # Documentation
    ├── readme.md                   # Setup and usage guide
    ├── commands.md                 # Complete command reference
    ├── thingstoknowabout.md        # Discord.py concepts
    ├── .env.example                # Environment template
    └── requirements.txt            # Python dependencies
```

---

### Testing

Run the bot locally:
```bash
python bot.py
```

Check for errors in the terminal output.

---

## Troubleshooting

### "MongoDB connected" error
- Check your `MONGODB_URI` in `.env`
- Verify network access is allowed in MongoDB Atlas (should be `0.0.0.0/0`)
- Ensure your username/password are correct

### Commands not appearing in Discord
- Try the force sync: The bot automatically clears and resyncs commands on startup
- Wait 5-10 seconds after bot starts
- Close and reopen Discord client

### "You do not have permission" error
- Ensure you have "Ban Members" permission or assigned Blacklist Manager role
- Check server member role hierarchy
