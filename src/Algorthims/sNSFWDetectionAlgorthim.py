import json
import unicodedata
import re
from rapidfuzz import process

SUSPICIOUS_SYMBOLS = {'@', '€', '$', '%', '&', '!', '¥', '¢', '¤'}

leet_dict = {
    '0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'a', '5': 's',
    '6': 'g', '7': 't', '8': 'b', '9': 'g',
    '@': 'a', '€': 'e', '$': 's', '!': 'i', '|': 'l', '£': 'l',
    '+': 't', '(': 'c', '{': 'c', '[': 'c', ')': 'c', '}': 'c', ']': 'c',
    '¥': 'y', '¢': 'c', '¤': 'o', '^': 'v', '&': 'e', '*': 'x', 
}
homoglyph_map = {
    'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
    'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L',
    'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
    'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X',
    'Ｙ': 'Y', 'Ｚ': 'Z',
    'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
    'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j', 'ｋ': 'k', 'ｌ': 'l',
    'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r',
    'ｓ': 's', 'ｔ': 't', 'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x',
    'ｙ': 'y', 'ｚ': 'z',

    '𝐀': 'A', '𝖆': 'a', '𝐵': 'B', '𝑏': 'b', '𝒞': 'C', '𝒸': 'c',
    '𝒟': 'D', '𝒹': 'd', '𝐸': 'E', '𝑒': 'e', '𝑭': 'F', '𝑓': 'f',
    '𝑮': 'G', '𝑔': 'g', '𝑯': 'H', '𝒽': 'h', '𝐼': 'I', '𝑖': 'i',
    '𝒥': 'J', '𝒿': 'j', '𝐾': 'K', '𝑘': 'k', '𝒧': 'L', '𝓁': 'l',
    '𝑀': 'M', '𝑚': 'm', '𝒩': 'N', '𝓃': 'n', '𝑶': 'O', '𝑜': 'o',
    '𝒫': 'P', '𝓅': 'p', '𝒬': 'Q', '𝓆': 'q', '𝑅': 'R', '𝓇': 'r',
    '𝒮': 'S', '𝓈': 's', '𝑇': 'T', '𝓉': 't', '𝑼': 'U', '𝓊': 'u',
    '𝒱': 'V', '𝓋': 'v', '𝑾': 'W', '𝓌': 'w', '𝒳': 'X', '𝓍': 'x',
    '𝒴': 'Y', '𝓎': 'y', '𝒵': 'Z', '𝓏': 'z',

    'ʜ': 'h',
    'ɪ': 'i',
    'ᴛ': 't',
    'ᴍ': 'm',
    'ᴋ': 'k',
    'ɴ': 'n',
    'ʟ': 'l',
    'ʀ': 'r',
    'ʃ': 'sh',
    'ʒ': 'zh',
    'ʎ': 'y',
    'ʞ': 'k',
}

leet_multi_dict = {
    '|-|': 'h',
    '|\\|': 'n',
    '||': 'u',
    '|_': 'l',
    '(_)': 'o',
}
ZERO_WIDTH_CHARS = re.compile(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]')

def is_regional_indicator_text(text):
    text = text.replace("️", "")
    pattern = r'^(?:[\U0001F1E6-\U0001F1FF\u24B6-\u24CF\U0001F170-\U0001F189]|🅰️|🅱️|🆎|🆑|🆒|🆓|🆔|🆕|🆖|🆗|🆘|🆙|🆚|Ⓜ️|🅾️|\s)*$'
    return re.fullmatch(pattern, text) is not None

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
            return chr(ord(char) - 0x1F1E6 + ord('A'))
        if '\u24B6' <= char <= '\u24CF':
            return chr(ord(char) - 0x24B6 + ord('A'))
        return char
    pattern = r'[\U0001F1E6-\U0001F1FF\u24B6-\u24CF\U0001F170-\U0001F189]|🅰️|🅱️|🆎|🆑|🆒|🆓|🆔|🆕|🆖|🆗|🆘|🆙|🆚|Ⓜ️|🅾️'

    return re.sub(pattern, convert_match, text)

def decode_leet_multi(text):
    for token, char in leet_multi_dict.items():
        text = text.replace(token, char)
    return text

def remove_spaces_in_letter_groups(text):
    def repl(m):
        return m.group(0).replace(' ', '')
    return re.sub(r'(?:[a-zA-Z] )+[a-zA-Z]', repl, text)
def normalize_text(text):
    text = regional_indicator_to_text(text)
    text = ZERO_WIDTH_CHARS.sub('', text)
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(homoglyph_map.get(char, char) for char in text)
    text = decode_leet_multi(text)
    text = ''.join(leet_dict.get(char, char) for char in text)
    text = re.sub(r'[^a-zA-Z0-9\s/()]+', '', text)
    text = re.sub(r'(?<=\b[a-zA-Z]) (?=[a-zA-Z]\b)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lower()
    return text




def load_nsfw_words(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        nsfw_words = json.load(file)
    return set(nsfw_words)

def is_nsfw(text, nsfw_set, threshold=95):
    words = re.findall(r"\b\w+\b", text.lower())
    words = [normalize_text(sword) for sword in words]
    
    return any(process.extractOne(word, nsfw_set)[1] >= threshold for word in words)