import re
import random
import json
from rapidfuzz import fuzz
from functools import lru_cache
import requests

import LilyAlgorthims.sNSFWDetectionAlgorthim as LNSFWDA


response_data = []
lily_response_rules = []
lilyconfig = {}

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
            return None
    return p

def update_response():
    global response_data, lilyconfig, lily_response_rules
    url = "https://ittzspsv.github.io/LilyV2-Configs/LilyResponse.json"
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
    with open("src/LilyResponse/LilyResponse.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=4)
    


    response_data = raw_data
    lily_response_rules = raw_data.get("response-rules", [])
    lilyconfig = raw_data.get("lily-response-config", {})

    if isinstance(lily_response_rules, list):
        for entry in lily_response_rules:
            if "prompt" in entry:
                entry["prompt"] = [RegexCompile(p) for p in entry["prompt"]]

    return True

def update_response_raw():
    global response_data, lilyconfig, lily_response_rules
    with open("src/LilyResponse/LilyResponse.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    


    response_data = raw_data
    lily_response_rules = raw_data.get("response-rules", [])
    lilyconfig = raw_data.get("lily-response-config", {})

    if isinstance(lily_response_rules, list):
        for entry in lily_response_rules:
            if "prompt" in entry:
                entry["prompt"] = [RegexCompile(p) for p in entry["prompt"]]

    return True

update_response()
#update_response_raw()

def FuzzyMatch(target_word, words_set, threshold=70):
    for word in words_set:
        score = fuzz.ratio(target_word, word)
        if score >= threshold:
            return True
    return False

def get_response(input_string):
    matched = re.match(r"<:(\w+):(\d+)>", input_string)
    if not matched:
        input_string = LNSFWDA.normalize_text(input_string)
        input_string = input_string.strip().lower()
    if not input_string:
        return "", 0, "", "", "", ""

    words = set(word for word in re.split(r'\s+|[,;?!.\-]\s*', input_string) if word)

    best_match = None
    best_score = 0

    for response in lily_response_rules:
        required = response.get("required_words", [])
        neglect = response.get("neglect_words", [])

        if any(FuzzyMatch(neg, words, lilyconfig['string_matching_influence']) for neg in neglect):
            continue

        if required and not all(FuzzyMatch(req, words, lilyconfig['string_matching_influence']) for req in required):
            continue

        compiled_prompts = response.get("prompt", [])

        direct_match = False
        for pattern in compiled_prompts:
            if not isinstance(pattern, str): 
                if pattern.search(input_string): 
                    direct_match = True
                    break

        if direct_match:
            score = 1000
        else:
            match_count = 0
            total_patterns = len(compiled_prompts)

            for pattern in compiled_prompts:
                if isinstance(pattern, str):
                    if FuzzyMatch(pattern, words, lilyconfig['string_matching_influence']):
                        match_count += 1
                else:
                    matched = any(FuzzyMatch(pattern.pattern, word, lilyconfig['string_matching_influence'])
                                  for word in words)
                    if matched:
                        match_count += 1

            if total_patterns > 0:
                if match_count < (total_patterns / 2.0):
                    continue
            score = match_count
        if score > best_score:
            best_match = response
            best_score = score

    if best_match:
        return (
            random.choice(best_match["response"]),
            best_match["channel_to_respond"],
            best_match["delete_message"],
            best_match["emoji_to_react"],
            best_match["media"],
            best_match["whitelist_roles"]
        )
    return "", 0, "", "", "", ""
