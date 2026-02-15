import re
import LilyBloxFruits.core.sTradeFormatAlgorthim as TFA

import LilyBloxFruits.sLilyBloxFruitsCache as BFC

from typing import Optional, Tuple, List

async def extract_fruits_emoji(message: str) -> Optional[Tuple[List, List, List, List]]:
    message = message.strip()

    fruit_names, alias_map = await TFA.get_all_fruit_names()
    fruit_names_sorted = BFC.fruit_names_sorted
    fruit_set = BFC.fruit_set

    trade_separators = ["pointtrade", "point_trade", "trade_pointer"]
    perm_keywords = ["perm", "permanent"]

    trade_parts = None
    for sep in trade_separators:
        if sep.lower() in message.lower():
            trade_parts = re.split(re.escape(sep), message, maxsplit=1)
            break

    if not trade_parts or len(trade_parts) != 2:
        return [], [], [], []

    left_side, right_side = trade_parts[0].strip(), trade_parts[1].strip()

    async def extract_valid_items_with_type(text: str):
        items = []
        types = []

        text_clean = re.sub(r"<a?:([\w\d_]+):\d+>", r" \1 ", text)
        words = re.split(r"[,\s]+", text_clean)

        i = 0
        max_words = max(len(fn.split()) for fn in fruit_names_sorted)
        is_perm = False

        while i < len(words):
            word = words[i].strip()
            if not word:
                i += 1
                continue

            if word.lower() in perm_keywords:
                is_perm = True
                i += 1
                continue

            matched_fruit = None
            matched_length = 0

            for window in range(1, max_words + 1):
                if i + window > len(words):
                    break

                candidate = ' '.join(words[i:i + window])
                matched = await TFA.MatchFruitSet(candidate.lower(), fruit_set, alias_map)

                if matched:
                    matched_fruit = matched.title()
                    matched_length = window
                    break

            if matched_fruit:
                fruit_type = "Permanent" if is_perm else "Physical"
                items.append(matched_fruit)
                types.append(fruit_type)
                is_perm = False
                i += matched_length
            else:
                i += 1

        return items, types

    your_fruits, your_fruit_types = await extract_valid_items_with_type(left_side)
    their_fruits, their_fruit_types = await extract_valid_items_with_type(right_side)

    return your_fruits, your_fruit_types, their_fruits, their_fruit_types