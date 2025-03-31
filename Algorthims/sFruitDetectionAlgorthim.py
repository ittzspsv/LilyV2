import json
import re
from rapidfuzz import process, fuzz
from Algorthims.sTradeFormatAlgorthim import *


value_data_path = "ValueData.json"
with open(value_data_path, "r", encoding="utf-8") as json_file:
    value_data = json.load(json_file)

fruit_names = sorted([fruit["name"].lower() for fruit in value_data], key=len, reverse=True)
fruit_set = set(fruit_names)

def extract_trade_details(message):
    message = message.lower()
    message = re.sub(r'[^\w\s]', '', message)
    message_parsed = message.split()

    trade_split_index = message_parsed.index("for") if "for" in message_parsed else -1
    your_message_split = message_parsed[:trade_split_index]
    their_message_split = message_parsed[trade_split_index + 1:]

    def extract_fruits(message_split):
        fruit_list = []
        fruit_types = []
        
        i = 0
        while i < len(message_split):
            matched_fruit = None
            matched_length = 0

            for fruit in fruit_names:
                matched_fruit = MatchFruitSet(' '.join(message_split[i:i + len(fruit.split())]), fruit_set)
                if matched_fruit:
                    matched_length = len(matched_fruit.split())
                    break

            if matched_fruit:
                counter = 1
                
                if i > 0 and message_split[i - 1].isdigit():
                    counter = min(int(message_split[i - 1]), 10)

                fruit_type = "Permanent" if (i > 0 and isPermanentMatch(message_split[i - 1])) else "Physical"

                
                for _ in range(counter):
                    fruit_list.append(matched_fruit)
                    fruit_types.append(fruit_type)

                i += matched_length - 1

            i += 1
        
        return fruit_list, fruit_types

    your_fruits, your_fruit_type = extract_fruits(your_message_split)
    their_fruits, their_fruit_types = extract_fruits(their_message_split)

    
    your_fruits = [yourfruit.title() for yourfruit in your_fruits]
    their_fruits = [theirfruit.title() for theirfruit in their_fruits]

    
    return your_fruits, your_fruit_type, their_fruits, their_fruit_types
