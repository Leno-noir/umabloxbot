from datetime import timezone

import discord
from discord.ext import commands

#Gets a string from the discord ID () and validates it (removes text, keeps numbers)
#If someone sends <@123456789> or smth it will extract only the numbers and return 123456789
def format_discord_id(raw_value: str) -> str | None:
    """Extract and validate a Discord ID from a raw input string."""
    digits_only = "".join(ch for ch in raw_value if ch.isdigit())
    return digits_only or None

#Gets a date from timezone (2026-05-20 15:30:00) and puts in discord format for date (1747850400)
#Discord uses like this <t:1747850400> to display the date in the user's local timezone
def timestamp_to_discord(dt) -> int:
    """Convert datetime to Discord timestamp."""
    return int(dt.replace(tzinfo=timezone.utc).timestamp())

#Calculate how many pages there will be on panel (10 items per page)
#Example: 25 items -> (25 + 9) // 10 = 34 
# 34 // 10 = 3 pages
def pagination_text(page: int, total: int) -> str:
    """Generate pagination footer text."""
    total_pages = (total + 9) // 10
    return f"Page {page}/{total_pages}"


#Gets a user display name by their discord ID (id 123456789 -> Leno#1234 (123456789))
#If the user is not found, it returns "Unknown user (123456789)"
async def get_user_by_discord_id(bot: commands.Bot, discord_id: str) -> str:
    """Fetch user by Discord ID and return formatted string with name and ID."""
    try:
        user = await bot.fetch_user(int(discord_id))
        return f"{user} (`{discord_id}`)"
    except (discord.NotFound, discord.HTTPException, ValueError):
        return f"Unknown user (`{discord_id}`)"