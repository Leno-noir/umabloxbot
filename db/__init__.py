# Re-exports database functions for simple imports
# Usage: from db import bl_add, connect, guild_get_settings, etc.
from .connection import connect, disconnect, get_application_db, get_db
from .blacklist import (
    bl_add, bl_remove, bl_get, bl_is_banned,
    bl_history, bl_list_active, bl_global_log,
)
from .guild_configs import (
    guild_set_blacklist_logs_channel, guild_get_blacklist_logs_channel,
    guild_get_blacklisted_users_join_alert_channel,
    guild_get_settings, guild_save_settings, guild_get_manager_role_id,
    guild_get_rotector_alert_channel, guild_get_rotector_enabled,
    guild_toggle_rotector_enabled,
)
from .allowed_guilds import (
    allowed_guild_add, allowed_guild_remove, allowed_guild_get,
    allowed_guild_exists, allowed_guild_is_enabled,
    allowed_guild_set_enabled, allowed_guild_list, allowed_guild_list_enabled,
)
from .funsies import (
    DEFAULT_FUNSIES_SETTINGS,
    application_gacha_get_usage, application_gacha_increment_usage,
    application_inventory_add_copy, application_inventory_has_copy,
    ensure_application_gacha_indexes,
    ensure_funsies_indexes,
    run_funsies_migrations,
    fact_add, fact_delete, fact_get_random_active, fact_list, fact_toggle_active,
    funsies_get_gacha_rarity_chances, funsies_get_settings, funsies_save_settings,
    funsies_get_gacha_rarity_names, funsies_set_gacha_rarity_chances,
    funsies_set_gacha_rarity_names, funsies_toggle_setting,
    gacha_get_usage, gacha_increment_usage,
    inventory_add_copy, inventory_count, inventory_get_by_id,
    inventory_has_copy,
    inventory_get_selected, inventory_get_selected_or_best,
    inventory_increment_win, inventory_list, inventory_set_selected,
    quote_add, quote_delete, quote_get_random_active, quote_list, quote_toggle_active,
    race_get_leaderboard, race_save_result,
    rarity_id_from_value, rarity_name_from_id, uma_add_character, uma_character_exists_name_overall,
    uma_delete_character, uma_get_character,
    uma_get_random_active, uma_get_random_by_rarity, uma_list_characters, uma_list_rarities,
    uma_search_by_name, uma_toggle_active, uma_update_character,
)
from .indexes import ensure_core_indexes
