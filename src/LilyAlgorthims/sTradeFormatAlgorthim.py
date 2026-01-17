import re
from rapidfuzz import process, fuzz
import Config.sValueConfig as VC
import LilyAlgorthims.sFruitDetectionAlgorthim as FDA
import LilyAlgorthims.sFruitDetectionAlgorthimEmoji as FDAE

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

    all_names = set(x.lower() for x in fruit_names)
    all_names.update(cleaned_alias_map.keys())

    if fruit in cleaned_alias_map:
        return cleaned_alias_map[fruit]


    if fruit in all_names:
        return cleaned_alias_map.get(fruit, fruit)

    fruit_words = set(fruit.split())
    for f in all_names:
        if not f:
            continue
        if set(f.split()) == fruit_words:
            return cleaned_alias_map.get(f, f)

    filtered_fruits = [f for f in all_names if f and f[0] == fruit[0]]
    if not filtered_fruits:
        return None

    effective_threshold = threshold
    if len(fruit) <= 3:
        effective_threshold = max(threshold, 88)

    match = process.extractOne(fruit, filtered_fruits, scorer=fuzz.ratio)
    if match:
        best_match, score = match[0], match[1]
        if score >= effective_threshold:
            return cleaned_alias_map.get(best_match, best_match)

    return None


async def is_valid_trade_format(message):
    try:
        message = message.lower().strip()
        message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

        trade_parts = message.split(" for ")
        if len(trade_parts) < 2:
            return False
        if "nlf" in trade_parts[1].split():
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
    except:
        return False

async def is_valid_emoji_trade_format(message: str):
    try:
        message = message.lower().strip()
        message = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", message).strip()

        fruit_names, alias_map = await get_all_fruit_names()
        trade_separators = ["pointtrade", "point_trade", "trade_pointer"]

        trade_parts = None
        for sep in trade_separators:
            if sep in message:
                trade_parts = re.split(re.escape(sep), message, maxsplit=1)
                break

        if not trade_parts or len(trade_parts) != 2:
            return False

        left_side, right_side = trade_parts[0].strip(), trade_parts[1].strip()

        async def extract_valid_items(text: str):
            items = []

            items.extend(re.findall(r"<a?:([\w\d_]+):\d+>", text))

            words = re.split(r"[,\s]+", text)
            for w in words:
                if w:
                    valid_fruit = await MatchFruitSet(w, fruit_names, alias_map)
                    if valid_fruit:
                        items.append(valid_fruit)

            return items

        left_items = await extract_valid_items(left_side)
        right_items = await extract_valid_items(right_side)

        return bool(left_items) and bool(right_items)
    except:
        return False

async def is_valid_trade_suggestor_format(message: str):
    try:
        msg = message.lower().strip()
        trimmed = re.sub(r"(for\b.*?\bnlf\b).*", r"\1", msg)

        if "nlf" in trimmed:
            trimmed = trimmed[:trimmed.find("nlf")].strip()

        your_fruits, _, their_fruits, _ = await FDA.extract_trade_details(trimmed)

        return bool((bool(your_fruits) != bool(their_fruits)))

    except:
        return False

async def is_valid_trade_suggestor_format_emoji(message: str):
    try:
        your_fruits, _, their_fruits, _ = await FDAE.extract_fruits_emoji(message)
        
        return bool((bool(your_fruits) != bool(their_fruits)))
    except:
        return False