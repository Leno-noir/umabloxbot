# Commands Reference

Complete list of all slash commands available in the bot.

**Total Commands:** 12  
**Public Commands:** 7  
**Restricted Commands:** 5

---

## 📋 Blacklist Cog

Commands for managing the shared blacklist across servers.

### `/blacklist-add`
**Type:** Restricted (Manager only)  
**Description:** Add a user to the shared blacklist

**Parameters:**
- `discord_id` (text) — The Discord user ID to blacklist

**Permissions Required:**
- Ban Members permission OR UmaBot Blacklist Manager role

**Validation:**
- Discord ID is automatically validated and normalized

**Flow:**
1. User runs `/blacklist-add @user/@discordID`
2. Opens BlacklistAddModal form
3. User enters: Roblox ID, Roblox username, reason, evidence (optional)
4. User is added to blacklist
5. Alert sent to log channel

---

### `/blacklist-remove`
**Type:** Restricted (Manager only)  
**Description:** Remove a user from the blacklist

**Parameters:**
- `discord_id` (text) — The Discord user ID to remove

**Permissions Required:**
- Ban Members permission OR UmaBot Blacklist Manager role

**Validation:**
- Discord ID is automatically validated and normalized
- User must already be on the blacklist

**Flow:**
1. User runs `/blacklist-remove @user/@discordID`
2. Confirmation view appears (Yes/No buttons)
3. If confirmed, opens BlacklistRemoveModal
4. User enters removal reason
5. User is removed from blacklist
6. Alert sent to log channel

---

### `/blacklist-info`
**Type:** Public  
**Description:** Look up a user's blacklist status

**Parameters:**
- `discord_id` (text) — The Discord user ID to look up

**Output:**
- Shows current ban status
- If banned: reason, Roblox account, added by, date
- Past entries (last 5 if any)
- Link to Roblox profile (button)

**Validation:**
- Discord ID is automatically validated and normalized

---

### `/blacklist-history`
**Type:** Restricted (Manager only)  
**Description:** Show the full blacklist history for a user

**Parameters:**
- `discord_id` (text) — The Discord user ID to look up

**Permissions Required:**
- Ban Members permission OR UmaBot Blacklist Manager role

**Output:**
- Shows ALL blacklist records for the user
- Distinguishes between active bans and removal events
- Complete details for each event

**Validation:**
- Discord ID is automatically validated and normalized

---

### `/blacklist-list`
**Type:** Public  
**Description:** List all currently banned users

**Parameters:**
- `page` (integer, optional) — Page number (10 users per page) [default: 1]

**Output:**
- Paginated list of all currently banned users
- Shows: Roblox username, Discord mention, reason, date added

---

### `/blacklist-log`
**Type:** Restricted (Manager only)  
**Description:** Show the full blacklist event log

**Parameters:**
- `page` (integer, optional) — Page number (10 events per page) [default: 1]

**Permissions Required:**
- Ban Members permission OR UmaBot Blacklist Manager role

**Output:**
- Paginated global event log
- Shows all ban and removal actions across all servers
- Includes timestamps and user information

---

### `/blacklist-panel`
**Type:** Public  
**Description:** Send the blacklist panel with navigation buttons

**Parameters:** None

**Output:**
- Sends an embed with navigation buttons
- Quick access to blacklist commands
- Interactive UI for users

---

## ⚙️ Settings Cog

Bot configuration and server settings.

### `/settings`
**Type:** Restricted (Server Admin only)  
**Description:** View and edit bot settings for this server

**Permissions Required:**
- Administrator permission

**Features:**
- Configure blacklist log channel
- Configure promotion settings
- Configure feedback settings
- Configure networking settings

**Sections:**
- Blacklist Settings
- Promotion Settings
- Feedback Settings
- Networking Settings

---

## 🎉 Scaffold Commands

These are placeholder commands created during the scaffolding phase. They will be replaced with actual features.

### `/funsies-ping`
**Type:** Public  
**Description:** Temporary command used while scaffolding the funsies cog

---

### `/feedback-ping`
**Type:** Public  
**Description:** Temporary command used while scaffolding the feedback cog

---

### `/networking-ping`
**Type:** Public  
**Description:** Temporary command used while scaffolding the networking cog

---

### `/promotion-ping`
**Type:** Public  
**Description:** Temporary command used while scaffolding the promotion cog

---

## 📊 Command Statistics

| Category | Count |
|----------|-------|
| Blacklist Commands | 7 |
| Settings Commands | 1 |
| Scaffold Commands | 4 |
| **Total** | **12** |

| Permission Level | Count |
|------------------|-------|
| Public | 7 |
| Restricted (Manager) | 4 |
| Restricted (Admin) | 1 |
| **Total** | **12** |

---

## 🔐 Permission Levels

### Public Commands
Anyone can use these commands:
- `/blacklist-info`
- `/blacklist-list`
- `/blacklist-panel`
- `/funsies-ping`
- `/feedback-ping`
- `/networking-ping`
- `/promotion-ping`

### Manager-Only Commands
Requires Ban Members permission OR UmaBot Blacklist Manager role:
- `/blacklist-add`
- `/blacklist-remove`
- `/blacklist-history`
- `/blacklist-log`

### Admin-Only Commands
Requires Administrator permission:
- `/settings`

---

## 🔄 Command Flow Diagram

```
User Input (/command)
    ↓
@app_commands.command() decorator
    ↓
Permission Check (@is_manager, @default_permissions)
    ↓
Parameter Validation (@validate_discord_id)
    ↓
Command Function
    ↓
Database Operation
    ↓
Response (Embed, Modal, or View)
```

---

## 📝 Notes

- All commands with Discord IDs support multiple input formats:
  - Raw ID: `123456789`
  - Discord mention: `<@123456789>`
  - Mention format: `@username`

- All ephemeral responses are only visible to the command user

- Pagination defaults to page 1 if not specified

- More commands are planned for feedback, promotion, and networking cogs
