import re
import json
from rapidfuzz import process, fuzz

value_data_path = "src/ValueData.json"

with open(value_data_path, "r", encoding="utf-8") as json_file:
    value_data = json.load(json_file)
fruit_names = {fruit["name"].lower() for fruit in value_data}

alias_map = {}

for fruit in value_data:
    real_name = fruit["name"].lower()
    for alias in fruit.get("aliases", []):
        alias_map[alias.lower()] = real_name

'''Trade Initializer are the words that people uses to start the trade'''
TradeInitializer = [
    "i got", "i gave", "i want to", "i wanna", "i want", 
    "i traded", "i trade", "i traded my", "i trade my"
]

'''OpponentTradeSplitter are the words that uses to split the trade messages for'''
OpponentTradeSplitter = ["his", "their", "her", "is it", "that"]

def predict_trade_message(text, phrases, threshold=70):
    words = text.split()
    corrected_text = text 

    for phrase in phrases:
        best_match = process.extractOne(text, [phrase], scorer=fuzz.ratio)
        if best_match:
            match_word, score, _ = best_match
            if score >= threshold:  
                corrected_text = corrected_text.replace(match_word, "").strip()

    return corrected_text


#ACCRUATE FRUIT MATCHING ALGORTHIM USING RAPIDFUZZ
def MatchFruit(fruits, data, threshold = 80):
    best_match, score, _ = process.extractOne(fruits, data.keys(), scorer=fuzz.ratio)
    if score >= threshold:
        return best_match, data[best_match]
    else:
        pass

def MatchFruitSet(fruit: str, data: set, threshold=80):
    if not fruit or not data:
        return None  

    fruit = fruit.lower().strip()
    if not fruit:
        return None  

    fruit_words = set(fruit.split())
    filtered_fruits = set()

    all_names = set(data)
    all_names.update(alias_map.keys())

    for f in all_names:
        if not f:
            continue

        if set(f.split()) == fruit_words:
            return alias_map.get(f, f)

        if f[0].lower() == fruit[0]:
            filtered_fruits.add(f)

    if not filtered_fruits:
        return None

    match = process.extractOne(fruit, filtered_fruits, scorer=fuzz.ratio)

    if match:
        best_match, score = match[0], match[1]
        if score >= threshold:
            return alias_map.get(best_match, best_match)

    return None

def isPermanentMatch(item, threshold=70):
    perm_words = {"perm", "permanent"}
    best_match, score, _ = process.extractOne(item, perm_words, scorer=fuzz.ratio)

    return score >= threshold

def PermanentMatch(item, threshold=70):
    perm_words = {"perm", "permanent"}
    best_match, score, _ = process.extractOne(item, perm_words, scorer=fuzz.ratio)

    if score >= threshold:
        return "permanent"
    return None

def is_valid_trade_format(message, fruit_names):
    message = message.lower().strip()

    message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

    trade_parts = message.split(" for ")
    if len(trade_parts) < 2:
        return False  

    clean_your_side = predict_trade_message(trade_parts[0], TradeInitializer)
    clean_their_side = predict_trade_message(trade_parts[1], OpponentTradeSplitter)

    def extract_fruits(text):
        fruits = []
        words = re.split(r",\s*|\s+", text)

        i = 0
        while i < len(words):
            item = words[i]

            if isPermanentMatch(item):
                i += 1
                if i < len(words):
                    item = words[i]

            for length in range(3, 0, -1):  
                possible_fruit = " ".join(words[i:i+length])
                matched_fruit = MatchFruitSet(possible_fruit, fruit_names)
                
                if matched_fruit:
                    fruits.append(matched_fruit)
                    i += length - 1
                    break  

            i += 1

        return fruits

    your_fruits = extract_fruits(clean_your_side)
    their_fruits = extract_fruits(clean_their_side)

    return bool(your_fruits) and bool(their_fruits)

def is_valid_trade_suggestor_format(message, fruit_names):
    message = message.lower().strip()

    message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

    if "for" not in message:
        return False
    trade_parts = message.split(" for ")

    clean_your_side = predict_trade_message(trade_parts[0], TradeInitializer)

    def extract_fruits(text):
        fruits = []
        words = re.split(r",\s*|\s+", text)

        i = 0
        while i < len(words):
            item = words[i]

            if isPermanentMatch(item):
                i += 1
                if i < len(words):
                    item = words[i]

            for length in range(3, 0, -1):  
                possible_fruit = " ".join(words[i:i+length])
                matched_fruit = MatchFruitSet(possible_fruit, fruit_names)
                
                if matched_fruit:
                    fruits.append(matched_fruit)
                    i += length - 1
                    break  

            i += 1

        return fruits

    your_fruits = extract_fruits(clean_your_side)

    return bool(your_fruits)