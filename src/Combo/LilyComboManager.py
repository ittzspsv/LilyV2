import json
import re
import string
import random
import discord
import Config.sValueConfig as VC


from rapidfuzz.fuzz import ratio
from rapidfuzz import fuzz, process
from difflib import SequenceMatcher
from typing import Tuple, Dict, List, Literal, Optional


ComboData = {}


def ratio(a, b) -> float:
    return SequenceMatcher(None, a, b).ratio() * 100


async def ComboPatternParser(message: str, threshold: int=95) -> Tuple[Dict, Tuple]:
    message = re.sub(f"[{re.escape(string.punctuation)}]", " ", message).lower()
    words = message.split()

    cursor = await VC.combo_db.execute("SELECT name, aliases, type FROM ItemData")
    rows = await cursor.fetchall()

    ComboData = {}
    known_phrases = []
    reverse_map = {}

    for name, aliases_json, item_type in rows:
        aliases = json.loads(aliases_json) if aliases_json else []

        if item_type not in ComboData:
            ComboData[item_type] = {}

        ComboData[item_type][name] = aliases
        known_phrases.append(name)

        for shorthand in aliases:
            for part in re.split(r',|\|', shorthand):
                clean_shorthand = re.sub(f"[{re.escape(string.punctuation)}]", "", part).lower().strip()
                if clean_shorthand:
                    reverse_map[clean_shorthand] = (item_type, name)

    known_phrases = sorted(known_phrases, key=lambda p: len(p.split()), reverse=True)
    all_items_set = set([p.lower() for p in known_phrases])
    max_words = max(len(p.split()) for p in known_phrases)

    result = []
    i = 0
    while i < len(words):
        matched_item = None
        matched_length = 0

        for window in range(max_words, 0, -1):
            if i + window > len(words):
                continue
            candidate = " ".join(words[i:i+window]).strip()

            if candidate in reverse_map:
                matched_item = reverse_map[candidate][1]
                matched_length = len(candidate.split())
                break

            if candidate in all_items_set:
                matched_item = candidate.title()
                matched_length = len(candidate.split())
                break

            filtered_candidates = [f.lower() for f in all_items_set.union(reverse_map.keys()) if f and f[0] == candidate[0]]
            if filtered_candidates:
                match = process.extractOne(candidate, filtered_candidates, scorer=fuzz.ratio)
                if match and match[1] >= threshold:
                    best_match = match[0]
                    matched_item = reverse_map.get(best_match, (None, best_match.title()))[1]
                    matched_length = len(best_match.split())
                    break

        if matched_item:
            result.append(matched_item)
            i += matched_length
        else:
            result.append(words[i].title())
            i += 1

    parsed_build = {}
    pretty_labels = {
        "FightingStyle": "Fighting Style",
        "Fruit": "Fruit",
        "Swords": "Sword",
        "Guns": "Gun",
        "MiscData": "MiscData"
    }
    found_categories = set()
    for item in result:
        key = item.lower()
        if key in reverse_map:
            category, display_name = reverse_map[key]
        else:
            display_name = item
            category = None
            for cat, items in ComboData.items():
                if item in items:
                    category = cat
                    break

        label = pretty_labels.get(category, category) if category else None
        if label and label not in parsed_build:
            parsed_build[label] = display_name
            found_categories.add(category)

    combo_data = []
    current_key = None
    current_values = []

    valid_keys = set([p.lower() for p in known_phrases])
    for word in result:
        key = word.lower()
        if key in valid_keys or key in reverse_map:
            if current_key is not None:
                combo_data.append((current_key, current_values))
            if key in reverse_map:
                current_key = reverse_map[key][1]
            else:
                current_key = word
            current_values = []
        elif current_key:
            if word.upper()[0] in ['Z', 'X', 'C', 'V', 'F', 'M1']:
                current_values.append(word.upper()[0])
            else:
                current_values.append(random.choice(['Z', 'X', 'C', 'V', 'F', 'M1']))

    if current_key is not None:
        combo_data.append((current_key, current_values))

    return parsed_build, tuple(combo_data)

async def ValidComboDataType(data: Tuple[Dict[str, str], Tuple[Tuple[str, List[str]], ...]]) -> bool:    
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

def ComboScope(message: str, threshold: int=80) -> Optional[Literal['Asking', 'Suggesting']]:
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

async def RegisterCombo(user_id: str = "", parsed_build: Optional[Dict[str, str]] = None, combo_data: Optional[Tuple[Dict[str, str], Tuple[Tuple[str, List[str]], ...]]] = None) -> Optional[int]:
    parsed_build = parsed_build or {}

    combo_data_str = str(combo_data) if combo_data else ""

    db_columns = {
        "fighting_style": None,
        "fruit": None,
        "sword": None,
        "gun": None
    }

    key_map = {
        "Fighting Style": "fighting_style",
        "Fruit": "fruit",
        "Sword": "sword",
        "Gun": "gun"
    }

    for key, value in parsed_build.items():
        if key in key_map:
            db_columns[key_map[key]] = value

    async with VC.combo_db.execute("INSERT INTO Combos (combo_author, fighting_style, fruit, sword, gun, combo_data) VALUES (?, ?, ?, ?, ?, ?)", (user_id,db_columns["fighting_style"],db_columns["fruit"],db_columns["sword"],db_columns["gun"],combo_data_str)) as cursor:
        await VC.combo_db.commit()
        return cursor.lastrowid

async def ComboLookup(message: str = "") -> Optional[Dict[str, str]]:
    parsed_build, _ = await ComboPatternParser(message)

    def normalize(s):
        return str(s).strip().lower()

    parser_items = {normalize(k): normalize(v) for k, v in parsed_build.items()}

    matchable_keys = ["Fighting Style", "Fruit", "Sword", "Gun"]
    normalized_match_keys = [normalize(k) for k in matchable_keys]

    valid_parser_items = {
        k: v for k, v in parser_items.items() if k in normalized_match_keys
    }

    if not valid_parser_items:
        return None

    key_map = {
        normalize("Fighting Style"): "fighting_style",
        normalize("Fruit"): "fruit",
        normalize("Sword"): "sword",
        normalize("Gun"): "gun",
    }

    where_clauses: List = []
    values: List = []

    for norm_key, value in valid_parser_items.items():
        column = key_map[norm_key]
        where_clauses.append(f"LOWER({column}) = ?")
        values.append(value)

    where_sql = " AND ".join(where_clauses)

    query = f"SELECT * FROM Combos WHERE {where_sql}"

    cursor = await VC.combo_db.execute(query, values)
    rows = await cursor.fetchall()

    if not rows:
        return None

    chosen_row = random.choice(rows)

    columns: List[str] = [col[0] for col in cursor.description]
    result: Dict[str, str] = {k: str(v) if v is not None else "" for k, v in zip(columns, chosen_row)}

    return result

async def ComboLookupByID(combo_id: Optional[int]):
    if combo_id is None:
        return None

    cursor = await VC.combo_db.execute(
        "SELECT * FROM Combos WHERE combo_id = ?",
        (combo_id,)
    )
    row = await cursor.fetchone()

    if not row:
        return None

    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))
    
async def DeleteComboByID(combo_id: int) -> Optional[int]:
    cursor = await VC.combo_db.execute(
        "DELETE FROM Combos WHERE combo_id = ?",
        (combo_id,)
    )
    await VC.combo_db.commit()

    return cursor.rowcount