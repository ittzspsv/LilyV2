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

async def BuildFruitFilterationMap(user_fruits, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False):
    excluded = tuple(f.lower() for f in user_fruits) or ("",)
    
    category_map = {
        'common'   : 1,
        'uncommon' : 2,
        'rare'     : 3,
        'legendary': 4,
        'mythical' : 5,
        'gamepass' : 6
    }


    placeholders = ",".join("?" * len(excluded))
    query = f"SELECT DISTINCT LOWER(category) FROM BF_ItemValues WHERE LOWER(name) IN ({placeholders})"
    cursor = await VC.vdb.execute(query, excluded)
    user_categories = [row[0] for row in await cursor.fetchall()]
    await cursor.close()


    rarity_levels = [category_map[c] for c in user_categories if c in category_map]

    if rarity_levels:
        user_max_rarity = max(rarity_levels)
    else:
        user_max_rarity = 6 


    if not suggest_permanent:
        allowed_categories = [
            cat for cat, lvl in category_map.items()
            if lvl >= abs(user_max_rarity - 1)
        ]
    else:
        allowed_categories = list(category_map.keys())

    if not suggest_gamepass:
        allowed_categories.remove('gamepass')

    base_query = f"""
        SELECT name, category, physical_value, permanent_value
        FROM BF_ItemValues
        WHERE LOWER(name) NOT IN ({placeholders})
          AND LOWER(category) IN ({",".join("?" * len(allowed_categories))})
          AND LOWER(category) != 'limited'
    """

    if not suggest_fruit_skins:
        base_query += " AND LOWER(category) != 'limited skin'"

    params = list(excluded) + allowed_categories
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
    print("POOL : 1")
    print(pool)
    return pool

def SuggestBuilder(pool, target_value, min_ratio=0.80, max_ratio=1.1, max_attempts=15000, max_gamepass=2):
    if not pool:
        return []

    target_min = int(target_value * min_ratio)
    target_max = int(target_value * max_ratio)


    best_valid = None

    for _ in range(max_attempts):
        selected = []
        total = 0
        perm_count = 0
        gp_count = 0

        attempt_pool = pool.copy()
        random.shuffle(attempt_pool)

        while len(selected) < 4 and attempt_pool:
            item = random.choice(attempt_pool)
            attempt_pool.remove(item)

            name, ftype, val, category = item

            if any(s[0] == name for s in selected):
                continue

            if ftype == "permanent" and perm_count >= 1:
                continue
            if category == "gamepass" and gp_count >= max_gamepass:
                continue

            if total + val > target_max:
                continue

            selected.append(item)
            total += val

            if ftype == "permanent":
                perm_count += 1
            if category == "gamepass":
                gp_count += 1

            if target_min <= total <= target_max:
                break

        if target_min <= total <= target_max:
            return selected

        if total >= target_min and (best_valid is None or abs(total - target_value) < abs(sum(v[2] for v in best_valid) - target_value)):
            best_valid = selected

    return best_valid or []

async def trade_suggestor(user_fruits, fruit_types, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False, overpay=False):
    total_value = 0

    for name, ftype in zip(user_fruits, fruit_types):
        total_value += await get_fruit_value(name, ftype.lower())
    
    if overpay:
        total_value += total_value * 0.15

    pool = await BuildFruitFilterationMap(user_fruits, suggest_permanent, suggest_gamepass, suggest_fruit_skins)
    suggestion = SuggestBuilder(pool, total_value)

    if not suggestion:
        total_value += total_value * 0.15
        pool = await BuildFruitFilterationMap(user_fruits, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False)
        suggestion = SuggestBuilder(pool, total_value)

    if not suggestion:
        return [], [], False

    fruit_names = [item[0] for item in suggestion]
    fruit_types = [item[1] for item in suggestion]

    return fruit_names, fruit_types, True