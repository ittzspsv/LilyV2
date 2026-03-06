import re
import word2number.w2n
import LilyBloxFruits.core.sTradeFormatAlgorthim as TFA

import LilyBloxFruits.sLilyBloxFruitsCache as BFC

from typing import Optional, Tuple, List

async def extract_trade_details(message: str) -> Optional[Tuple[List, List, List, List]]:
    fruit_names, alias_map = await TFA.get_all_fruit_names()
    fruit_names_sorted = BFC.fruit_names_sorted
    fruit_set = BFC.fruit_set

    message = message.lower()
    message = re.sub(r'[^\w\s]', ' ', message)
    message_parsed = message.split()

    for i, word in enumerate(message_parsed):
        try:
            message_parsed[i] = str(word2number.w2n.word_to_num(word))
        except ValueError:
            continue

    trade_split_index = message_parsed.index("for") if "for" in message_parsed else -1
    your_message_split = message_parsed[:trade_split_index]
    their_message_split = message_parsed[trade_split_index + 1:]

    async def extract_fruits(message_split):
        fruit_list = []
        fruit_types = []

        i = 0
        max_words = 1
        for fn in fruit_names_sorted:
            wn = len(fn.split())
            if wn > max_words:
                max_words = wn

        while i < len(message_split):
            matched_fruit = None
            matched_length = 0

            for window in range(max_words, 0, -1):
                if i + window > len(message_split):
                    continue
                candidate = ' '.join(message_split[i:i + window])
                matched = await TFA.MatchFruitSet(candidate, fruit_set, alias_map)
                if matched:
                    matched_fruit = matched 
                    matched_length = len(matched.split()) 
                    if matched_length == 0:
                        matched_length = window
                    break

            if matched_fruit:
                counter = 1
                if i > 0 and message_split[i - 1].isdigit():
                    counter = min(int(message_split[i - 1]), 10)

                before_word = message_split[i - 1] if i > 0 else ""
                after_word = message_split[i + window] if i + window < len(message_split) else ""

                if TFA.isPermanentMatch(before_word) or TFA.isPermanentMatch(after_word):
                    fruit_type = "Permanent"
                else:
                    fruit_type = "Physical"

                for _ in range(counter):
                    fruit_list.append(matched_fruit)
                    fruit_types.append(fruit_type)

                i += window
            else:
                i += 1

        return fruit_list, fruit_types

    your_fruits, your_fruit_type = await extract_fruits(your_message_split)
    their_fruits, their_fruit_types = await extract_fruits(their_message_split)

    your_fruits = [fruit.title() for fruit in your_fruits]
    their_fruits = [fruit.title() for fruit in their_fruits]

    return your_fruits, your_fruit_type, their_fruits, their_fruit_types