import discord

from db.guild_configs import guild_get_settings


DEFAULT_DEV_ROLE_OPTIONS = [
    ("Builder", "builder"),
    ("Scripter", "scripter"),
    ("Animator", "animator"),
    ("Artist", "artist"),
]

DEV_ROLE_LABELS = {value: label for label, value in DEFAULT_DEV_ROLE_OPTIONS}


def dev_role_value(label: str) -> str:
    clean_label = "".join(
        character.lower() if character.isalnum() else "_" for character in label.strip()
    )
   
    return "_".join(part for part in clean_label.split("_") if part)






def normalize_dev_role_option(configured_role) -> tuple[str, str]:
    if isinstance(configured_role, dict):
        label = str(configured_role.get("label") or "").strip()
        value = str(configured_role.get("value") or dev_role_value(label)).strip()
        return label, value

    if isinstance(configured_role, (list, tuple)) and configured_role:
        label = str(configured_role[0]).strip()
        value = dev_role_value(label)
        if len(configured_role) > 1:
            value = str(configured_role[1]).strip()
        return label, value

    label = str(configured_role).strip()
    return label, dev_role_value(label)






def normalize_dev_role_options(configured_roles) -> list[tuple[str, str]]:
    role_options: list[tuple[str, str]] = []
    seen_values: set[str] = set()

    for configured_role in configured_roles or []:
        label, value = normalize_dev_role_option(configured_role)
        if not label or not value or value in seen_values:
            continue

        role_options.append((label, value))
        seen_values.add(value)

    return role_options






async def get_networking_channel(
    interaction: discord.Interaction,
) -> discord.abc.GuildChannel | None:
    settings = await guild_get_settings(interaction.guild_id) or {}
    channel_id = settings.get("networking_channel")

    if not channel_id:
        return None

    return interaction.guild.get_channel(channel_id)






async def get_dev_role_options(guild_id: int) -> list[tuple[str, str]]:
    settings = await guild_get_settings(guild_id) or {}
    role_options = normalize_dev_role_options(settings.get("networking_dev_roles"))
    return role_options or DEFAULT_DEV_ROLE_OPTIONS





def serialize_dev_role_options(role_options: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in role_options]





def format_dev_role(
    role: str,
    role_options: list[tuple[str, str]] | None = None,
) -> str:
    labels = DEV_ROLE_LABELS.copy()

    for label, value in role_options or []:
        labels[value] = label

    return labels.get(role, role.replace("_", " ").title())





def format_post_status(status: str | None) -> str:
    if status == "closed":
        return "Closed"

    return "Open"





def is_project_post(post: dict | None) -> bool:
    return bool(post and post.get("post_type") in {"project", "looking_for"})






def next_post_status(post: dict) -> str:
    if post.get("status") == "closed":
        return "open"

    return "closed"





def project_display_name(post: dict) -> str:
    return post.get("project_name") or post.get("game_name") or post.get("title") or "Project"






def post_contact(post: dict) -> str:
    return post.get("contact") or f"<@{post['author_id']}>"






def post_created_timestamp(post: dict) -> str:
    created_at = post.get("created_at")
    if not created_at:
        return "Unknown"

    return f"<t:{int(created_at.timestamp())}:R>"






def short_post_id(post: dict) -> str:
    return str(post["_id"])[-6:]






def build_project_post_embed(
    post: dict,
    role_options: list[tuple[str, str]] | None = None,
) -> discord.Embed:
   
    role_label = format_dev_role(post["dev_role"], role_options)
   
    embed = discord.Embed(
        title=f"{project_display_name(post)} is looking for {role_label}",
        description=post["description"],
        colour=discord.Colour.orange(),
    )
    
    embed.add_field(name="Role", value=role_label, inline=True)
    embed.add_field(name="Status", value=format_post_status(post.get("status")), inline=True)
    embed.add_field(name="Contact", value=post_contact(post), inline=True)

    if post.get("game_link"):
        embed.add_field(name="Game link", value=post["game_link"], inline=False)

    if post.get("discord_invite"):
        embed.add_field(name="Discord invite", value=post["discord_invite"], inline=False)

    embed.set_footer(text=f"Posted by {post.get('author_name', 'Unknown')}")
    return embed






def build_dev_post_embed(
    post: dict,
    role_options: list[tuple[str, str]] | None = None,
) -> discord.Embed:
    
    role_label = format_dev_role(post["dev_role"], role_options)
   
    embed = discord.Embed(
        title=f"{post.get('author_name', 'Developer')} is available as {role_label}",
        description=post["description"],
        colour=discord.Colour.green(),
    )
    
    embed.add_field(name="Role", value=role_label, inline=True)
    embed.add_field(name="Status", value=format_post_status(post.get("status")), inline=True)
    embed.add_field(name="Contact", value=post_contact(post), inline=True)

    if post.get("portfolio_url"):
        embed.add_field(name="Portfolio", value=post["portfolio_url"], inline=False)

    embed.set_footer(text=f"Posted by {post.get('author_name', 'Unknown')}")
    return embed






def build_public_post_buttons(post: dict) -> discord.ui.View | None:
    buttons: list[discord.ui.Button] = []

    if post.get("portfolio_url"):
        buttons.append(
            discord.ui.Button(
                label="Portfolio",
                style=discord.ButtonStyle.link,
                url=post["portfolio_url"],
            )
        )

    if post.get("game_link"):
        buttons.append(
            discord.ui.Button(
                label="Game",
                style=discord.ButtonStyle.link,
                url=post["game_link"],
            )
        )

    if not buttons:
        return None

    view = discord.ui.View(timeout=None)
    for button in buttons:
        view.add_item(button)

    return view



async def networking_channel_is_configured(
    interaction: discord.Interaction,
) -> bool:
    networking_channel = await get_networking_channel(interaction)

    if networking_channel is None:
        await interaction.response.send_message(
            "Networking channel is not configured. Set it in /settings first.",
            ephemeral=True,
        )
        return False

    return True




async def send_project_post_message(
    channel,
    post: dict,
    role_options: list[tuple[str, str]],
) -> discord.Message:
    return await channel.send(
        embed=build_project_post_embed(post, role_options),
        view=build_public_post_buttons(post),
    )


async def send_dev_post_message(
    channel,
    post: dict,
    role_options: list[tuple[str, str]],
) -> discord.Message:
    return await channel.send(
        embed=build_dev_post_embed(post, role_options),
        view=build_public_post_buttons(post),
    )


async def update_public_post(bot, post: dict) -> None:
    channel_id = post.get("channel_id")
    message_id = post.get("message_id")
    guild_id = post.get("guild_id")
   
    if not channel_id or not message_id or not guild_id:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            return

    role_options = await get_dev_role_options(guild_id)
    embed = build_project_post_embed(post, role_options)
   
    if not is_project_post(post):
        embed = build_dev_post_embed(post, role_options)

    try:
        message = await channel.fetch_message(message_id)
        await message.edit(embed=embed, view=build_public_post_buttons(post))
    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
        return






async def delete_public_post(bot, post: dict) -> None:
    channel_id = post.get("channel_id")
    message_id = post.get("message_id")
  
    if not channel_id or not message_id:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            return

    try:
        message = await channel.fetch_message(message_id)
        await message.delete()
    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
        return
