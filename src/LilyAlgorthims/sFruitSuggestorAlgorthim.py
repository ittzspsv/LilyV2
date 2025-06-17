import json
import random

with open("src/ValueData.json", "r") as f:
    raw_fruit_data = json.load(f)

fruit_data = raw_fruit_data[:-2]

def parse_value(val):
    return int(val.replace(",", "")) if val else 0

def build_candidate_pool(user_fruits, suggest_permanent, suggest_gamepass):
    pool = []
    for fruit in fruit_data:
        name = fruit["name"]
        category = fruit["category"]

        if name in user_fruits or category == "limited":
            continue

        if category == "gamepass" and suggest_gamepass:
            val = parse_value(fruit["physical_value"])
            if val > 0:
                pool.append((name, "physical", val, "gamepass"))

        elif category != "gamepass":
            perm_val = parse_value(fruit["permanent_value"])
            phys_val = parse_value(fruit["physical_value"])

            if suggest_permanent and perm_val > 0:
                pool.append((name, "permanent", perm_val, "fruit"))
            if phys_val > 0:
                pool.append((name, "physical", phys_val, "fruit"))
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

def trade_suggestor(user_fruits, fruit_types, suggest_permanent=False, suggest_gamepass=False):
    total_value = 0

    for name, ftype in zip(user_fruits, fruit_types):
        for fruit in fruit_data:
            if fruit["name"] == name:
                val = parse_value(fruit.get(f"{ftype.lower()}_value", "0"))
                total_value += val
                break

    pool = build_candidate_pool(user_fruits, suggest_permanent, suggest_gamepass)
    suggestion = generate_suggestion(pool, total_value)

    if not suggestion:
        pool = build_candidate_pool(user_fruits, suggest_permanent=False, suggest_gamepass=True)
        suggestion = generate_suggestion(pool, total_value)

    if not suggestion:
        return [], [], False

    fruit_names = [item[0] for item in suggestion]
    fruit_types = [item[1] for item in suggestion]

    return fruit_names, fruit_types, True