import random
import Config.sValueConfig as VC



async def get_fruit_value(fruit_name, value_type="physical"):
    cursor = await VC.vdb.execute(
        f"SELECT {value_type}_value FROM BF_ItemValues WHERE LOWER(name) = ?",
        (fruit_name.lower(),)
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row[0] if row else 0

async def fetch_all_fruits():
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

async def BuildFruitFilterationMap(user_fruits,suggest_permanent=False,suggest_gamepass=False,suggest_fruit_skins=False,neglect_fruits=[]):
    excluded = tuple(f.lower() for f in user_fruits) or ("",)
    neglected = tuple(f.lower() for f in neglect_fruits)

    blocked_fruits = excluded + neglected

    category_map = {
        'common': 1,
        'uncommon': 2,
        'rare': 3,
        'legendary': 4,
        'mythical': 5,
        'gamepass': 6
    }

    placeholders = ",".join("?" * len(excluded))
    query = f"""
        SELECT DISTINCT LOWER(category)
        FROM BF_ItemValues
        WHERE LOWER(name) IN ({placeholders})
    """

    cursor = await VC.vdb.execute(query, excluded)
    user_categories = [row[0] for row in await cursor.fetchall()]
    await cursor.close()

    rarity_levels = [category_map[c] for c in user_categories if c in category_map]
    user_max_rarity = max(rarity_levels) if rarity_levels else 6

    if not suggest_permanent:
        allowed_categories = [
            cat for cat, lvl in category_map.items()
            if lvl >= abs(user_max_rarity - 1)
        ]
    else:
        allowed_categories = list(category_map.keys())

    if not suggest_gamepass and "gamepass" in allowed_categories:
        allowed_categories.remove("gamepass")

    all_blocked = blocked_fruits
    blocked_placeholders = ",".join("?" * len(all_blocked))
    category_placeholders = ",".join("?" * len(allowed_categories))

    base_query = f"""
        SELECT name, category, physical_value, permanent_value
        FROM BF_ItemValues
        WHERE LOWER(name) NOT IN ({blocked_placeholders})
          AND LOWER(category) IN ({category_placeholders})
          AND LOWER(category) != 'limited'
    """

    if not suggest_fruit_skins:
        base_query += " AND LOWER(category) != 'limited skin'"

    params = list(all_blocked) + allowed_categories

    cursor = await VC.vdb.execute(base_query, params)
    rows = await cursor.fetchall()
    await cursor.close()

    pool = []
    for name, category, phys_val, perm_val in rows:
        if category in ("gamepass", "limited skin"):
            if (suggest_gamepass or suggest_fruit_skins) and phys_val > 0:
                pool.append((name, "physical", phys_val, "gamepass"))
        else:
            if suggest_permanent and perm_val > 0:
                pool.append((name, "permanent", perm_val, "fruit"))
            if phys_val > 0:
                pool.append((name, "physical", phys_val, "fruit"))

    return pool


def SuggestBuilder(pool, target_value, max_gamepass=2, overpay=False,storage_capacity=1, max_items=4):
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

async def trade_suggestor(user_fruits, fruit_types, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False, overpay=False, neglect_fruits=[], storage_capacity=1):
    total_value = 0

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