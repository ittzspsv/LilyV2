import json
import re

def load_nsfw_words(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        nsfw_words = json.load(file)
    return set(nsfw_words)

def is_nsfw(text, nsfw_set):
    words = re.findall(r"\b\w+\b", text.lower())
    return any(word in nsfw_set for word in words)

nsfw_set = load_nsfw_words("nsfw.json")