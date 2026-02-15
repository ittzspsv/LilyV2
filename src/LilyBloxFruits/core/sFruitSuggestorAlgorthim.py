import random
import Config.sValueConfig as VC


import LilyBloxFruits.sLilyBloxFruitsCache as BFC

from typing import List, Optional, Dict, Union, Tuple, Literal


async def get_fruit_value(fruit_name: Optional[str], value_type: str = "physical") -> int:
    if not fruit_name:
        return 0
    fruit = BFC.item_dict.get(fruit_name.title())
    if not fruit:
        return 0
    return fruit.get(f"{value_type}_value") or 0

async def fetch_all_fruits() -> List[Dict[str, Union[str, int]]]:
    '''
    cursor = await VC.vdb.execute(
        "SELECT name, category, physical_value, permanent_value FROM BF_ItemValues"
    )
    rows = await cursor.fetchall()
    await cursor.close()
    fruits = []
    for row in rows:
        fruits.append({
            "name": row[0],
            "category": row[1],
            "physical_value": row[2] or 0,
            "permanent_value": row[3] or 0
        })
    return fruits
    '''

    return BFC.item_list_minimal

async def BuildFruitFilterationMap(user_fruits, suggest_permanent: bool = False, suggest_gamepass: bool = False, suggest_fruit_skins: bool = False,neglect_fruits: Optional[List] = None) -> List:
    if neglect_fruits is None:
        neglect_fruits = []

    excluded = tuple(f.lower() for f in user_fruits) or ("",)
    neglected = tuple(f.lower() for f in neglect_fruits)

    blocked_fruits = set(excluded + neglected)

    user_categories = [
        BFC.name_to_category[f]
        for f in excluded
        if f in BFC.name_to_category
    ]

    rarity_levels = [
        BFC.category_map[c]
        for c in user_categories
        if c in BFC.category_map
    ]

    user_max_rarity = max(rarity_levels) if rarity_levels else 6

    if not suggest_permanent:
        min_level = abs(user_max_rarity - 1)
        allowed_categories = {
            cat
            for cat, lvl in BFC.category_map.items()
            if lvl >= min_level
        }
    else:
        allowed_categories = set(BFC.category_map.keys())

    if not suggest_gamepass:
        allowed_categories.discard("gamepass")

    pool = []

    for item in BFC.item_list_minimal:

        name_lower = item["name_lower"]
        category = item["category"]

        if name_lower in blocked_fruits:
            continue

        if category not in allowed_categories:
            continue

        if category == "limited":
            continue

        if not suggest_fruit_skins and category == "limited skin":
            continue

        name = item["name"]
        phys_val = item["physical_value"]
        perm_val = item["permanent_value"]

        if category in ("gamepass", "limited skin"):
            if (suggest_gamepass or suggest_fruit_skins) and phys_val > 0:
                pool.append((name, "physical", phys_val, "gamepass"))

        else:
            if suggest_permanent and perm_val > 0:
                pool.append((name, "permanent", perm_val, "fruit"))

            if phys_val > 0:
                pool.append((name, "physical", phys_val, "fruit"))

    return pool

def SuggestBuilder(pool: Optional[List], target_value, max_gamepass=2, overpay=False,storage_capacity=1, max_items=4) -> Optional[List]:
    if not pool:
        return []

    if not overpay:
        min_ratio = 0.80
        max_ratio = 1.10
    else:
        min_ratio = 1.03
        max_ratio = 1.10

    target_min = int(target_value * min_ratio)
    target_max = int(target_value * max_ratio)

    expanded_items = []
    for name, ftype, val, category in pool:
        for _ in range(storage_capacity):
            expanded_items.append((name, ftype, val, category))

    dp = {0: (0, 0, 0, [])}

    for name, ftype, val, category in expanded_items:
        new_dp = dp.copy()
        for total, (item_count, perm_count, gp_count, sel) in dp.items():
            if item_count + 1 > max_items:
                continue
            if ftype == "permanent" and perm_count >= 1:
                continue
            if category == "gamepass" and gp_count + 1 > max_gamepass:
                continue
            new_total = total + val
            if new_total > target_max:
                continue

            new_perm = perm_count + (1 if ftype == "permanent" else 0)
            new_gp = gp_count + (1 if category == "gamepass" else 0)
            new_sel = sel + [(name, ftype, val, category)]

            if new_total not in new_dp or abs(new_total - target_value) < abs(new_total - target_value):
                new_dp[new_total] = (item_count + 1, new_perm, new_gp, new_sel)

        dp = new_dp

    best_total = None
    best_diff = float('inf')
    best_selection = []

    for total, (_, _, _, sel) in dp.items():
        diff = abs(total - target_value)
        if target_min <= total <= target_max and diff < best_diff:
            best_diff = diff
            best_total = total
            best_selection = sel

    return best_selection

async def trade_suggestor(user_fruits, fruit_types, suggest_permanent: bool = False, suggest_gamepass: bool = False, suggest_fruit_skins: bool = False, overpay: bool = False, neglect_fruits: List | None = None, storage_capacity=1) -> Union[Tuple[List, List, Literal[True]], Tuple[List, List, Literal[False]]]:
    total_value = 0
    if neglect_fruits is None:
        neglect_fruits = []

    for name, ftype in zip(user_fruits, fruit_types):
        total_value += await get_fruit_value(name, ftype.lower())
    
    if overpay:
        total_value += total_value * 0.15

    pool = await BuildFruitFilterationMap(user_fruits, suggest_permanent, suggest_gamepass, suggest_fruit_skins, neglect_fruits)
    suggestion = SuggestBuilder(pool=pool, target_value=total_value, storage_capacity=storage_capacity)

    if not suggestion:
        total_value += total_value * 0.15
        pool = await BuildFruitFilterationMap(user_fruits, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False, neglect_fruits=neglect_fruits)
        suggestion = SuggestBuilder(pool=pool, target_value=total_value, storage_capacity=storage_capacity)

    if not suggestion:
        return [], [], False

    fruit_names = [item[0] for item in suggestion]
    fruit_types = [item[1] for item in suggestion]

    return fruit_names, fruit_types, True