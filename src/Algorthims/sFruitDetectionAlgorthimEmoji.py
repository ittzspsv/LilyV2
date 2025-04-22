import re
import json
import Config.sBotDetails as BD



if BD.port == 0:
    emoji_data_path = "src/EmojiData.json"
    with open(emoji_data_path, "r", encoding="utf-8") as json_file:
        emoji_data = json.load(json_file)
else:
    emoji_data_path = "src/bEmojiData.json"
    with open(emoji_data_path, "r", encoding="utf-8") as json_file:
        emoji_data = json.load(json_file)

emoji_id_to_name = {}
for fruit_name, emoji_value in emoji_data.items():
    for emoji_values in emoji_value:
        match = re.search(r"<:(\w+):(\d+)>", emoji_values)
        if match:
            emoji_id_to_name[match.group(2)] = fruit_name.title()


def extract_fruit_trade(emoji_string, emoji_id_to_name):
    emojis = re.findall(r"<:(\w+):(\d+)>", emoji_string)

    if not any(emoji_id in BD.TRADE_EMOJI_ID for _, emoji_id in emojis):
        return [], [], [], []

    your_fruits, your_fruit_types = [], []
    their_fruits, their_fruit_types = [], []

    trade_index = next((i for i, (garbage, emoji_id) in enumerate(emojis) if emoji_id in BD.TRADE_EMOJI_ID), None)
    
    if trade_index is None:
        return [], [], [], []

    i = 0
    while i < trade_index:
        if any(emojis[i][1] == perm_emoji_id for perm_emoji_id in BD.PERM_EMOJI_ID): 
            if i + 1 < trade_index and emojis[i + 1][1] in emoji_id_to_name:
                your_fruits.append(emoji_id_to_name[emojis[i + 1][1]])
                your_fruit_types.append("permanent")
                i += 2 
                continue
        elif emojis[i][1] in emoji_id_to_name:
            your_fruits.append(emoji_id_to_name[emojis[i][1]])
            your_fruit_types.append("physical")
        i += 1

    i = trade_index + 1
    while i < len(emojis):
        if any(emojis[i][1] == perm_emoji_id for perm_emoji_id in BD.PERM_EMOJI_ID):
            if i + 1 < len(emojis) and emojis[i + 1][1] in emoji_id_to_name:
                their_fruits.append(emoji_id_to_name[emojis[i + 1][1]])
                their_fruit_types.append("permanent")
                i += 2
                continue
        elif emojis[i][1] in emoji_id_to_name:
            their_fruits.append(emoji_id_to_name[emojis[i][1]])
            their_fruit_types.append("physical")
        i += 1

    return your_fruits, your_fruit_types, their_fruits, their_fruit_types

def is_valid_trade_sequence(emoji_string, emoji_id_to_name):
    if not any(trade_emoji in emoji_string for trade_emoji in BD.TRADE_EMOJI_ID):
        return False

    emojis = re.findall(r"<:(\w+):(\d+)>", emoji_string)

    trade_index = next(
        (i for i, (garbage, emoji_id) in enumerate(emojis) if emoji_id in BD.TRADE_EMOJI_ID), 
        None
    )

    if trade_index is None or trade_index == 0 or trade_index == len(emojis) - 1:
        return False

    valid_fruits_before_trade = any(
        emoji_id in emoji_id_to_name and emoji_id not in BD.PERM_EMOJI_ID 
        for garbage, emoji_id in emojis[:trade_index]
    )

    valid_fruits_after_trade = any(
        emoji_id in emoji_id_to_name and emoji_id not in BD.PERM_EMOJI_ID
        for garbage, emoji_id in emojis[trade_index + 1:]
    )

    return valid_fruits_before_trade and valid_fruits_after_trade

def is_valid_trade_suggestor_sequence(emoji_string):
    if not any(trade_emoji in emoji_string for trade_emoji in BD.TRADE_EMOJI_ID):
        return False
    
    emojis = re.findall(r"<:(\w+):(\d+)>", emoji_string)

    trade_index = next(
        (i for i, (garbage, emoji_id) in enumerate(emojis) if emoji_id in BD.TRADE_EMOJI_ID), 
        None
    )

    if trade_index is None:
        return False

    trade_emoji_str = f"<:{emojis[trade_index][0]}:{emojis[trade_index][1]}>"
    trade_emoji_pos = emoji_string.find(trade_emoji_str)

    after_trade_emoji = emoji_string[trade_emoji_pos + len(trade_emoji_str):].strip()
    return after_trade_emoji.startswith("❓")