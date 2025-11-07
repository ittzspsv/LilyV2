import random
import Config.sValueConfig as VC

def parse_value(val):
    if val is None:
        return 0
    if isinstance(val, str):
        return int(val.replace(",", ""))
    return int(val)

async def get_fruit_value(fruit_name, value_type="physical"):
    cursor = await VC.vdb.execute(
        f"SELECT {value_type}_value FROM BF_ItemValues WHERE LOWER(name) = ?",
        (fruit_name.lower(),)
    )
    row = await cursor.fetchone()
    await cursor.close()
    return parse_value(row[0]) if row else 0

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

async def build_candidate_pool(user_fruits, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False):
    pool = []
    cursor = await VC.vdb.execute(
        "SELECT name, category, physical_value, permanent_value FROM BF_ItemValues"
    )
    async for name, category, physical_value, permanent_value in cursor:
        if name in user_fruits or category == "limited":
            continue
        if not suggest_fruit_skins and category.lower() == 'limited skin':
            continue

        phys_val = parse_value(physical_value)
        perm_val = parse_value(permanent_value)

        if category in ("gamepass", "limited skin") and (suggest_gamepass or suggest_fruit_skins) and phys_val > 0:
            pool.append((name, "physical", phys_val, "gamepass"))

        elif category not in ("gamepass", "limited skin"):
            if suggest_permanent and perm_val > 0:
                pool.append((name, "permanent", perm_val, "fruit"))
            if phys_val > 0:
                pool.append((name, "physical", phys_val, "fruit"))

    await cursor.close()
    return pool

def generate_suggestion(pool, target_value, min_ratio=1.03, max_ratio=1.1, max_attempts=15000, max_gamepass=2):
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

        while len(selected) < 4 and total < target_max and attempt_pool:
            item = random.choice(attempt_pool)
            attempt_pool.remove(item)

            name, ftype, val, category = item

            if ftype == "permanent" and perm_count >= 1:
                continue
            if category == "gamepass" and gp_count >= max_gamepass:
                continue
            if any(s[0] == name for s in selected):
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
            return selected
        elif total >= target_min and best_valid is None:
            best_valid = selected

    return best_valid or []

async def trade_suggestor(user_fruits, fruit_types, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False, overpay=False):
    total_value = 0

    for name, ftype in zip(user_fruits, fruit_types):
        total_value += await get_fruit_value(name, ftype.lower())
    
    if overpay:
        total_value += total_value * 0.15

    pool = await build_candidate_pool(user_fruits, suggest_permanent, suggest_gamepass, suggest_fruit_skins)
    suggestion = generate_suggestion(pool, total_value)

    if not suggestion:
        pool = await build_candidate_pool(user_fruits, suggest_permanent=False, suggest_gamepass=False, suggest_fruit_skins=False)
        suggestion = generate_suggestion(pool, total_value)

    if not suggestion:
        return [], [], False

    fruit_names = [item[0] for item in suggestion]
    fruit_types = [item[1] for item in suggestion]

    return fruit_names, fruit_types, True