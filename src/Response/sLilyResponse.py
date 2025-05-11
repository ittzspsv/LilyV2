import re
import random
import json
from rapidfuzz import fuzz
from functools import lru_cache
import requests


response_data = []

def load_json(file):
    with open(file, encoding="utf-8") as bot_responses:
        print(f"Loaded '{file}' successfully!")
        return json.load(bot_responses)


def RegexCompile(p):
    if isinstance(p, str) and p.startswith("re:"):
        pattern = p[3:]
        try:
            return re.compile(pattern)
        except re.error as e:
            print(f"Regex error: {e} in pattern: {pattern}")
            return None
    return p

def update_response(url):
    global response_data
    try:
        response = requests.get(url)
        response.raise_for_status()
        raw_data = response.json()
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"JSON Decode error: {e}")
        return False
    if isinstance(raw_data, dict) and "prompt" in raw_data:
        raw_data["prompt"] = [RegexCompile(pattern) for pattern in raw_data["prompt"]]
    with open("src/Response/LilyResponse.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=4)
    response_data = load_json("src/Response/LilyResponse.json")

    return True



update_response("https://pastebin.com/raw/2j6Wcirx")    

def FuzzyMatch(target_word, words_set, threshold=70):
    for word in words_set:
        if fuzz.ratio(target_word, word) >= threshold:
            return True
    return False


@lru_cache(maxsize=1000)
def get_response(input_string):
    input_string = input_string.strip()
    if not input_string:
        return "", 0, "", ""

    words = set(re.split(r'\s+|[,;?!.-]\s*', input_string.lower()))
    best_match = None
    best_score = 0

    for response in response_data:
        required = response.get("required_words", [])
        neglect = response.get("neglect_words", [])
        compiled_prompts = response.get("prompt", [])

        if any(FuzzyMatch(neg, words) for neg in neglect):
            continue
        if required and not all(FuzzyMatch(req, words) for req in required):
            continue

        score = 0
        for pattern in compiled_prompts:
            if isinstance(pattern, str):
                if pattern in words:
                    score += 1
            elif pattern:
                matched = any(pattern.fullmatch(word) for word in words)
                if not matched:
                    matched = any(FuzzyMatch(pattern.pattern, word) for word in words)
                if matched:
                    score += 1

        if score > best_score:
            best_match = response
            best_score = score

    if best_match:
        return random.choice(best_match["response"]), best_match["channel_to_respond"], best_match['delete_message'], best_match['emoji_to_react']

    return "", 0, "", ""