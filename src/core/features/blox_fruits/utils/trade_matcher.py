from rapidfuzz import process, fuzz

def predict_trade_message(text, phrases, threshold=70):
    corrected_text = text
    for phrase in phrases:
        best_match = process.extractOne(text, [phrase], scorer=fuzz.ratio)
        if best_match:
            match_word, score, _ = best_match
            if score >= threshold:
                corrected_text = corrected_text.replace(match_word, "").strip()
    return corrected_text

def is_permanent_match(item, threshold=70):
    perm_words = {"perm", "permanent"}

    result = process.extractOne(item, perm_words, scorer=fuzz.ratio)

    if result is None:
        return False

    _, score, _ = result
    return score >= threshold

def permanent_match(item, threshold=70):
    perm_words = {"perm", "permanent"}

    result = process.extractOne(item, perm_words, scorer=fuzz.ratio)

    if result is None:
        return None

    _, score, _ = result

    if score >= threshold:
        return "permanent"

    return None


def match_fruit(fruits, data, threshold=80):
    result = process.extractOne(fruits, data.keys(), scorer=fuzz.ratio)

    if result is None:
        return None

    best_match, score, _ = result

    if score >= threshold:
        return best_match, data[best_match]

    return None

def match_fruit_set(fruit: str, fruit_names: set, alias_map: dict, threshold=80):
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