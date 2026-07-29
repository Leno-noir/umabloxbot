from bson import ObjectId
from discord.utils import utcnow
from pymongo import ReturnDocument

from .connection import get_db


def object_id_from_post_id(post_id: str) -> ObjectId | None:
    try:
        return ObjectId(post_id)
    except Exception:
        return None


def active_post_query() -> dict:
    return {"$or": [{"status": "open"}, {"active": True}]}


def project_post_type_query() -> dict:
    return {"$in": ["project", "looking_for"]}


def dev_post_type_query() -> dict:
    return {"$in": ["dev", "available"]}


async def create_project_post(
    guild_id: int,
    author_id: int,
    author_name: str,
    message_id: int,
    channel_id: int,
    dev_role: str,
    project_name: str,
    description: str,
    contact: str | None,
    discord_invite: str | None,
    game_link: str | None,
) -> dict:
    now = utcnow()
    post = {
        "guild_id": guild_id,
        "author_id": author_id,
        "author_name": author_name,
        "message_id": message_id,
        "channel_id": channel_id,
        "post_type": "project",
        "dev_role": dev_role,
        "project_name": project_name,
        "description": description,
        "contact": contact,
        "portfolio_url": None,
        "discord_invite": discord_invite,
        "game_link": game_link,
        "status": "open",
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    await get_db().networking_posts.insert_one(post)
    return post


async def create_dev_post(
    guild_id: int,
    author_id: int,
    author_name: str,
    message_id: int,
    channel_id: int,
    dev_role: str,
    description: str,
    contact: str | None,
    portfolio_url: str | None,
) -> dict:
    now = utcnow()
    post = {
        "guild_id": guild_id,
        "author_id": author_id,
        "author_name": author_name,
        "message_id": message_id,
        "channel_id": channel_id,
        "post_type": "dev",
        "dev_role": dev_role,
        "project_name": None,
        "description": description,
        "contact": contact,
        "portfolio_url": portfolio_url,
        "discord_invite": None,
        "game_link": None,
        "status": "open",
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    await get_db().networking_posts.insert_one(post)
    return post


async def get_user_active_dev_post(guild_id: int, author_id: int) -> dict | None:
    return await get_db().networking_posts.find_one(
        {
            "guild_id": guild_id,
            "author_id": author_id,
            "post_type": dev_post_type_query(),
            **active_post_query(),
        }
    )


async def get_user_project_posts(guild_id: int, author_id: int) -> list[dict]:
    cursor = get_db().networking_posts.find(
        {
            "guild_id": guild_id,
            "author_id": author_id,
            "post_type": project_post_type_query(),
        }
    ).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def get_user_networking_post(
    post_id: str,
    guild_id: int,
    author_id: int,
) -> dict | None:
    object_id = object_id_from_post_id(post_id)
    if not object_id:
        return None

    return await get_db().networking_posts.find_one(
        {
            "_id": object_id,
            "guild_id": guild_id,
            "author_id": author_id,
        }
    )


async def get_networking_posts(
    guild_id: int,
    post_type: str,
    dev_role: str | None = None,
) -> list[dict]:
    query = {"guild_id": guild_id, **active_post_query()}

    if post_type == "project":
        query["post_type"] = project_post_type_query()
    else:
        query["post_type"] = dev_post_type_query()

    if dev_role:
        query["dev_role"] = dev_role

    cursor = get_db().networking_posts.find(query).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def update_networking_post(
    post_id: str,
    guild_id: int,
    author_id: int,
    updates: dict,
) -> dict | None:
    object_id = object_id_from_post_id(post_id)
    if not object_id:
        return None

    clean_updates = {}
    blocked_fields = {
        "_id",
        "guild_id",
        "author_id",
        "message_id",
        "channel_id",
        "created_at",
    }

    for field_name, field_value in updates.items():
        if field_name in blocked_fields:
            continue
        clean_updates[field_name] = field_value

    clean_updates["updated_at"] = utcnow()

    return await get_db().networking_posts.find_one_and_update(
        {
            "_id": object_id,
            "guild_id": guild_id,
            "author_id": author_id,
        },
        {"$set": clean_updates},
        return_document=ReturnDocument.AFTER,
    )


async def set_post_status(
    post_id: str,
    guild_id: int,
    author_id: int,
    status: str,
) -> dict | None:
    object_id = object_id_from_post_id(post_id)
    if not object_id or status not in {"open", "closed"}:
        return None

    return await get_db().networking_posts.find_one_and_update(
        {
            "_id": object_id,
            "guild_id": guild_id,
            "author_id": author_id,
        },
        {
            "$set": {
                "status": status,
                "active": status == "open",
                "updated_at": utcnow(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )


async def delete_networking_post(
    post_id: str,
    guild_id: int,
    author_id: int,
) -> dict | None:
    object_id = object_id_from_post_id(post_id)
    if not object_id:
        return None

    return await get_db().networking_posts.find_one_and_delete(
        {
            "_id": object_id,
            "guild_id": guild_id,
            "author_id": author_id,
        }
    )
