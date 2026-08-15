from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from bson import ObjectId

from .connection import get_application_db, get_db


logger = logging.getLogger(__name__)

GLOBAL_FUNSIES_GUILD_ID = 0
FUNSIES_SETTINGS_CACHE_TTL_SECONDS = 10.0
ACTIVE_UMAS_CACHE_TTL_SECONDS = 10.0

_FUNSIES_SETTINGS_CACHE: dict[int, tuple[float, dict]] = {}
_ACTIVE_UMAS_CACHE: dict[tuple[int, bool | None], tuple[float, list[dict]]] = {}


DEFAULT_FUNSIES_SETTINGS = {
    "quote_enabled": True,
    "fact_enabled": True,
    "uma_collection_enabled": True,
    "daily_gacha_limit": 50,
    "gacha_rarity_chances": {
        "1": 60,
        "2": 25,
        "3": 14,
        "4": 1,
    },
    "gacha_rarity_names": {
        "1": "R",
        "2": "SR",
        "3": "SSR",
        "4": "UR",
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today_key() -> str:
    return _now().date().isoformat()


def _global_scope() -> dict:
    return {"guild_id": GLOBAL_FUNSIES_GUILD_ID}


def _cache_get(guild_id: int) -> dict | None:
    cached = _FUNSIES_SETTINGS_CACHE.get(guild_id)
    if not cached:
        return None

    cached_at, settings = cached
    if time.monotonic() - cached_at > FUNSIES_SETTINGS_CACHE_TTL_SECONDS:
        _FUNSIES_SETTINGS_CACHE.pop(guild_id, None)
        return None

    return dict(settings)


def _cache_set(guild_id: int, settings: dict) -> None:
    _FUNSIES_SETTINGS_CACHE[guild_id] = (time.monotonic(), dict(settings))


def _cache_clear() -> None:
    _FUNSIES_SETTINGS_CACHE.clear()


def _active_umas_cache_get(guild_id: int, active: bool | None) -> list[dict] | None:
    if active is not True:
        return None

    cached = _ACTIVE_UMAS_CACHE.get((guild_id, active))
    if not cached:
        return None

    cached_at, items = cached
    if time.monotonic() - cached_at > ACTIVE_UMAS_CACHE_TTL_SECONDS:
        _ACTIVE_UMAS_CACHE.pop((guild_id, active), None)
        return None

    return [dict(item) for item in items]


def _active_umas_cache_set(guild_id: int, active: bool | None, items: list[dict]) -> None:
    if active is not True:
        return

    _ACTIVE_UMAS_CACHE[(guild_id, active)] = (time.monotonic(), [dict(item) for item in items])


def _active_umas_cache_clear() -> None:
    _ACTIVE_UMAS_CACHE.clear()


def _doc_timestamp(doc: dict | None) -> datetime:
    if not doc:
        return datetime.min.replace(tzinfo=timezone.utc)

    updated_at = doc.get("updated_at")
    if isinstance(updated_at, datetime):
        if updated_at.tzinfo is None:
            return updated_at.replace(tzinfo=timezone.utc)
        return updated_at

    doc_id = doc.get("_id")
    if isinstance(doc_id, ObjectId):
        return doc_id.generation_time

    return datetime.min.replace(tzinfo=timezone.utc)


async def funsies_get_settings(guild_id: int) -> dict:
    cached_settings = _cache_get(guild_id)
    if cached_settings is not None:
        return cached_settings

    db = get_db()
    global_doc = await db.funsies_settings.find_one(_global_scope())
    legacy_doc = None
    if guild_id != GLOBAL_FUNSIES_GUILD_ID:
        legacy_doc = await db.funsies_settings.find_one({"guild_id": guild_id})
    settings = dict(DEFAULT_FUNSIES_SETTINGS)
    docs = [doc for doc in (legacy_doc, global_doc) if doc]
    docs.sort(key=_doc_timestamp)
    for doc in docs:
        settings.update({k: v for k, v in doc.items() if k not in {"_id", "guild_id"}})

    for key in ("gacha_rarity_chances", "gacha_rarity_names"):
        default_value = DEFAULT_FUNSIES_SETTINGS.get(key)
        current_value = settings.get(key)
        if isinstance(default_value, dict):
            merged = dict(default_value)
            if isinstance(current_value, dict):
                for nested_key, nested_value in current_value.items():
                    if nested_value is not None and str(nested_value).strip():
                        merged[str(nested_key)] = nested_value
            settings[key] = merged
    _cache_set(guild_id, settings)
    return settings


async def funsies_save_settings(guild_id: int, updates: dict) -> None:
    db = get_db()
    await db.funsies_settings.update_one(
        _global_scope(),
        {"$set": {**updates, "guild_id": GLOBAL_FUNSIES_GUILD_ID, "updated_at": _now()}},
        upsert=True,
    )
    _cache_clear()


async def funsies_toggle_setting(guild_id: int, key: str) -> bool:
    settings = await funsies_get_settings(guild_id)
    new_value = not bool(settings.get(key, DEFAULT_FUNSIES_SETTINGS.get(key, False)))
    await funsies_save_settings(guild_id, {key: new_value})
    return new_value


async def funsies_set_gacha_rarity_chances(guild_id: int, chances: dict[str, int]) -> None:
    await funsies_save_settings(guild_id, {"gacha_rarity_chances": chances})


async def funsies_set_gacha_rarity_names(guild_id: int, names: dict[str, str]) -> None:
    await funsies_save_settings(guild_id, {"gacha_rarity_names": names})


async def funsies_get_gacha_rarity_chances(guild_id: int) -> dict[str, int]:
    settings = await funsies_get_settings(guild_id)
    chances = settings.get("gacha_rarity_chances") or {}
    merged = dict(DEFAULT_FUNSIES_SETTINGS["gacha_rarity_chances"])
    for rarity, value in chances.items():
        try:
            merged[str(rarity)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return merged


async def funsies_get_gacha_rarity_names(guild_id: int) -> dict[str, str]:
    settings = await funsies_get_settings(guild_id)
    names = settings.get("gacha_rarity_names") or {}
    stored_names: dict[str, str] = dict(DEFAULT_FUNSIES_SETTINGS["gacha_rarity_names"])
    for rarity, value in names.items():
        if value:
            stored_names[str(rarity)] = str(value)
    return stored_names


def rarity_id_from_value(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None

    text = str(value).strip()
    if not text:
        return None

    if text.isdigit():
        rarity_id = int(text)
        return rarity_id if rarity_id > 0 else None
    return None


RARITY_NAME_FIELDS = (
    "rarity_label",
    "rarity_name",
    "rarity_display",
    "rarity_title",
    "rarityLabel",
    "rarityName",
)


def rarity_name_from_id(rarity_id: str | int | None, names: dict[str, str] | None = None) -> str:
    if rarity_id is None:
        return "Unknown"
    rarity_key = str(rarity_id)
    label_map = names or {}
    return label_map.get(rarity_key, DEFAULT_FUNSIES_SETTINGS["gacha_rarity_names"].get(rarity_key, rarity_key))


def _valid_rarity_label(value: object, rarity_id: object = None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if rarity_id is not None and text == str(rarity_id).strip():
        return None
    return text


def _rarity_name_from_item(item: dict) -> str | None:
    rarity_id = item.get("rarity")
    for field in RARITY_NAME_FIELDS:
        value = _valid_rarity_label(item.get(field), rarity_id)
        if value:
            return value

    rarity = item.get("rarity")
    if isinstance(rarity, dict):
        for field in ("name", "label", "display", "title"):
            value = _valid_rarity_label(rarity.get(field), rarity.get("id"))
            if value:
                return value
    return None


async def _attach_rarity_names(guild_id: int, items: list[dict]) -> list[dict]:
    names = await funsies_get_gacha_rarity_names(guild_id)
    for item in items:
        rarity_key = str(item.get("rarity")) if item.get("rarity") is not None else None
        configured_name = _valid_rarity_label(names.get(rarity_key), rarity_key) if rarity_key else None
        resolved_name = configured_name or _rarity_name_from_item(item) or rarity_name_from_id(item.get("rarity"), names)
        item["rarity_name"] = resolved_name
        item["rarity_label"] = resolved_name
    return items


async def uma_list_rarities(guild_id: int, active: bool | None = True) -> list[int]:
    db = get_db()
    query = {}
    if active is not None:
        query["active"] = active
    rarities = await db.uma_characters.distinct("rarity", query)
    normalized = sorted({rarity_id_from_value(rarity) for rarity in rarities if rarity_id_from_value(rarity) is not None})
    return normalized


async def uma_get_random_by_rarity(guild_id: int, rarity: str | int) -> dict | None:
    db = get_db()
    rarity_id = rarity_id_from_value(rarity)
    cursor = db.uma_characters.aggregate(
        [
            {"$match": {"active": True, "rarity": rarity_id}},
            {"$sample": {"size": 1}},
        ]
    )
    items = await cursor.to_list(length=1)
    await _attach_rarity_names(guild_id, items)
    return items[0] if items else None


async def quote_add(
    guild_id: int,
    character: str,
    text: str,
    active: bool = True,
) -> dict:
    db = get_db()
    document = {
        "guild_id": GLOBAL_FUNSIES_GUILD_ID,
        "character": character,
        "text": text,
        "active": active,
        "created_at": _now(),
    }
    result = await db.uma_quotes.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def quote_get_random_active(guild_id: int) -> dict | None:
    db = get_db()
    cursor = db.uma_quotes.aggregate(
        [
            {"$match": {"active": True}},
            {"$sample": {"size": 1}},
        ]
    )
    items = await cursor.to_list(length=1)
    return items[0] if items else None


async def quote_list(guild_id: int, active: bool | None = None) -> list[dict]:
    db = get_db()
    query = {}
    if active is not None:
        query["active"] = active
    cursor = db.uma_quotes.find(query).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def quote_toggle_active(guild_id: int, quote_id: ObjectId) -> bool:
    db = get_db()
    quote = await db.uma_quotes.find_one({"_id": quote_id})
    if not quote:
        return False
    result = await db.uma_quotes.update_one(
        {"_id": quote_id},
        {"$set": {"active": not quote.get("active", True)}},
    )
    return result.modified_count > 0


async def quote_delete(guild_id: int, quote_id: ObjectId) -> bool:
    db = get_db()
    result = await db.uma_quotes.delete_one({"_id": quote_id})
    return result.deleted_count > 0


async def fact_add(
    guild_id: int,
    text: str,
    active: bool = True,
) -> dict:
    db = get_db()
    document = {
        "guild_id": GLOBAL_FUNSIES_GUILD_ID,
        "text": text,
        "active": active,
        "created_at": _now(),
    }
    result = await db.uma_facts.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def fact_get_random_active(guild_id: int) -> dict | None:
    db = get_db()
    cursor = db.uma_facts.aggregate(
        [
            {"$match": {"active": True}},
            {"$sample": {"size": 1}},
        ]
    )
    items = await cursor.to_list(length=1)
    return items[0] if items else None


async def fact_list(guild_id: int, active: bool | None = None) -> list[dict]:
    db = get_db()
    query = {}
    if active is not None:
        query["active"] = active
    cursor = db.uma_facts.find(query).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def fact_toggle_active(guild_id: int, fact_id: ObjectId) -> bool:
    db = get_db()
    fact = await db.uma_facts.find_one({"_id": fact_id})
    if not fact:
        return False
    result = await db.uma_facts.update_one(
        {"_id": fact_id},
        {"$set": {"active": not fact.get("active", True)}},
    )
    return result.modified_count > 0


async def fact_delete(guild_id: int, fact_id: ObjectId) -> bool:
    db = get_db()
    result = await db.uma_facts.delete_one({"_id": fact_id})
    return result.deleted_count > 0


async def uma_add_character(
    guild_id: int,
    name: str,
    rarity: str,
    image_url: str | None,
    overall: int,
    active: bool = True,
) -> dict:
    db = get_db()
    rarity_id = rarity_id_from_value(rarity)
    if rarity_id is None:
        rarity_id = 1
    document = {
        "guild_id": guild_id,
        "name": name,
        "rarity": rarity_id,
        "image_url": image_url or None,
        "overall": int(overall),
        "active": active,
        "created_at": _now(),
    }
    result = await db.uma_characters.insert_one(document)
    document["_id"] = result.inserted_id
    _active_umas_cache_clear()
    return document


async def uma_character_exists_name_overall(
    name: str,
    overall: int,
    exclude_id: ObjectId | None = None,
) -> bool:
    db = get_db()
    query = {
        "name": {"$regex": f"^{name}$", "$options": "i"},
        "overall": int(overall),
    }
    if exclude_id is not None:
        query["_id"] = {"$ne": exclude_id}
    existing = await db.uma_characters.find_one(query)
    return existing is not None


async def uma_get_character(guild_id: int, uma_id: ObjectId) -> dict | None:
    db = get_db()
    item = await db.uma_characters.find_one({"_id": uma_id})
    if item:
        await _attach_rarity_names(guild_id, [item])
    return item


async def uma_list_characters(guild_id: int, active: bool | None = None) -> list[dict]:
    cached_items = _active_umas_cache_get(guild_id, active)
    if cached_items is not None:
        return await _attach_rarity_names(guild_id, cached_items)

    db = get_db()
    query = {}
    if active is not None:
        query["active"] = active
    cursor = db.uma_characters.find(query).sort([("overall", -1), ("created_at", 1)])
    items = await cursor.to_list(length=None)
    _active_umas_cache_set(guild_id, active, items)
    return await _attach_rarity_names(guild_id, items)


async def uma_search_by_name(guild_id: int, name: str, active: bool | None = None) -> list[dict]:
    db = get_db()
    query = {
        "name": {"$regex": name, "$options": "i"},
    }
    if active is not None:
        query["active"] = active
    cursor = db.uma_characters.find(query).sort([("overall", -1), ("created_at", 1)])
    items = await cursor.to_list(length=None)
    return await _attach_rarity_names(guild_id, items)


async def uma_migrate_rarity_values() -> int:
    db = get_db()
    updated = 0
    async for doc in db.uma_characters.find({}):
        rarity_id = rarity_id_from_value(doc.get("rarity"))
        if rarity_id is None:
            continue
        if doc.get("rarity") == rarity_id:
            continue
        result = await db.uma_characters.update_one({"_id": doc["_id"]}, {"$set": {"rarity": rarity_id}})
        updated += result.modified_count
    if updated:
        _active_umas_cache_clear()
    return updated


async def uma_get_random_active(guild_id: int) -> dict | None:
    db = get_db()
    cursor = db.uma_characters.aggregate(
        [
            {"$match": {"active": True}},
            {"$sample": {"size": 1}},
        ]
    )
    items = await cursor.to_list(length=1)
    await _attach_rarity_names(guild_id, items)
    return items[0] if items else None


async def uma_toggle_active(guild_id: int, uma_id: ObjectId) -> bool:
    db = get_db()
    uma = await db.uma_characters.find_one({"_id": uma_id})
    if not uma:
        return False
    result = await db.uma_characters.update_one(
        {"_id": uma_id},
        {"$set": {"active": not uma.get("active", True)}},
    )
    if result.modified_count > 0:
        _active_umas_cache_clear()
    return result.modified_count > 0


async def uma_update_character(
    guild_id: int,
    uma_id: ObjectId,
    *,
    name: str,
    rarity: str | int,
    image_url: str | None,
    overall: int,
) -> bool:
    db = get_db()
    rarity_id = rarity_id_from_value(rarity)
    if rarity_id is None:
        return False
    result = await db.uma_characters.update_one(
        {"_id": uma_id, "guild_id": guild_id},
        {
            "$set": {
                "name": name,
                "rarity": rarity_id,
                "image_url": image_url or None,
                "overall": int(overall),
                "updated_at": _now(),
            }
        },
    )
    if result.matched_count > 0:
        _active_umas_cache_clear()
    return result.matched_count > 0


async def uma_delete_character(guild_id: int, uma_id: ObjectId) -> bool:
    db = get_db()
    if await db.user_uma_inventory.find_one({"uma_id": uma_id}, {"_id": 1}):
        logger.warning("Refusing to delete owned Uma %s; deactivate it instead", uma_id)
        return False
    result = await db.uma_characters.delete_one({"_id": uma_id, "guild_id": guild_id})
    if result.deleted_count > 0:
        _active_umas_cache_clear()
    return result.deleted_count > 0


async def inventory_add_copy(
    guild_id: int,
    user_id: int,
    uma_document: dict,
) -> dict:
    db = get_db()
    existing = await db.user_uma_inventory.find_one(
        {
            "guild_id": guild_id,
            "user_id": user_id,
            "uma_id": uma_document["_id"],
        }
    )
    if existing:
        return existing

    document = {
        "guild_id": guild_id,
        "user_id": user_id,
        "uma_id": uma_document["_id"],
        "wins": 0,
        "obtained_at": _now(),
    }
    result = await db.user_uma_inventory.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def inventory_has_copy(
    guild_id: int,
    user_id: int,
    uma_id: ObjectId,
) -> bool:
    db = get_db()
    existing = await db.user_uma_inventory.find_one(
        {
            "guild_id": guild_id,
            "user_id": user_id,
            "uma_id": uma_id,
        }
    )
    return existing is not None


def _inventory_catalog_pipeline(match: dict) -> list[dict]:
    return [
        {"$match": match},
        {
            "$lookup": {
                "from": "uma_characters",
                "localField": "uma_id",
                "foreignField": "_id",
                "as": "uma",
            }
        },
        {"$unwind": "$uma"},
        {
            "$set": {
                "uma_name": "$uma.name",
                "rarity": "$uma.rarity",
                "rarity_name": "$uma.rarity_name",
                "rarity_label": "$uma.rarity_label",
                "rarity_display": "$uma.rarity_display",
                "rarity_title": "$uma.rarity_title",
                "overall": "$uma.overall",
                "image_url": "$uma.image_url",
                "uma_active": "$uma.active",
            }
        },
        {"$unset": "uma"},
    ]


async def inventory_list(guild_id: int, user_id: int) -> list[dict]:
    db = get_db()
    pipeline = _inventory_catalog_pipeline({"guild_id": guild_id, "user_id": user_id})
    pipeline.append({"$sort": {"overall": -1, "obtained_at": 1}})
    items = await db.user_uma_inventory.aggregate(pipeline).to_list(length=None)
    return await _attach_rarity_names(guild_id, items)


async def inventory_count(guild_id: int, user_id: int) -> int:
    db = get_db()
    return await db.user_uma_inventory.count_documents(
        {"guild_id": guild_id, "user_id": user_id}
    )


async def inventory_get_by_id(
    guild_id: int,
    user_id: int,
    inventory_id: ObjectId,
) -> dict | None:
    db = get_db()
    pipeline = _inventory_catalog_pipeline(
        {"_id": inventory_id, "guild_id": guild_id, "user_id": user_id}
    )
    items = await db.user_uma_inventory.aggregate(pipeline).to_list(length=1)
    await _attach_rarity_names(guild_id, items)
    return items[0] if items else None


async def inventory_increment_win(
    guild_id: int,
    user_id: int,
    inventory_id: ObjectId,
    amount: int = 1,
) -> bool:
    db = get_db()
    result = await db.user_uma_inventory.update_one(
        {"_id": inventory_id, "guild_id": guild_id, "user_id": user_id},
        {"$inc": {"wins": amount}},
    )
    return result.modified_count > 0


async def inventory_get_selected(guild_id: int, user_id: int) -> dict | None:
    db = get_db()
    return await db.user_race_settings.find_one(
        {"guild_id": guild_id, "user_id": user_id}
    )


async def inventory_set_selected(
    guild_id: int,
    user_id: int,
    inventory_id: ObjectId | None,
) -> None:
    db = get_db()
    await db.user_race_settings.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {
            "$set": {
                "selected_inventory_uma_id": inventory_id,
                "updated_at": _now(),
            }
        },
        upsert=True,
    )


async def inventory_get_selected_or_best(
    guild_id: int,
    user_id: int,
) -> dict | None:
    inventory = await inventory_list(guild_id, user_id)
    if not inventory:
        return None

    selected = await inventory_get_selected(guild_id, user_id)
    selected_id = selected.get("selected_inventory_uma_id") if selected else None
    if selected_id:
        for item in inventory:
            if item["_id"] == selected_id:
                return item

    return inventory[0]


async def gacha_get_usage(guild_id: int, user_id: int, date_key: str | None = None) -> dict | None:
    db = get_db()
    date = date_key or _today_key()
    item = await db.gacha_daily_usage.find_one({"guild_id": guild_id, "user_id": user_id, "date": date})
    if not item:
        return None
    return {
        "guild_id": guild_id,
        "user_id": user_id,
        "date": date,
        "used": int(item.get("used", 0) or 0),
    }


async def gacha_increment_usage(
    guild_id: int,
    user_id: int,
    amount: int,
    date_key: str | None = None,
) -> int:
    db = get_db()
    today = date_key or _today_key()
    await db.gacha_daily_usage.update_one(
        {"guild_id": guild_id, "user_id": user_id, "date": today},
        {
            "$setOnInsert": {"guild_id": guild_id, "user_id": user_id, "date": today},
            "$inc": {"used": amount},
        },
        upsert=True,
    )
    doc = await gacha_get_usage(guild_id, user_id, today)
    return int(doc.get("used", 0)) if doc else amount


async def application_gacha_get_usage(
    user_id: int,
    date_key: str | None = None,
) -> dict | None:
    """Get daily gacha usage from the user-installed app database."""
    db = get_application_db()
    date = date_key or _today_key()
    item = await db.gacha_daily_usage.find_one({"user_id": user_id, "date": date})
    if not item:
        return None
    return {"user_id": user_id, "date": date, "used": int(item.get("used", 0) or 0)}


async def application_gacha_increment_usage(
    user_id: int,
    amount: int,
    date_key: str | None = None,
) -> int:
    """Increment daily gacha usage in the user-installed app database."""
    db = get_application_db()
    today = date_key or _today_key()
    await db.gacha_daily_usage.update_one(
        {"user_id": user_id, "date": today},
        {
            "$setOnInsert": {"user_id": user_id, "date": today},
            "$inc": {"used": amount},
        },
        upsert=True,
    )
    doc = await application_gacha_get_usage(user_id, today)
    return int(doc.get("used", 0)) if doc else amount


async def application_inventory_has_copy(user_id: int, uma_id: ObjectId) -> bool:
    """Check application-gacha ownership without reading guild inventories."""
    db = get_application_db()
    return await db.user_uma_inventory.find_one({"user_id": user_id, "uma_id": uma_id}) is not None


async def application_inventory_add_copy(user_id: int, uma_document: dict) -> dict:
    """Store ownership for a user-installed app gacha pull.

    The Uma catalogue remains shared, but ownership is intentionally written to
    the separate application database so it can never mix with a guild team.
    """
    db = get_application_db()
    existing = await db.user_uma_inventory.find_one(
        {"user_id": user_id, "uma_id": uma_document["_id"]}
    )
    if existing:
        return existing

    document = {
        "user_id": user_id,
        "uma_id": uma_document["_id"],
        "wins": 0,
        "obtained_at": _now(),
    }
    result = await db.user_uma_inventory.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def race_save_result(result: dict) -> dict:
    db = get_db()
    document = dict(result)
    document.setdefault("created_at", _now())
    insert_result = await db.uma_race_results.insert_one(document)
    document["_id"] = insert_result.inserted_id
    return document


async def race_get_leaderboard(guild_id: int, limit: int = 50) -> list[dict]:
    db = get_db()
    cursor = (
        db.uma_race_results.find({"guild_id": guild_id})
        .sort("winner_time_ms", 1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def inventory_migrate_to_catalog_references() -> dict[str, int]:
    db = get_db()
    groups: dict[tuple[int, int, ObjectId], list[dict]] = {}
    orphaned = 0

    async for item in db.user_uma_inventory.find({}):
        uma_id = item.get("uma_id")
        if not isinstance(uma_id, ObjectId):
            orphaned += 1
            logger.warning("Inventory item %s has no valid uma_id; leaving it unchanged", item.get("_id"))
            continue
        uma_exists = await db.uma_characters.find_one({"_id": uma_id}, {"_id": 1})
        if not uma_exists:
            orphaned += 1
            logger.warning(
                "Inventory item %s references missing Uma %s; leaving it unchanged",
                item.get("_id"),
                uma_id,
            )
            continue
        key = (item.get("guild_id"), item.get("user_id"), uma_id)
        groups.setdefault(key, []).append(item)

    merged = 0
    migrated = 0
    snapshot_fields = {"uma_name": "", "rarity": "", "overall": "", "image_url": ""}
    for (guild_id, user_id, _uma_id), items in groups.items():
        def obtained_sort_key(item: dict) -> tuple[float, str]:
            obtained_at = item.get("obtained_at")
            if isinstance(obtained_at, datetime):
                if obtained_at.tzinfo is None:
                    obtained_at = obtained_at.replace(tzinfo=timezone.utc)
                timestamp = obtained_at.timestamp()
            else:
                timestamp = item["_id"].generation_time.timestamp()
            return timestamp, str(item["_id"])

        items.sort(key=obtained_sort_key)
        primary = items[0]
        duplicate_ids = [item["_id"] for item in items[1:]]
        total_wins = sum(int(item.get("wins", 0) or 0) for item in items)

        if duplicate_ids or any(field in primary for field in snapshot_fields):
            await db.user_uma_inventory.update_one(
                {"_id": primary["_id"]},
                {"$set": {"wins": total_wins}, "$unset": snapshot_fields},
            )
            migrated += 1

        if duplicate_ids:
            await db.user_race_settings.update_one(
                {
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "selected_inventory_uma_id": {"$in": duplicate_ids},
                },
                {"$set": {"selected_inventory_uma_id": primary["_id"], "updated_at": _now()}},
            )
            result = await db.user_uma_inventory.delete_many({"_id": {"$in": duplicate_ids}})
            merged += result.deleted_count

    if orphaned:
        logger.warning("Found %s orphaned inventory item(s) that require manual correction", orphaned)
    if migrated or merged:
        logger.info("Inventory migration complete: %s migrated, %s duplicates merged", migrated, merged)
    return {"migrated": migrated, "merged": merged, "orphaned": orphaned}


async def funsies_migrate_global_settings() -> bool:
    db = get_db()
    global_doc = await db.funsies_settings.find_one(_global_scope())
    source = await db.funsies_settings.find_one(
        {"guild_id": {"$ne": GLOBAL_FUNSIES_GUILD_ID}},
        sort=[("updated_at", -1), ("_id", -1)],
    )
    if not source:
        return False
    if global_doc and _doc_timestamp(global_doc) >= _doc_timestamp(source):
        return False

    updates = {
        key: value
        for key, value in source.items()
        if key not in {"_id", "guild_id"}
    }
    updates["guild_id"] = GLOBAL_FUNSIES_GUILD_ID
    await db.funsies_settings.update_one(_global_scope(), {"$set": updates}, upsert=True)
    logger.info("Migrated funsies settings from guild %s to global scope", source.get("guild_id"))
    return True


async def ensure_funsies_indexes() -> None:
    """Create safe query indexes only; data migrations run out-of-band."""
    db = get_db()
    await db.uma_quotes.create_index([("active", 1), ("created_at", -1)])
    await db.uma_facts.create_index([("active", 1), ("created_at", -1)])
    await db.uma_characters.create_index([("active", 1), ("rarity", 1), ("overall", -1)])
    await db.uma_race_results.create_index(
        [("guild_id", 1), ("winner_time_ms", 1), ("created_at", -1)]
    )


async def ensure_application_gacha_indexes() -> None:
    """Create indexes in the database reserved for application gacha data."""
    db = get_application_db()
    await db.gacha_daily_usage.create_index(
        [("user_id", 1), ("date", 1)],
        unique=True,
        name="unique_application_gacha_usage",
    )
    await db.user_uma_inventory.create_index(
        [("user_id", 1), ("uma_id", 1)],
        unique=True,
        name="unique_application_owned_uma",
    )


async def run_funsies_migrations() -> dict[str, object]:
    """Run data-changing Funsies migrations during an explicit maintenance window."""
    db = get_db()
    # Import here to keep normal bot startup independent from maintenance tools.
    from scripts.preflight_database import (
        assert_all_unique_preconditions,
        assert_funsies_preflight_before_migration,
    )

    preflight_before = await assert_funsies_preflight_before_migration(db)
    settings_migrated = await funsies_migrate_global_settings()
    inventory_result = await inventory_migrate_to_catalog_references()
    rarity_migrated = await uma_migrate_rarity_values()

    preflight_after = await assert_all_unique_preconditions(db)

    await db.funsies_settings.create_index("guild_id", unique=True)
    await db.user_uma_inventory.create_index(
        [("guild_id", 1), ("user_id", 1), ("uma_id", 1)],
        name="unique_owned_uma",
        unique=True,
        partialFilterExpression={"uma_id": {"$type": "objectId"}},
    )
    await db.user_race_settings.create_index(
        [("guild_id", 1), ("user_id", 1)],
        unique=True,
    )
    await db.gacha_daily_usage.create_index(
        [("guild_id", 1), ("user_id", 1), ("date", 1)],
        unique=True,
    )
    return {
        "settings_migrated": settings_migrated,
        "inventory_migrated": inventory_result["migrated"],
        "inventory_merged": inventory_result["merged"],
        "inventory_orphaned": inventory_result["orphaned"],
        "rarity_migrated": rarity_migrated,
        "preflight_before": preflight_before,
        "preflight_after": preflight_after,
    }
