import json
import random

with open("ValueData.json", "r") as f:
    raw_fruit_data = json.load(f)

fruit_data = raw_fruit_data[:-2]

def parse_value(val):
    return int(val.replace(",", "")) if val else 0

def build_candidate_pool(user_fruits, suggest_permanent, suggest_gamepass):
    pool = []
    for fruit in fruit_data:
        name = fruit["name"]
        if name in user_fruits or fruit["category"] == "limited":
            continue

        category = fruit["category"]
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

def generate_suggestion(pool, target_value, min_ratio=0.9, max_ratio=1.1, max_attempts=15000, max_gamepass=1):
    target_min = int(target_value * min_ratio)
    target_max = int(target_value * max_ratio)

    best_valid = None

    for i in range(max_attempts):
        selected = []
        total = 0
        perm_count = 0
        gp_count = 0

        while len(selected) < 4 and total < target_max:
            name, ftype, val, category = random.choice(pool)

            if ftype == "permanent" and perm_count >= 1:
                continue
            if category == "gamepass" and gp_count >= max_gamepass:
                continue

            if total + val > target_max:
                break

            selected.append((name, ftype, val, category))
            total += val

            if ftype == "permanent":
                perm_count += 1
            if category == "gamepass":
                gp_count += 1

        if total >= target_min and total <= target_max:
            return selected 
        elif total >= target_min and best_valid is None:
            best_valid = selected

    return best_valid or [] 

def trade_suggestor(user_fruits, fruit_types, suggest_permanent=False, suggest_gamepass=False):

    total_value = 0
    for name, ftype in zip(user_fruits, fruit_types):
        for fruit in fruit_data:
            if fruit["name"] == name:
                val = parse_value(fruit[f"{ftype}_value"])
                total_value += val
                break

    pool = build_candidate_pool(user_fruits, suggest_permanent, suggest_gamepass)
    suggestion = generate_suggestion(pool, total_value)

    if not suggestion:
        print("No valid permanent suggestions found, switching to gamepass fruits.")
        pool = build_candidate_pool(user_fruits, suggest_permanent=False, suggest_gamepass=True)
        suggestion = generate_suggestion(pool, total_value)

    fruit_names = [item[0] for item in suggestion]
    fruit_types = [item[1] for item in suggestion]
    
    suggested_value = sum(item[2] for item in suggestion)

    print(f"Total Value of User's Fruits: {total_value}")
    print(f"Suggested Fruits: {fruit_names}")
    print(f"Suggested Types: {fruit_types}")
    print(f"Total Value of Suggested Fruits: {suggested_value}")
    
    return fruit_names, fruit_types


user_fruits = ["Buddha", "Buddha", "Buddha", "Buddha"]
fruit_types = ["physical", "physical", "physical", "physical"]

names, types = trade_suggestor(
    user_fruits, fruit_types,
    suggest_permanent=False,
    suggest_gamepass=False
)
