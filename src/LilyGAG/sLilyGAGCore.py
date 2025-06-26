import json
import os
import re
from rapidfuzz import process, fuzz
import discord
from io import BytesIO
from itertools import combinations, chain
try:
    import Config.sBotDetails as Config
    import ui.sWinOrLossImageGenerator as LilyWORLGen
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

def value_parser(value_with_suffix):
    chars = list(value_with_suffix)
    num = float(''.join(chars[:-1]))
    suffix = chars[-1].lower()
    multiplier = 1

    for s in ('k','m','b','t'):
        if suffix == s:
            if s == 'k':
                multiplier = 10**3
            elif s == 'm':
                multiplier = 10**6
            elif s == 'b':
                multiplier = 10**9
            elif s == 't':
                multiplier = 10**12
            break

    return int(num * multiplier)

def GAGMessageParser(sentence, threshold=75):
    parser = sentence.split()

    sheckle_value = re.findall(r'\b(\d+(?:\.\d+)?[kKmMbBtT])\b', sentence)
    if sheckle_value:
        return ("Candy Blossom", "", tuple(), "", "", 1, value_parser(sheckle_value[0])), []

    plant_names = [item["name"] for item in Data["PlantsData"]]
    plant_name_map = {name.lower(): name for name in plant_names}
    plant_candidates = []

    for i in range(len(parser)):
        for j in range(i + 1, len(parser) + 1):
            phrase = ' '.join(parser[i:j]).lower()
            for plant_key in plant_name_map:
                score = fuzz.ratio(phrase, plant_key)
                if score >= threshold:
                    plant_candidates.append((plant_key, score))

    if plant_candidates:
        plant_candidates.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
        matched_key = plant_candidates[0][0]
        best_match = (plant_name_map[matched_key], plant_candidates[0][1])
    else:
        best_match = (None, 0)

    fruit_name = best_match[0]
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
            continue

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

    return (fruit_name, weight, tuple(mutations_found), fruit_type, quantity, 0, 0), best_match

def GAGPetMessageParser(sentence, threshold=75):
    parser = sentence.split()
    pets = list(Data["PetValueData"].keys())
    pet_name_map = {p.lower(): p for p in pets}
    pet_candidates = []

    for i in range(len(parser)):
        for j in range(i + 1, len(parser) + 1):
            phrase = ' '.join(parser[i:j]).lower()
            for pet_key in pet_name_map:
                score = fuzz.ratio(phrase, pet_key)
                if score >= threshold:
                    pet_candidates.append((pet_key, score))

    if pet_candidates:
        pet_candidates.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
        matched_pet_key = pet_candidates[0][0]
        pet_name = (pet_name_map[matched_pet_key], pet_candidates[0][1])
    else:
        pet_name = (None, 0)

    pet_age = 0
    age_keywords = ["yr", "yrs", "year", "years", "age"]
    for i, word in enumerate(parser):
        word_lower = word.lower()

        for keyword in age_keywords:
            if word_lower.endswith(keyword):
                try:
                    pet_age = int(re.sub(r"[a-zA-Z]", "", word))
                    break
                except ValueError:
                    pet_age = 1
                    break
        if pet_age:
            break

        if word_lower == "age" and i + 1 < len(parser):
            next_word = parser[i + 1]
            if next_word.isdigit():
                pet_age = int(next_word)
                break

        if word.isdigit() and i + 1 < len(parser):
            if parser[i + 1].lower() in age_keywords:
                pet_age = int(word)
                break

    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', sentence, re.IGNORECASE)
    pet_weight = float(weight_match.group(1)) if weight_match else 1

    return {
        "name": pet_name[0],
        "age": pet_age,
        "weight": pet_weight
    }, pet_name

def ParserType(sentence):
    seed_Data, fuzzresultant = GAGMessageParser(sentence)
    pet_Data, secondary_fuzzresultant = GAGPetMessageParser(sentence)

    if seed_Data[-2] == 1 and seed_Data[-1]:
        print(seed_Data[-1])
        return "SeedType", seed_Data
    elif seed_Data[0] != None and (fuzzresultant[1] > secondary_fuzzresultant[1]):
        return "SeedType", seed_Data
    elif pet_Data['name'] != None and ((fuzzresultant[1] < secondary_fuzzresultant[1])):
        return "PetType", pet_Data,
    else:
        return "None", {}
    
def GAGValue(fruit_data):
    url = "https://api.joshlei.com/v2/growagarden/calculate"
    name, weight, mutations, variant, quantity, shecklebool, sheckles = fruit_data
    if shecklebool == 1:
        return {'value' : int(sheckles), "Name": str(name),"Weight": str(weight),"Variant": str(variant),"Mutation": ",".join(mutations) if mutations else ""}, 1
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
    #-------------------MATH FUNCTION STARTS----------------------#
    def interpolate_nonlinear(value, in_min, in_max, out_min, out_max):
        return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)

    def age_factor(age):
        if age <= 39:
            return interpolate_nonlinear(age, 0, 39, 0.00001, 0.001)
        elif age <= 55:
            return interpolate_nonlinear(age, 45, 55, 0.05, 0.5)
        elif age <= 65:
            return interpolate_nonlinear(age, 56, 65, 0.6, 1.0)
        else:
            return 1.0

    def weight_factor(weight):
        if weight <= 9:
            return interpolate_nonlinear(weight, 0, 9, 0.00001, 0.001)
        elif weight <= 15:
            return interpolate_nonlinear(weight, 10, 15, 0.75, 0.8)
        elif weight <= 20:
            return interpolate_nonlinear(weight, 16, 20, 0.85, 0.95)
        elif weight <= 25:
            return interpolate_nonlinear(weight, 21, 25, 0.95, 1.0)
        else:
            return 1.0

    def compute_value(min_value, max_value, age, weight):
        a_factor = age_factor(age)
        w_factor = weight_factor(weight)

        combined_factor = (a_factor + w_factor) / 2
        value = interpolate_nonlinear(combined_factor, 0, 1, min_value, max_value)

        age_boost = 0
        weight_boost = 0
        if age > 65:
            age_boost = interpolate_nonlinear(min(age, 100), 65, 100, 0.10, 1.00)
        if weight > 25:
            weight_boost = interpolate_nonlinear(min(weight, 35), 25, 35, 0.10, 1.00)

        if age > 65 and weight > 25:
            value += max_value * 1.5
        elif age_boost > 0 or weight_boost > 0:
            value += max_value * max(age_boost, weight_boost)

        return value
    #-----------MATH FUNCTION ENDS------------------------#
    try:
        pet_value = Data["PetValueData"][pet_data['name']]
        pet_value = pet_value[0].replace(",", "")
        return compute_value(int(Data["PetValueData"][pet_data['name']][0].replace(",", "")), int(Data["PetValueData"][pet_data['name']][1].replace(",", "")), int(pet_data['age']), float(pet_data['weight']))
    except Exception as e:
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
            type, Data = ParserType(message.content.lower())
            if type == "SeedType":
                data, quantity = GAGValue(Data)
                name = Data["Name"].replace(" ", "_")
                img_path = next((f"src/ui/GAG/{name}.{ext}" for ext in ["png", "webp"] if os.path.exists(f"src/ui/GAG/{name}.{ext}")), None)
                embed = discord.Embed(title=f"VALUE :  {price_formatter(int(data['value']) * quantity)}",
                            colour=0x1000f5)

                embed.set_author(name="BloxTrade")
                embed.set_thumbnail(url="attachment://image.png")
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

            elif type == "PetType":
                pet_value = GAGPetValue(Data)
                name = Data["name"].replace(" ", "_")
                img_path = next((f"src/ui/GAG/{name}.{ext}" for ext in ["png", "webp"] if os.path.exists(f"src/ui/GAG/{name}.{ext}")), None)
                embed = discord.Embed(title=f"VALUE :  {price_formatter(int(pet_value) * 1)}",
                            colour=0x1000f5)
                embed.set_author(name="BloxTrade")
                embed.set_thumbnail(url="attachment://image.png")
                embed.add_field(name="Name",
                                value=Data['name'],
                                inline=False)
                embed.add_field(name="Weight",
                                value=f"{Data['weight']}kg",
                                inline=False)
                embed.add_field(name="Age",
                                value=f"{Data['age']} yrs old",
                                inline=False)
            await message.reply(embed=embed, file=discord.File(img_path, filename="image.png"))
        except Exception as e:
            await message.delete()  
    
    elif message.channel.id == int(Config.gag_worl_channel_id):
            org_message = await message.reply("Thinking...")
            outcome_data, your_side_items, your_side_values, their_side_items, their_side_values = WORL(message.content.lower())
            if your_side_items and their_side_items:
                your_side_items  = [items.replace(" ", "_").title() for items in your_side_items]
                their_side_items  = [items.replace(" ", "_").title() for items in their_side_items]
                winorlossorfair = 0
                if outcome_data['outcome'] == 'Win':
                    winorlossorfair = 0
                elif outcome_data['outcome'] == 'Loss':
                    winorlossorfair = 1
                else:
                    winorlossorfair = 2
                generated_img = LilyWORLGen.GAGGenerateWORLImage(your_side_items[:4], your_side_values, their_side_items[:4], their_side_values, outcome_data['outcome'].title(), f"Your Trade is an {outcome_data['outcome'].title()}", outcome_data['percentage'], winorlossorfair)
                img_buffer = BytesIO()
                generated_img.save(img_buffer, format="PNG")
                img_buffer.seek(0)

                file = discord.File(img_buffer, filename="trade.png")

                await org_message.edit(content="", attachments=[file])