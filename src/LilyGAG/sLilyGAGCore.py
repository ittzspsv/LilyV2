import json
import os
import re
from rapidfuzz import process, fuzz
import discord
from discord.ext import commands
try:
    import Config.sBotDetails as Config
except:
    pass
import requests

Data = {}

def DataProcessor(filename, expected_type):
    if not os.path.exists(filename):
        return [] if expected_type == list else {}

    with open(filename, "r") as f:
        content = f.read().strip()
        if not content:
            return [] if expected_type == list else {}
        try:
            data = json.loads(content)
            if isinstance(data, expected_type):
                return data
            else:
                return [] if expected_type == list else {}
        except json.JSONDecodeError:
            return [] if expected_type == list else {}

def UpdateData():
    global Data
    Data["MutationData"] = DataProcessor("src/LilyGAG/data/GAGMutationData.json", dict)
    Data["PetValueData"] = DataProcessor("src/LilyGAG/data/GAGPetValueData.json", dict)
    Data["PlantsData"] = DataProcessor("src/LilyGAG/data/GAGPlantsData.json", list)
    Data["FruitType"] = DataProcessor("src/LilyGAG/data/GAGFruitTypeData.json", dict)

UpdateData()

def price_formatter(value):
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.1f}T"
        elif value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}k"
        else:
            return str(int(value)) 

def GAGMessageParser(sentence, threshold=75):
    parser = sentence.split()
    plant_names = [item["name"] for item in Data["PlantsData"]]
    best_match = process.extractOne(sentence, plant_names, scorer=fuzz.partial_ratio)

    fruit_name = best_match[0] if best_match and best_match[1] >= threshold else None
    fruit_data = next((item for item in Data["PlantsData"] if item["name"] == fruit_name), None)

    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', sentence, re.IGNORECASE)

    if weight_match:
        weight = float(weight_match.group(1))
    elif fruit_data is not None:
        weight = fruit_data.get("weightDivisor", None)
    else:
        weight = None

    quantity = 1
    for word in parser:
        try:
            quantity = int(word)
            break
        except ValueError:
            quantity = 1

    mutations_found = []
    for mutation in Data["MutationData"].keys():
        match_score = fuzz.partial_ratio(mutation.lower(), sentence.lower())
        if match_score >= threshold:
            mutations_found.append(mutation)

    fruit_type = ""
    for fruittype in Data["FruitType"].keys():
        match_score = fuzz.partial_ratio(fruittype.lower(), sentence.lower())
        if match_score >= threshold:
            fruit_type = fruittype
            break

    return (fruit_name, weight, tuple(mutations_found), fruit_type, quantity), best_match

def GAGPetMessageParser(sentence, threshold=75):
    parser = sentence.split()
    pets = list(Data["PetValueData"].keys())
    pet_name = process.extractOne(sentence, pets, scorer=fuzz.partial_ratio)

    pet_age = 0
    age_keywords = ["yr", "yrs", "year", "years"]

    for i, word in enumerate(parser):
        for keyword in age_keywords:
            if word.lower().endswith(keyword):
                try:
                    pet_age = int(re.sub(r"[a-zA-Z]", "", word))
                    break
                except ValueError:
                    pet_age = 1
                    break
        if pet_age:
            break
        if word.isdigit() and i + 1 < len(parser) and parser[i + 1].lower() in age_keywords:
            pet_age = int(word)
            break

    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', sentence, re.IGNORECASE)
    if weight_match:
        pet_weight = float(weight_match.group(1))
    else:
        pet_weight = 1

    return {
        "name": pet_name[0] if pet_name and pet_name[1] >= threshold else None,
        "age": pet_age,
        "weight": pet_weight
    }, pet_name

def ParserType(sentence):
    seed_Data, fuzzresultant = GAGMessageParser(sentence)
    pet_Data, secondary_fuzzresultant = GAGPetMessageParser(sentence)

    if seed_Data[0] != None and (fuzzresultant[1] > secondary_fuzzresultant[1]):
        return "SeedType", seed_Data
    elif pet_Data['name'] != None and ((fuzzresultant[1] < secondary_fuzzresultant[1])):
        return "PetType", pet_Data
    else:
        return "None", {}

        
def GAGValue(fruit_data):
    url = "https://api.joshlei.com/v2/growagarden/calculate"
    name, weight, mutations, variant, quantity = fruit_data
    params = {
        "Name": str(name),
        "Weight": str(weight),
        "Variant": str(variant),
        "Mutation": ",".join(mutations) if mutations else "",
    }

    response = requests.get(url, params=params)
    if response.ok:
        response_data = response.json()
        return response_data, quantity
    
def GAGPetValue(pet_data):
    try:
        pet_value = Data["PetValueData"][pet_data['name']]
        pet_value = pet_value[0].replace(",", "")
        return int(pet_value)
    except Exception as e:
        print(e)
        return 0

def WORL(message:str=None):
    splitter = message.split("for")
    your_side = splitter[0]
    their_side = splitter[1]

    your_side_split = your_side.split(",")
    their_side_split = their_side.split(",")

    your_side_items = []
    their_side_items = []
    your_side_values = []
    their_side_values = []

    for split in your_side_split:
        type, data = ParserType(split)
        if type == "SeedType":
            Tuple  = data
            valuedata, quantity = GAGValue(Tuple)
            your_side_items.append(valuedata['Name'])
            your_side_values.append(int(valuedata['value']) * quantity)
        if type == "PetType":
            value = GAGPetValue(data)
            your_side_items.append(data['name'])
            your_side_values.append(value)

    for split in their_side_split:
        type, data = ParserType(split)
        if type == "SeedType":
            Tuple  = data
            valuedata, quantity = GAGValue(Tuple)
            their_side_items.append(valuedata['Name'])
            their_side_values.append(int(valuedata['value']) * quantity)
        if type == "PetType":
            value = GAGPetValue(data)
            their_side_items.append(data['name'])
            their_side_values.append(value)

    total_yours = sum(your_side_values)
    total_theirs = sum(their_side_values)

    if total_yours >= total_theirs:
        loss_percentage = ((total_yours - total_theirs) / total_yours) * 100 if total_yours != 0 else 0.0
        return {"outcome": "Loss", "percentage": round(loss_percentage, 2)}, your_side_items, your_side_values, their_side_items, their_side_values
    elif total_yours < total_theirs:
        win_percentage = ((total_theirs - total_yours) / total_theirs) * 100 if total_theirs != 0 else 0.0
        return {"outcome": "Win", "percentage": round(win_percentage, 2)}, your_side_items, your_side_values, their_side_items, their_side_values
    else:
        return {"outcome": "Fair", "percentage": 0.0}, your_side_items, your_side_values, their_side_items, their_side_values


async def MessageEvaluate(self, bot, message):
    #Seeds, Pets, Value
    if message.channel.id == int(Config.gag_value_calculator_channel_id):
        try:
            data, quantity = GAGValue(GAGMessageParser(message.content.lower()))
            embed = discord.Embed(title=f"VALUE :  {price_formatter(int(data['value']) * quantity)}",
                        colour=0x1000f5)

            embed.set_author(name="BloxTrade | Grow a Garden Calculator")

            embed.add_field(name="Name",
                            value=data['Name'],
                            inline=False)
            embed.add_field(name="Weight",
                            value=f"{data['Weight']}kg",
                            inline=False)
            embed.add_field(name="Variant",
                            value=data["Variant"],
                            inline=False)
            embed.add_field(name="Mutation",
                            value=data['Mutation'],
                            inline=False)

            await message.reply(embed=embed)
        except:
            await message.delete()
    elif message.channel.id == int(Config.gag_worl_channel_id):
        try:
            outcome_data, your_side_items, your_side_values, their_side_items, their_side_values = WORL(message.content.lower())
            your_side_items_string = ""
            their_side_item_string = ""

            for items, values in zip(your_side_items, your_side_values):
                your_side_items_string += f"- {items} : {price_formatter(values)}\n"
            for items, values in zip(their_side_items, their_side_values):
                their_side_item_string += f"- {items} : {price_formatter(int(values))}\n"
            outcome_caliber = ""
            if outcome_data['outcome'] == 'Loss':
                outcome_caliber = f"Its an Loss you lose {outcome_data['percentage']}"
            elif outcome_data['outcome'] == 'Fair':
                outcome_caliber = f"Its an Fair offer"
            else:
                outcome_caliber = f"Its a Win.  You gain {outcome_data['percentage']}%"

            embed = discord.Embed(title=outcome_caliber,
                        colour=0x5600f5)

            embed.set_author(name="BloxTrade | Grow a garden values")

            embed.add_field(name="Your Items",
                            value=your_side_items_string,
                            inline=False)
            embed.add_field(name="Their Items",
                            value=their_side_item_string,
                            inline=False)
            await message.reply(embed=embed)
        except:
            await message.delete()
        
