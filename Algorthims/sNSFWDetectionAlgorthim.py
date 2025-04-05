import json
import unicodedata
import re
from rapidfuzz import process

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



def load_nsfw_words(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        nsfw_words = json.load(file)
    return set(nsfw_words)

def is_nsfw(text, nsfw_set, threshold=96):
    words = re.findall(r"\b\w+\b", text.lower())
    words = [normalize_text(sword) for sword in words]
    
    return any(process.extractOne(word, nsfw_set)[1] >= threshold for word in words)


nsfw_set = load_nsfw_words("nsfw.json")