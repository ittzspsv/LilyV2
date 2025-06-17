import json
import re
import string
import polars as pl
import os
import random

from rapidfuzz.fuzz import ratio
from itertools import islice
from difflib import SequenceMatcher


ComboData = {}


def LoadComboData():
    global ComboData
    with open("src/Config/JSONData/FightingStyleData.json", "r") as fdata:
        ComboData["FightingStyle"] = json.load(fdata)
    with open("src/ValueData.json", "r") as frdata:
        fruit_data = json.load(frdata)
        ComboData["Fruit"] = {i['name']: i['aliases'] for i in fruit_data}
    
    with open("src/Config/JSONData/GunData.json", "r") as gdata:
        ComboData["Guns"] = json.load(gdata)
    with open("src/Config/JSONData/SwordData.json", "r") as sdata:
        ComboData["Swords"] = json.load(sdata)
    with open("src/Config/JSONData/MiscData.json", "r") as miscdata:
        ComboData["MiscData"] = json.load(miscdata)

LoadComboData()

def ratio(a, b):
    return SequenceMatcher(None, a, b).ratio() * 100

def ComboPatternParser(message: str, threshold=95):
    message = re.sub(f"[{re.escape(string.punctuation)}]", "", message)

    known_phrases = (
        list(ComboData["Guns"].keys()) +
        list(ComboData["Swords"].keys()) +
        list(ComboData["FightingStyle"].keys()) +
        list(ComboData["Fruit"].keys()) +
        list(ComboData["MiscData"].keys())
    )
    
    known_phrases = sorted(known_phrases, key=lambda p: len(p.split()), reverse=True)
    
    reverse_map = {}
    for category, items in ComboData.items():
        for display_name, shorthands in items.items():
            for shorthand in shorthands:
                reverse_map[shorthand.lower()] = (category, display_name)
    
    words = message.title().split()
    result = []
    i = 0
    
    while i < len(words):
        matched_phrase = None
        matched_length = 0
        highest_score = 0
        
        for phrase in known_phrases:
            phrase_words = phrase.title().split()
            length = len(phrase_words)
            segment = list(islice(words, i, i + length))
            
            if len(segment) < length:
                continue
            
            segment_str = " ".join(segment).lower()
            phrase_str = " ".join(phrase_words).lower()
            
            score = ratio(segment_str, phrase_str)
            
            if score >= threshold and score > highest_score:
                matched_phrase = phrase
                matched_length = length
                highest_score = score
        
        if matched_phrase:
            result.append(matched_phrase)
            i += matched_length
        else:
            result.append(words[i])
            i += 1

    parsed_build = {}
    pretty_labels = {
        "FightingStyle": "Fighting Style",
        "Fruit": "Fruit",
        "Swords": "Sword",
        "Guns": "Gun",
        "MiscData" : "MiscData"
    }
    
    found_categories = set()
    
    for item in result:
        shorthand_match = reverse_map.get(item.lower())
        if shorthand_match:
            category, display_name = shorthand_match
            label = pretty_labels.get(category, category)
            if label not in parsed_build:
                parsed_build[label] = display_name
                found_categories.add(category)
        else:
            for category in ComboData:
                if category in found_categories:
                    continue
                if item in ComboData[category]:
                    label = pretty_labels.get(category, category)
                    parsed_build[label] = item
                    found_categories.add(category)
                    break
    
    valid_keys = set(known_phrases)
    combo_data = []
    current_key = None
    current_values = []
    
    for word in result:
        if word in valid_keys:
            if current_key is not None:
                combo_data.append((current_key, current_values))
            current_key = word
            current_values = []
        else:
            shorthand_match = reverse_map.get(word.lower())
            if shorthand_match:
                if current_key is not None:
                    combo_data.append((current_key, current_values))
                _, display_name = shorthand_match
                current_key = display_name
                current_values = []
            elif current_key:
                if word and word[0] in ['Z', 'X', 'C', 'V', 'F', 'M1']:
                    current_values.append(word[0])
                else:
                    current_values.append(random.choice(['Z', 'X', 'C', 'V', 'F', 'M1']))
    
    if current_key is not None:
        combo_data.append((current_key, current_values))
    return parsed_build, tuple(combo_data)

def ValidComboDataType(data):
    if not isinstance(data, tuple) or len(data) != 2:
        return False

    d, tuple_of_tuples = data

    if not isinstance(d, dict) or not d or any(not v for v in d.values()):
        return False

    if not isinstance(tuple_of_tuples, tuple) or not tuple_of_tuples:
        return False

    for item in tuple_of_tuples:
        if not isinstance(item, tuple) or len(item) != 2:
            return False

        key, lst = item

        if not isinstance(key, str) or not key:
            return False
        if not isinstance(lst, list):
            return False

        if lst and any(not elem for elem in lst):
            return False

    return True

def ComboScope(message: str, threshold=80):
    BaseWords = ["combo", "combos"]
    RequestWords = ["want", "show", "give", "list", "suggest", "what", "best", "help", "please", "pls", "say"]
    SuggestionWords = ["suggest", "try", "recommend", "add", "share", "check", "here's", "heres", "my", "this", "got", "found", "made"]

    def fuzzy_contains(text: str, keyword: str) -> bool:
        k = len(keyword)
        for i in range(len(text) - k + 1):
            substring = text[i:i+k]
            if ratio(substring, keyword) >= threshold:
                return True
        return False

    msg = message.lower()

    has_combo = any(fuzzy_contains(msg, kw) for kw in BaseWords)
    if not has_combo:
        return None

    if any(fuzzy_contains(msg, word) for word in RequestWords):
        return "Asking"
    elif any(fuzzy_contains(msg, word) for word in SuggestionWords):
        return "Suggesting"
    else:
        return None

def RegisterCombo(user_id: str = "", parsed_build: dict = None, combo_data: tuple = None):
    csv_path = "storage/common/Comboes/Comboes.csv"
    parsed_build = parsed_build or {}
    combo_data_str = str(combo_data) if combo_data is not None else ""

    base_columns = ["id", "user_id", "combo_data"]
    parsed_columns = list(parsed_build.keys())
    all_columns = base_columns + parsed_columns

    if os.path.exists(csv_path):
        existing_df = pl.read_csv(csv_path)
        if "id" in existing_df.columns:
            existing_ids = existing_df["id"].to_list()
            existing_ids_int = [int(x) for x in existing_ids if str(x).isdigit()]
            next_id = max(existing_ids_int, default=0) + 1
        else:
            next_id = 1
    else:
        existing_df = None
        next_id = 1

    id_str = f"{next_id:07d}"

    row_data = {
        "id": id_str,
        "user_id": user_id,
        "combo_data": combo_data_str,
        **parsed_build,
    }

    if existing_df is not None:
        final_columns = set(existing_df.columns).union(all_columns)
        sorted_columns = existing_df.columns + sorted(final_columns - set(existing_df.columns))
    else:
        sorted_columns = all_columns

    row_complete = {col: row_data.get(col, "") for col in sorted_columns}
    new_row_df = pl.DataFrame([row_complete])

    if existing_df is None:
        new_row_df.write_csv(csv_path)
        return

    for col in sorted_columns:
        if col not in existing_df.columns:
            existing_df = existing_df.with_columns(pl.lit("").alias(col))

    for col in sorted_columns:
        if col in existing_df.columns:
            try:
                existing_dtype = existing_df.schema[col]
                new_row_df = new_row_df.with_columns(
                    new_row_df[col].cast(existing_dtype)
                )
            except Exception as e:
                print(f"Warning: Could not cast column '{col}' to {existing_dtype}. Error: {e}")
        else:
            new_row_df = new_row_df.with_columns(pl.col(col).cast(pl.Utf8))

    for col in sorted_columns:
        if col not in new_row_df.columns:
            new_row_df = new_row_df.with_columns(pl.lit("").alias(col))

    existing_df = existing_df.select(sorted_columns)
    new_row_df = new_row_df.select(sorted_columns)
    updated_df = pl.concat([existing_df, new_row_df], how="vertical")
    updated_df.write_csv(csv_path)

    return int(id_str)

def ComboLookup(message: str = ""):
    parser_build, _ = ComboPatternParser(message)
    df = pl.read_csv("storage/common/Comboes/Comboes.csv")

    def normalize(s):
        return str(s).strip().lower()

    parser_items = {normalize(k): normalize(v) for k, v in parser_build.items()}

    matchable_keys = ['Fighting Style', 'Fruit', 'Sword', 'Gun']
    normalized_match_keys = [normalize(k) for k in matchable_keys]

    valid_parser_items = {
        k: v for k, v in parser_items.items() if k in normalized_match_keys
    }

    if not valid_parser_items:
        return None

    key_map = {normalize(k): k for k in matchable_keys}

    mask = pl.Series([True] * df.height)

    for norm_key, value in valid_parser_items.items():
        col = key_map[norm_key]
        mask &= (df[col].str.to_lowercase().str.strip_chars() == value)

    matched_rows = df.filter(mask)

    if matched_rows.height > 0:
        return matched_rows.sample(n=1).to_dicts()[0]

    return None

def ComboLookupByID(combo_id):
    if combo_id is None:
        return None

    df = pl.read_csv("storage/common/Comboes/Comboes.csv")
    matched_rows = df.filter(pl.col("id") == combo_id)

    if matched_rows.height > 0:
        return matched_rows.to_dicts()[0]
    else:
        return None
    
def DeleteComboByID(combo_id):
    csv_path = "storage/common/Comboes/Comboes.csv"
    df = pl.read_csv(csv_path)
    df_filtered = df.filter(pl.col("id") != combo_id)
    df_filtered.write_csv(csv_path)