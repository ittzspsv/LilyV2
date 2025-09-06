import re
from rapidfuzz import process, fuzz
import Config.sValueConfig as VC

TradeInitializer = [
    "i got", "i gave", "i want to", "i wanna", "i want", 
    "i traded", "i trade", "i traded my", "i trade my"
]

OpponentTradeSplitter = ["his", "their", "her", "is it", "that"]


async def get_all_fruit_names():
    cursor = await VC.vdb.execute("SELECT name, aliases FROM BF_ItemValues")
    rows = await cursor.fetchall()
    await cursor.close()

    fruit_names = set()
    alias_map = {}

    for name, aliases in rows:
        if name:
            fruit_names.add(name.lower())
        if aliases:
            for alias in aliases.split(","):
                alias_map[alias.strip().lower()] = name.lower()

    return fruit_names, alias_map

def predict_trade_message(text, phrases, threshold=70):
    corrected_text = text
    for phrase in phrases:
        best_match = process.extractOne(text, [phrase], scorer=fuzz.ratio)
        if best_match:
            match_word, score, _ = best_match
            if score >= threshold:
                corrected_text = corrected_text.replace(match_word, "").strip()
    return corrected_text

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

# ------------------- Matching -------------------

async def MatchFruit(fruits, data, threshold=80):
    best_match, score, _ = process.extractOne(fruits, data.keys(), scorer=fuzz.ratio)
    if score >= threshold:
        return best_match, data[best_match]
    else:
        pass


async def MatchFruitSet(fruit: str, fruit_names: set, alias_map: dict, threshold=80):
    if not fruit or not fruit_names:
        return None  

    fruit = fruit.lower().strip()
    if not fruit:
        return None  

    cleaned_alias_map = {}
    for k, v in alias_map.items():
        clean_key = k.strip("[]\"' ").lower() 
        cleaned_alias_map[clean_key] = v.lower() if isinstance(v, str) else v

    fruit_words = set(fruit.split())
    filtered_fruits = set()

    all_names = set(fruit_names)
    all_names.update(cleaned_alias_map.keys())

    for f in all_names:
        if not f:
            continue

        if set(f.split()) == fruit_words:
            return cleaned_alias_map.get(f, f)

        if f[0].lower() == fruit[0]:
            filtered_fruits.add(f)

    if not filtered_fruits:
        return None

    # Fuzzy match
    match = process.extractOne(fruit, filtered_fruits, scorer=fuzz.ratio)
    if match:
        best_match, score = match[0], match[1]
        if score >= threshold:
            return cleaned_alias_map.get(best_match, best_match)

    return None


async def is_valid_trade_format(message):
    message = message.lower().strip()
    message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

    trade_parts = message.split(" for ")
    if len(trade_parts) < 2:
        return False

    clean_your_side = predict_trade_message(trade_parts[0], TradeInitializer)
    clean_their_side = predict_trade_message(trade_parts[1], OpponentTradeSplitter)

    fruit_names, alias_map = await get_all_fruit_names()

    async def extract_fruits(text):
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
                matched_fruit = await MatchFruitSet(possible_fruit, fruit_names, alias_map)

                if matched_fruit:
                    fruits.append(matched_fruit)
                    i += length - 1
                    break

            i += 1
        return fruits

    your_fruits = await extract_fruits(clean_your_side)
    their_fruits = await extract_fruits(clean_their_side)

    return bool(your_fruits) and bool(their_fruits)

async def is_valid_trade_suggestor_format(message):
    message = message.lower().strip()
    message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

    if "for" not in message:
        return False
    trade_parts = message.split(" for ")

    clean_your_side = predict_trade_message(trade_parts[0], TradeInitializer)

    # Fetch fruits from DB once
    fruit_names, alias_map = await get_all_fruit_names()

    async def extract_fruits(text):
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
                matched_fruit = await MatchFruitSet(possible_fruit, fruit_names, alias_map)

                if matched_fruit:
                    fruits.append(matched_fruit)
                    i += length - 1
                    break

            i += 1
        return fruits

    your_fruits = await extract_fruits(clean_your_side)

    return bool(your_fruits)

