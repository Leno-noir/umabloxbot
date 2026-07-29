import discord
from discord import app_commands

from db.feedback import feedback_get_games
from db.guild_configs import (
    guild_get_feedback_manager_role_id,
    guild_get_feedback_manager_role_name,
)


FEEDBACK_CATEGORY_LABELS = {
    "bug": "🐛 Bug",
    "balancing": "⚖️ Balancing",
    "ux": "✨ UX",
    "suggestion": "💡 Suggestion",
}

FEEDBACK_CATEGORY_OPTIONS = [
    discord.SelectOption(label=label, value=category)
    for category, label in FEEDBACK_CATEGORY_LABELS.items()
]


async def send_ephemeral_message(
    interaction: discord.Interaction,
    message: str,
):
    
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    
    else:
        await interaction.response.send_message(message, ephemeral=True)






def category_label(category: str) -> str:
    return FEEDBACK_CATEGORY_LABELS.get(category, category.capitalize())






def category_emoji(category: str) -> str:
    label = category_label(category)
    
    return label.split(" ", 1)[0]






def active_feedback_games(games: list[dict]) -> list[dict]:
    return [game for game in games if game.get("active")]






async def get_active_feedback_games(guild_id: int) -> list[dict]:
    games = await feedback_get_games(guild_id)
   
    return active_feedback_games(games)






def feedback_sender_label(
    interaction: discord.Interaction,
    send_anonymously: bool,
) -> str:
    
    if send_anonymously:
        return "Anonymous"

    return f"{interaction.user.name} ({interaction.user.id})"






def is_feedback_manager():
    """Allow feedback manager commands for moderators or the configured role."""

    async def authorize_feedback_commands(interaction: discord.Interaction) -> bool:
        if interaction.permissions and interaction.permissions.ban_members:
            return True

        member = (
            interaction.user
            if isinstance(interaction.user, discord.Member)
            else None
        )
       
        if member is None and interaction.guild is not None:
            member = interaction.guild.get_member(interaction.user.id)

       
        manager_role_name = await get_feedback_manager_role_name(interaction.guild_id)
        if manager_role_name and member is not None:
            if any(role.name == manager_role_name for role in member.roles):
                return True

       
        await send_ephemeral_message(
            interaction,
            "You do not have permission to use this command.",
        )
       
        return False

    return app_commands.check(authorize_feedback_commands)






async def get_feedback_manager_role_name(guild_id: int) -> str | None:
    return await guild_get_feedback_manager_role_name(guild_id)


async def get_feedback_manager_role_id(guild_id: int) -> int | None:
    return await guild_get_feedback_manager_role_id(guild_id)
