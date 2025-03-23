import re
import unicodedata
from rapidfuzz import fuzz
import sTradeFormatAlgorthim as TFA

strong_scam_words = {
    "hosting", "fully bribed", "private server", "briber", "shipwright",
    "d_m", "dragon user", "beast hunter", "ps", "have boat"
}

weak_scam_words = {"levi", "leviathan", "tiki", "hydra", "heart", "hunt"}

free_stuff_words = {
    "first", "1st", "one", "quickly", "fast", "hurry", "dm", "reply",
    "permanent", "perm", "fruit", "reward", "prize", "limited", "get", "win", "giveaway", "free"
}

leet_dict = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't'
}

def normalize_text(text):
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text.lower().strip()

def leetspeak_to_text(text):
    for k, v in leet_dict.items():
        text = text.replace(k, v)
    return text

def detect_beamer_message(message, mode="sea_event"):
    normalized_message = normalize_text(message)
    converted_message = leetspeak_to_text(normalized_message)

    looking_for_match = re.match(r"^\s*(looking\s*for|lf)\b", converted_message, re.IGNORECASE)
    
    score = 0

    if mode == "sea_event":
        for word in strong_scam_words:
            if fuzz.partial_ratio(converted_message, word) >= 90:
                score += 3

        for word in weak_scam_words:
            if fuzz.partial_ratio(converted_message, word) >= 90:
                score += 1 

        threshold = 6 if looking_for_match else 3
        return score >= threshold

    elif mode == "free_Stuffs":
        giveaway_pattern = re.compile(
            r"(first|1st|one)\s*\d*\s*(?:people|users|persons|to|who)\s*(?:dm|message|reply|contact|ping|pm)",
            re.IGNORECASE
        )
        if giveaway_pattern.search(converted_message):
            return True

        for word in free_stuff_words:
            if fuzz.partial_ratio(converted_message, word) >= 90:
                score += 2

        return score >= 4

    return False
