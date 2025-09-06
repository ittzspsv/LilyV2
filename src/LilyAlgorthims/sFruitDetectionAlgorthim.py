import re
import word2number.w2n
import Config.sValueConfig as VC
import LilyAlgorthims.sTradeFormatAlgorthim as TFA

async def extract_trade_details(message):
    fruit_names, alias_map = await TFA.get_all_fruit_names()
    fruit_names_sorted = sorted([name.lower() for name in fruit_names], key=len, reverse=True)
    fruit_set = set(fruit_names_sorted)

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
        while i < len(message_split):
            matched_fruit = None
            matched_length = 0

            for fruit in fruit_names_sorted:
                matched_fruit = await TFA.MatchFruitSet(
                    ' '.join(message_split[i:i + len(fruit.split())]),
                    fruit_set,
                    alias_map
                )
                if matched_fruit:
                    matched_length = len(matched_fruit.split())
                    break

            if matched_fruit:
                counter = 1
                if i > 0 and message_split[i - 1].isdigit():
                    counter = min(int(message_split[i - 1]), 10)

                fruit_type = "Permanent" if (i > 0 and TFA.isPermanentMatch(message_parsed[i - 1])) else "Physical"

                for _ in range(counter):
                    fruit_list.append(matched_fruit)
                    fruit_types.append(fruit_type)

                i += matched_length - 1

            i += 1

        return fruit_list, fruit_types

    your_fruits, your_fruit_type = await extract_fruits(your_message_split)
    their_fruits, their_fruit_types = await extract_fruits(their_message_split)

    your_fruits = [fruit.title() for fruit in your_fruits]
    their_fruits = [fruit.title() for fruit in their_fruits]

    return your_fruits, your_fruit_type, their_fruits, their_fruit_types
