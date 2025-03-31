from Values.sStockValueJSON import *

def get_proper_fruit_value(fruit):
    return int(fruit["physical_value"].replace(",", "").strip())

def calculate_total_value(user_fruits, value_data):
    total_value = 0
    for fruit in value_data:
        if fruit["name"] in user_fruits:
            total_value += get_proper_fruit_value(fruit) * user_fruits.count(fruit["name"])
    return total_value

def get_valid_fruits(user_fruits, value_data):
    valid_fruits = []
    for fruit in value_data:
            
            valid_fruits.append(fruit)
    return valid_fruits

def sort_fruits_by_value(fruits):
    for i in range(len(fruits)):
        for j in range(i + 1, len(fruits)):
            if fruits[i][1] < fruits[j][1]:
                fruits[i], fruits[j] = fruits[j], fruits[i]
    return fruits

def suggest_trade(user_fruits, value_data, max_fruits=4):
    total_value = calculate_total_value(user_fruits, value_data)
    print(f"Total Trade Value: {total_value}")

    valid_fruits = get_valid_fruits(user_fruits, value_data)
    if not valid_fruits:
        return []

    valid_fruits.sort(key=get_proper_fruit_value, reverse=True)

    selected_fruits = []
    remaining_value = total_value
    gamepass_limit = False

    for fruit in valid_fruits:
        fruit_value = get_proper_fruit_value(fruit)
        
        if fruit["category"] == "gamepass" and not gamepass_limit:
            if fruit_value <= remaining_value:
                selected_fruits.append((fruit["name"], fruit_value))
                remaining_value -= fruit_value
                gamepass_limit = True
            continue
        
        while fruit_value <= remaining_value and len(selected_fruits) < max_fruits:
            selected_fruits.append((fruit["name"], fruit_value))
            remaining_value -= fruit_value
            
        if remaining_value <= 0:
            break

    selected_fruits = sort_fruits_by_value(selected_fruits)[:max_fruits]
    return selected_fruits

while True:
    user_fruits = input("Trade Format: ").title().strip().split()
    suggested_trade = suggest_trade(user_fruits, value_data)

    print("\nSuggested Trade:")
    if suggested_trade:
        total_suggested_value = 0
        for fruit, value in suggested_trade:
            print(f"{fruit}: {value}")
            total_suggested_value += value
        print(f"Total Value of suggested side: {total_suggested_value}")
    else:
        print("No suitable trade found.")