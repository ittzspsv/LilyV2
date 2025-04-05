import unicodedata
from rapidfuzz import fuzz
import Algorthims.sTradeFormatAlgorthim as TFA
import re

HIGH_RISK_WORDS = {
    "account", "robux", "id", "@cc", "bladeball", "cross-trade", "bucks", "ps",
    "gamepass", "mm2", "acc", "akkount"
}

SCAM_WORDS = {
    "hosting", "fully bribed", "private server", "briber", "shipwright", "d_m",
    "beast hunter", "have boat", "levi", "leviathan", "tiki", "hydra", "heart", "hunt"
}

FREE_STUFF_WORDS = {
    "first", "1st", "one", "quickly", "fast", "hurry", "dm", "reply", "permanent",
    "perm", "fruit", "reward", "prize", "limited", "get", "win", "giveaway", "free",
}

SUSPICIOUS_SYMBOLS = {'@', '€', '$', '%', '&', '!', '¥', '¢', '¤'}

leet_dict = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't',
    '@': 'a', '€': 'e', '$': 's', '!': 'i', '£': 'l', '8': 'b'
}

homoglyph_map = {
    '𝐀': 'A', '𝖆': 'a', '𝐵': 'B', '𝑏': 'b', '𝒞': 'C', '𝒸': 'c',
    '𝒟': 'D', '𝒹': 'd', '𝐸': 'E', '𝑒': 'e', '𝑭': 'F', '𝑓': 'f',
    '𝑮': 'G', '𝑔': 'g', '𝑯': 'H', '𝒽': 'h', '𝐼': 'I', '𝑖': 'i',
    '𝒥': 'J', '𝒿': 'j', '𝐾': 'K', '𝑘': 'k', '𝒧': 'L', '𝓁': 'l',
    '𝑀': 'M', '𝑚': 'm', '𝒩': 'N', '𝓃': 'n', '𝑶': 'O', '𝑜': 'o',
    '𝒫': 'P', '𝓅': 'p', '𝒬': 'Q', '𝓆': 'q', '𝑅': 'R', '𝓇': 'r',
    '𝒮': 'S', '𝓈': 's', '𝑇': 'T', '𝓉': 't', '𝑼': 'U', '𝓊': 'u',
    '𝒱': 'V', '𝓋': 'v', '𝑾': 'W', '𝓌': 'w', '𝒳': 'X', '𝓍': 'x',
    '𝒴': 'Y', '𝓎': 'y', '𝒵': 'Z', '𝓏': 'z'
}
ZERO_WIDTH_CHARS = re.compile(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]')

IGNORE_WORDS = {"moderation", "testing", "idle", "online", "pings", "moderators", "ping"}


def regional_indicator_to_text(text):
    styled_letters = {
        "🅰️": "A", "🅱️": "B", "🆎": "AB", "🆑": "CL", "🆒": "COOL",
        "🆓": "FREE", "🆔": "ID", "🆕": "NEW", "🆖": "NG", "🆗": "OK",
        "🆘": "SOS", "🆙": "UP", "🆚": "VS", "Ⓜ️": "M", "🅾️": "O"
    }
    
    def convert_match(match):
        char = match.group(0)
        char = char.replace("️", "") 
        if char in styled_letters:
            return styled_letters[char]
        if '\U0001F1E6' <= char <= '\U0001F1FF':
            unicode_val = ord(char) - 0x1F1E6
            return chr(unicode_val + ord('A'))
        if '\u24B6' <= char <= '\u24CF':
            return chr(ord(char) - 0x24B6 + ord('A'))
        return char
    
    text = text.replace("️", "")
    converted_text = re.sub(r'[\U0001F1E6-\U0001F1FFⒶ-Ⓩ\U0001F170-\U0001F189]', convert_match, text)
    return converted_text.replace(" ", "")

def normalize_text(text):
    text = ZERO_WIDTH_CHARS.sub('', text)
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(homoglyph_map.get(char, char) for char in text)
    text = ''.join(leet_dict.get(char, char) for char in text)
    text = re.sub(r'[^a-zA-Z0-9\s/()]+', '', text)
    text = re.sub(r'(?<=\b[a-zA-Z]) (?=[a-zA-Z]\b)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lower()
    return text


debug_String = ""


def detect_beamer_message(message):
    global debug_String
    if TFA.is_valid_trade_format(message, TFA.fruit_names):
        return False, 0  

    normalized_message = normalize_text(message)
    words = []
    for i in normalized_message.split():
        if len(i) > 2:
            words.append(i)

    score = 0
    word_count = {"high_risk": 0, "scam": 0, "free_stuff": 0}

    def match_words(word_list, category, base_score, similarity_threshold):
        nonlocal score
        for word in word_list:
            for w in words:
                if w in IGNORE_WORDS:
                    continue
                similarity = fuzz.partial_ratio(w, word)
                if similarity == 100:
                    score += base_score
                    word_count[category] += 1
                elif similarity >= similarity_threshold:
                    score += base_score - 1
                    word_count[category] += 1

    match_words(HIGH_RISK_WORDS, "high_risk", 8, 87)
    match_words(SCAM_WORDS, "scam", 5, 85)
    match_words(FREE_STUFF_WORDS, "free_stuff", 3, 80)

    if any(c in SUSPICIOUS_SYMBOLS for c in message):
        score += 10

    if word_count["high_risk"] >= 2:
        score += 10

    if word_count["high_risk"] >= 1 and word_count["scam"] >= 1:
        score += 7

    THRESHOLD = 15

    confirmation_probability = min(100, max(0, round((score / THRESHOLD) * 100 - 50)))

    result = score >= THRESHOLD

    return result


message = """
🇭​🇴​🇸​🇹​🇮​🇳​🇬​ ⠀ 🇱​🇪​🇻​🇮​🇦​🇹​🇭​🇦​🇳​ ⠀ 🇹​🇴​ ⠀ 🇭​🇾​🇩​🇷​🇦  
🄴🅇🄿🄴🅁🄸🄴🄽🄲🄴🄳⠀(𝕯𝖔𝖓𝖊⠀𝕷𝖊𝖛𝖎⠀𝕸𝖆𝖓𝖞⠀𝕿𝖎𝖒𝖊𝖘⠀𝕭𝖊𝖋𝖔𝖗𝖊).  
𝟛 / 𝟟 ⠀ 𝖀𝖘𝖊𝖗  
𝕬𝖑𝖗𝖊𝖆𝖉𝖞⠀𝖍𝖆𝖛𝖊⠀🄱𝖊𝖆𝖘𝖙⠀🄷𝖚𝖓𝖙𝖊𝖗⠀𝖜𝖎𝖙𝖍⠀🄱𝖗𝖎𝖇𝖊𝖗  
𝕎𝖊⠀𝖍𝖆𝖛𝖊⠀🄼𝖆𝖝⠀𝕊𝖍𝖎𝖕𝖜𝖗𝖎𝖌𝖍𝖙  
𝕭𝖚𝖙⠀𝖜𝖊⠀𝖓𝖊𝖊𝖉⠀𝖕𝖊𝖔𝖕𝖑𝖊  
𝕯𝖔𝖓'𝖙⠀𝕯𝖔⠀𝕬𝖓𝖞𝖙𝖍𝖎𝖓𝖌⠀🄱𝖆𝖉⠀𝖔𝖗⠀🄺𝖎𝖈𝖐  
𝟚⠀𝕯𝖗𝖆𝖌𝖔𝖓⠀𝖀𝖘𝖊𝖗  
𝕯_𝕸⠀𝖎𝖋⠀𝖞𝖔𝖚⠀𝖜𝖆𝖓𝖙⠀𝖍𝖆𝖛𝖊⠀🅿🅂  
"""