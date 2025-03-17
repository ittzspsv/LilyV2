import re
import json

value_data_path = "ValueData.json"

with open(value_data_path, "r", encoding="utf-8") as json_file:
    value_data = json.load(json_file)
fruit_names = {fruit["name"].lower() for fruit in value_data}


def is_valid_trade_format(message, fruit_names):
    message = message.lower().strip()

    message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

    trade_parts = message.split(" for ")

    if len(trade_parts) < 2:
        return False 

    clean_your_side = re.sub(r"^(i (got|gave|want to|wanna|want) |(i )?(traded|trade)( my)? )", "", trade_parts[0]).strip()
    clean_their_side = re.sub(r"\bhis|their|her|is it|that\b", "", trade_parts[1]).strip()

    def extract_fruits(text):
        fruits = []
        words = re.split(r",\s*|\s+", text)

        i = 0
        while i < len(words):
            item = words[i]

            if item in ("perm", "permanent"):
                i += 1
                if i < len(words):
                    item = words[i]

            for length in range(3, 0, -1):  
                possible_fruit = " ".join(words[i:i+length])
                if possible_fruit in fruit_names:
                    fruits.append(possible_fruit)
                    i += length - 1
                    break  

            i += 1

        return fruits

    your_fruits = extract_fruits(clean_your_side)
    their_fruits = extract_fruits(clean_their_side)

    return bool(your_fruits) and bool(their_fruits)