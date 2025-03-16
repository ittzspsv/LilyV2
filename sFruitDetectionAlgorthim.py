import re
import json

value_data_path = "ValueData.json"

with open(value_data_path, "r", encoding="utf-8") as json_file:
    value_data = json.load(json_file)
fruit_names = {fruit["name"].lower() for fruit in value_data}


def extract_trade_details(sentence):
    sentence = sentence.lower()

    sentence = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", sentence).strip()

    trade_parts = sentence.split(" for ")

    if len(trade_parts) < 2:
        return [], [], [], []

    clean_your_side = re.sub(r"^(i (want to|wanna|want) |(i )?(traded|trade)( my)? )", "", trade_parts[0]).strip()
    clean_their_side = re.sub(r"\bhis|their|her|is it|that|his|\b", "", trade_parts[1]).strip()

    your_side = clean_your_side.split(",")
    their_side = clean_their_side.split(",")

    def extract_fruits(fruit_list):
        fruits = []
        fruit_types = []

        for item in fruit_list:
            item = item.strip()

            is_permanent = item.startswith(("perm ", "permanent "))
            item = re.sub(r"^(perm|permanent)\s+", "", item)

            if item in fruit_names:
                fruit_type = "permanent" if is_permanent else "physical"
                fruits.append(item.title())
                fruit_types.append(fruit_type)

        return fruits, fruit_types

    your_fruits, your_fruit_type = extract_fruits(your_side)
    their_fruits, their_fruit_type = extract_fruits(their_side)

    return your_fruits, your_fruit_type, their_fruits, their_fruit_type


your_fruits = []
your_fruit_types = []
their_fruits = []
their_fruits_types = []

your_fruits, your_fruit_types, their_fruits, their_fruits_types = extract_trade_details("traded my perm portal for east dragon")
print(f'{your_fruits} \n{your_fruit_types} \n{their_fruits} \n{their_fruits_types}')
