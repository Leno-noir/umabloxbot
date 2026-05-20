
# Discord Bot Development Guide

## Table of Contents
1. [App Commands](#app-commands)
2. [Ephemeral Messages](#ephemeral-messages)
3. [Custom Decorators](#custom-decorators)
4. [Embeds](#embeds)
5. [Defer](#defer)
6. [Discord Timestamps](#discord-timestamps)
7. [Permissions and Checks](#permissions-and-checks)

---

## App Commands

### Overview
App commands are slash commands (e.g., `/blacklist-add`) that appear in Discord chat when typing.

### @app_commands.command()
Creates a new slash command with a name and description.

**Parameters:**
- `name` - Command name (appears as `/name`)
- `description` - Description shown in Discord's autocomplete interface
- `interaction` - Object representing the user's interaction with the command

**Example:**
```python
@app_commands.command(name="ping", description="Get latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")
```

### @app_commands.describe()
Adds parameter descriptions that appear when users interact with the command.

**Example:**
```python
@app_commands.describe(discord_id="The Discord user ID to blacklist")
```

This shows a helpful description when the user inputs the `discord_id` parameter.

---

## Ephemeral Messages

### What Are Ephemeral Messages?
Messages that are only visible to the user who triggered the command. They disappear after approximately 15 minutes.

**Key Point:** `ephemeral=True` ensures privacy for sensitive information.

**Example:**
```python
await interaction.response.send_message(
    "This Discord ID is not on the blacklist.", 
    ephemeral=True
)
```

---

## Custom Decorators

Custom decorators eliminate code duplication by encapsulating common validation and permission logic.

### @is_manager()
Restricts command access to users with the "Ban Members" permission or a custom role.

- Returns an error message if the user lacks proper permissions
- Command execution is prevented automatically

**Example:**
```python
@app_commands.command(name="blacklist-add", description="Add a user to the blacklist")
@is_manager()
async def blacklist_add(self, interaction: discord.Interaction, discord_id: str):
    # Only managers can execute this command
    pass
```

### @validate_discord_id()
Normalizes and validates a Discord ID before passing it to the command.

- Sends an error message automatically if the ID is invalid
- Passes the formatted ID to the command function if valid

**Example:**
```python
@app_commands.command(name="blacklist-info", description="Look up a user")
@validate_discord_id()
async def blacklist_info(self, interaction: discord.Interaction, formated_discord_id: str):
    # The discord_id parameter has already been validated and normalized
    pass
```

---

## Embeds

Embeds are richly formatted messages with colors, titles, fields, and other visual elements.

### Basic Structure
```python
embed = discord.Embed(
    title="Title here",
    description="Description here",
    color=Colors.RED,  # or use hex color (0xFF0000)
)
```

### Adding Fields
```python
embed.add_field(name="Field Title", value="Field content", inline=False)
# inline=False: field takes full width
# inline=True: multiple fields can appear on the same row
```

### Setting Footer
```python
embed.set_footer(text="Footer text here")
```

### Setting Images
```python
embed.set_thumbnail(url="image_url")  # Small image
embed.set_image(url="image_url")      # Large image
```

### Complete Example
```python
embed = discord.Embed(
    title=f"Blacklist info - {user_name}",
    description="CURRENTLY BANNED",
    color=Colors.RED,
)
embed.add_field(name="Reason", value="Exploiting", inline=False)
embed.add_field(name="Added by", value="Moderator#1234", inline=False)
embed.set_footer(text="Page 1/3")
await interaction.response.send_message(embed=embed)
```

---

## Defer

Defers a response when a command takes time to process, preventing Discord timeout errors.

### Basic Usage
```python
await interaction.response.defer(ephemeral=True)
# ephemeral=True: only the user sees the response
# ephemeral=False: everyone sees the response
```

After deferring, use `followup` instead of `response`:
```python
await interaction.followup.send("Message here")
```

### Example
```python
@app_commands.command(name="blacklist-info", description="Look up a user")
async def blacklist_info(self, interaction: discord.Interaction, discord_id: str):
    await interaction.response.defer(ephemeral=True)
    
    # Perform time-consuming database queries
    history = await bl_history(discord_id)
    
    # Send the response after processing
    await interaction.followup.send("Results here")
```

---

## Discord Timestamps

Formats dates and times that automatically convert to each user's timezone.

### Format Syntax
```
<t:unix_timestamp:format_flag>
```

### Format Flags
| Flag | Example Output | Description |
|------|----------------|-------------|
| `d` | 20/05/2026 | Short date |
| `D` | May 20, 2026 | Long date |
| `t` | 14:30 | Short time |
| `T` | 14:30:45 | Long time |
| `f` | May 20, 2026 14:30 | Short date/time |
| `F` | Friday, May 20, 2026 14:30 | Long date/time |
| `R` | 2 hours ago | Relative time (updates automatically) |

### Usage Examples
```python
added_ts = timestamp_to_discord(record["added_at"])
# Convert datetime object to unix timestamp

embed.add_field(name="Added", value=f"<t:{added_ts}:d>", inline=False)
# Shows as "20/05/2026" to each user

embed.add_field(name="When", value=f"<t:{added_ts}:R>", inline=False)
# Shows as "2 hours ago" and updates automatically
```

---

## Permissions and Checks

Methods to verify user permissions before command execution.

### @app_commands.check()
A generic decorator for permission verification. Runs a function that returns `True` (allowed) or `False` (denied).

**Example:**
```python
def is_manager():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.ban_members
    return app_commands.check(predicate)

@app_commands.command(name="ban")
@is_manager()
async def ban_user(interaction: discord.Interaction):
    # Only users with ban_members permission can use this
    pass
```

### Common Permission Checks
```python
interaction.permissions.administrator        # Is admin
interaction.permissions.ban_members          # Can ban members
interaction.permissions.manage_messages      # Can manage messages
interaction.permissions.manage_roles         # Can manage roles
```

### Checking User Roles
```python
user_roles = interaction.user.roles
has_role = discord.utils.get(user_roles, name="Moderator")

if has_role:
    # User has the Moderator role
    pass
```

### Custom Implementation in This Bot
```python
@is_manager()
# Checks if user has "Ban Members" permission OR a custom BLACKLIST_ROLE_NAME
# If neither condition is met, the command won't execute and shows an error
```
