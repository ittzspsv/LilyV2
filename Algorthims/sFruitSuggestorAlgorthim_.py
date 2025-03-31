import random
from Values.sStockValueJSON import *

#fruit_s_dict = {"Kitsune": 215000000, "Yeti": 140000000, "Leopard": 55000000, "Spirit": 10000000, "Gas": 80000000, "Control": 35000000, "Venom": 8000000, "Shadow": 6500000, "Dough": 30000000, "Trex": 20000000, "Mammoth": 8000000, "Gravity": 55000000, "Blizzard": 5000000, "Pain": 2000000, "Rumble": 7000000, "Portal": 11000000, "Phoenix": 2750000, "Sound": 2500000, "Spider": 1500000, "Love": 1500000, "Buddha": 11000000, "Quake": 1000000, "Magma": 1150000, "Ghost": 800000, "Barrier": 800000, "Rubber": 700000, "Light": 700000, "Diamond": 1500000, "Dark": 400000, "Sand": 420000, "Ice": 550000, "Falcon": 300000, "Flame": 800000, "Spike": 180000, "Smoke": 100000, "Bomb": 80000, "Spring": 60000, "Blade": 50000, "Spin": 7500, "Rocket": 5000}

# Get user input
'''
user_fruits = [fruit.title() for fruit in input("Enter your fruits (space-separated): ").split()]
num_return_fruits = int(input("How many fruits do you want in return? (1-4): "))
num_trade_options = int(input("How many trade options would you like to see? (1-5): "))'''

# Function to generate trade suggestions
def get_trade_suggestions(user_fruits, num_return_fruits, num_trade_options):
    user_total_value = sum(fruit_s_dict.get(fruit, 0) for fruit in user_fruits)
    trade_options = set()  # Store unique fruit combinations
    available_fruits = [fruit for fruit in fruit_s_dict.keys() if fruit not in user_fruits]  # Exclude user's fruits
    retries = 0  # Prevent infinite loops

    while len(trade_options) < num_trade_options and retries < 10000 :  # Limit retries to prevent infinite loop
        trade_fruits = tuple(sorted(random.choices(available_fruits, k=num_return_fruits), key=lambda x: fruit_s_dict[x], reverse=True))
        trade_value = sum(fruit_s_dict[fruit] for fruit in trade_fruits)

        min_value = user_total_value * 0.90  # Minimum -10%
        max_value = user_total_value * 1.10  # Maximum +10%

        if min_value <= trade_value <= max_value and trade_fruits not in trade_options:
            trade_options.add(trade_fruits)  # Add unique trade
        else:
            retries += 1  # Increase retry count if trade is invalid

    sorted_trades_dict = {}
    for fruits in trade_options:
        total_value = sum(fruit_s_dict[fruit] for fruit in fruits)
        sorted_trades_dict.setdefault(total_value, []).append(fruits)

    sorted_trades_dict = dict(sorted(sorted_trades_dict.items(), reverse=True))

    return sorted_trades_dict, user_total_value

'''
# Generate and display trade options
trade_suggestions, user_total_values = get_trade_suggestions(user_fruits, num_return_fruits, num_trade_options)

for key, values in trade_suggestions.items():
    print(f"{values} {key}")'''
