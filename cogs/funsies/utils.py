from __future__ import annotations

import random

RACE_MARGIN_BANDS = [
    (50, "Photo Finish"),
    (80, "Nose"),
    (150, "Head"),
    (250, "Neck"),
    (400, "1/2 Length"),
    (650, "1 Length"),
    (900, "1½ Lengths"),
    (1200, "2 Lengths"),
    (1600, "3 Lengths"),
    (2200, "4 Lengths"),
    (3000, "5 Lengths"),
]


def format_time_ms(total_ms: int) -> str:
    minutes, remainder_ms = divmod(max(0, total_ms), 60_000)
    seconds, centiseconds = divmod(remainder_ms, 1000)
    return f"{minutes}:{seconds:02d}.{centiseconds // 10:02d}"


def build_race_score(overall: int) -> float:
    return random.randint(1, 100) + (overall * 0.35)


def build_race_time_ms(score: float) -> int:
    base_time_ms = 95_000
    return max(50_000, base_time_ms - int(score * 120) + random.randint(-300, 300))


def race_margin_from_diff(diff_ms: int) -> str:
    for limit, label in RACE_MARGIN_BANDS:
        if diff_ms <= limit:
            return label
    return "Distance"


def build_uma_summary_label(uma: dict) -> str:
    rarity_name = uma.get("rarity_label") or uma.get("rarity_name") or str(uma.get("rarity", ""))
    return f"{uma['name']} | {rarity_name} | Overall {uma['overall']}"


def build_inventory_line(item: dict, position: int | None = None, selected: bool = False) -> str:
    prefix = "-> " if selected else ""
    index = f"{position}. " if position is not None else ""
    rarity_stars = ":star:" * max(1, int(item.get("rarity", 1) or 1))
    rarity_name = item.get("rarity_label") or item.get("rarity_name") or str(item.get("rarity", ""))
    return (
        f"{index}{prefix}{item['uma_name']}\n"
        f"{rarity_stars} {rarity_name} | Overall {item['overall']} | Wins: {item.get('wins', 0)}"
    )
