import re
from word2number.w2n import word_to_num
from src.core.utils.lily_utility import proper_capatilize
from ....database.integrations.blox_fruits import BloxFruitsDatabase
from .trade_matcher import match_fruit_set, is_permanent_match

from typing import Tuple, List


def extract_trade_details(message: str, db: BloxFruitsDatabase) -> Tuple[List, List, List, List]:
    alias_map = db.alias_map
    fruit_names_sorted = db.fruit_names_sorted
    fruit_set = set(db.fruit_names_sorted)

    max_words = max(len(fn.split()) for fn in fruit_names_sorted)

    EMOJI_SEPARATORS = ["pointtrade", "point_trade", "trade_pointer"]
    PERM_KEYWORDS = {"perm", "permanent"}

    def try_emoji_split(raw: str):
        """Return (left, right) tokens if an emoji-style separator is found."""
        for sep in EMOJI_SEPARATORS:
            if sep.lower() in raw.lower():
                parts = re.split(re.escape(sep), raw, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()
        return None

    def normalize_emoji(text: str) -> str:
        """<a:Buddha:123>  →  Buddha   (no-op on plain text)"""
        return re.sub(r"<a?:([\w\d_]+):\d+>", r" \1 ", text)

    def tokenize_text(text: str) -> List[str]:
        """
        Full text pipeline:
          lowercase → strip punctuation → split → word_to_num
        """
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()
        for i, tok in enumerate(tokens):
            try:
                tokens[i] = str(word_to_num(tok))
            except ValueError:
                pass
        return tokens

    def tokenize_emoji(text: str) -> List[str]:
        """
        Emoji pipeline:
          expand emoji names → split on whitespace/commas
        """
        text = normalize_emoji(text)
        return [t for t in re.split(r"[,\s]+", text) if t]

    emoji_sides = try_emoji_split(message)

    if emoji_sides:
        left_raw, right_raw = emoji_sides
        your_tokens  = tokenize_emoji(left_raw)
        their_tokens = tokenize_emoji(right_raw)
        is_emoji_mode = True
    else:
        all_tokens = tokenize_text(message)
        if "for" not in all_tokens:
            return [], [], [], []
        split_idx     = all_tokens.index("for")
        your_tokens   = all_tokens[:split_idx]
        their_tokens  = all_tokens[split_idx + 1:]
        is_emoji_mode = False


    def extract_fruits(tokens: List[str]) -> Tuple[List[str], List[str]]:
        fruit_list  = []
        fruit_types = []
        i = 0

        while i < len(tokens):
            tok = tokens[i]

            if is_emoji_mode and tok.lower() in PERM_KEYWORDS:
                i += 1
                fruit_types.append("__PERM_FLAG__")
                continue

            matched_fruit  = None
            matched_length = 0

            for window in range(max_words, 0, -1):
                if i + window > len(tokens):
                    continue
                candidate = " ".join(tokens[i:i + window])
                matched = match_fruit_set(candidate.lower(), fruit_set, alias_map)
                if matched:
                    matched_fruit  = matched
                    matched_length = len(matched.split()) or window
                    break

            if matched_fruit:
                counter = 1
                if not is_emoji_mode and i > 0 and tokens[i - 1].isdigit():
                    counter = min(int(tokens[i - 1]), 10)

                if is_emoji_mode:
                    if fruit_types and fruit_types[-1] == "__PERM_FLAG__":
                        fruit_types.pop()
                        fruit_type = "Permanent"
                    else:
                        fruit_type = "Physical"
                else:
                    before = tokens[i - 1] if i > 0 else ""
                    after  = tokens[i + matched_length] if i + matched_length < len(tokens) else ""
                    fruit_type = "Permanent" if (is_permanent_match(before) or is_permanent_match(after)) else "Physical"

                for _ in range(counter):
                    fruit_list.append(matched_fruit)
                    fruit_types.append(fruit_type)

                i += matched_length
            else:
                i += 1

        fruit_types = [t for t in fruit_types if t != "__PERM_FLAG__"]

        return fruit_list, fruit_types

    your_fruits,  your_types  = extract_fruits(your_tokens)
    their_fruits, their_types = extract_fruits(their_tokens)

    your_fruits  = [proper_capatilize(f) for f in your_fruits]
    their_fruits = [proper_capatilize(f) for f in their_fruits]

    return your_fruits, your_types, their_fruits, their_types