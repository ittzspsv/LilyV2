import re
import json

value_data_path = "ValueData.json"

with open(value_data_path, "r", encoding="utf-8") as json_file:
    value_data = json.load(json_file)
fruit_names = {fruit["name"].lower() for fruit in value_data}


def is_valid_trade_format(message, fruit_names):
    message = message.lower().strip()

    # Remove unnecessary words but preserve structure
    message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

    # Split the trade into two parts (before & after "for")
    trade_parts = message.split(" for ")

    if len(trade_parts) < 2:
        return False  # No clear trade format detected

    # Remove unnecessary prefixes and pronouns
    clean_your_side = re.sub(r"^(i want to|i wanna|i want|trade|i traded|i trade|trade|traded|trade my|traded my)\s*(trade my|trade|my)?\s*", "", trade_parts[0]).strip()
    clean_their_side = re.sub(r"\bhis|their|her\b", "", trade_parts[1]).strip()

    # Split items by comma, handling spaces properly
    your_side = [item.strip() for item in clean_your_side.split(",")]
    their_side = [item.strip() for item in clean_their_side.split(",")]

    def extract_fruits(fruit_list):
        fruits = []

        for item in fruit_list:
            item = item.strip()

            # Remove "perm" or "permanent" at the beginning
            item = re.sub(r"^(perm|permanent)\s+", "", item)

            # Check if the cleaned item exists in fruit database
            if item in fruit_names:
                fruits.append(item)

        return fruits

    # Extract valid fruits
    your_fruits = extract_fruits(your_side)
    their_fruits = extract_fruits(their_side)

    # Ensure at least one valid fruit exists on both sides
    return bool(your_fruits) and bool(their_fruits)

'''test_bool = is_valid_trade_format("i traded my venom, spider for spirit w or l?", fruit_names)
print(test_bool)'''