import json
import os
import re
from rapidfuzz import fuzz
import discord
from io import BytesIO
try:
    import Config.sBotDetails as Config
    import ui.sWinOrLossImageGenerator as LilyWORLGen
    import Config.sValueConfig as VC
    import Misc.sLilyComponentV2 as CV2
except:
    pass


def price_formatter(value):
    if value >= 1_000_000_000_000_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000_000:.1f}DX"
    elif value >= 1_000_000_000_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000:.1f}NX"
    elif value >= 1_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000:.1f}OX"
    elif value >= 1_000_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000_000:.1f}SPX"
    elif value >= 1_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000:.1f}SX"
    elif value >= 1_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000:.1f}QI"
    elif value >= 1_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000:.1f}QT"
    elif value >= 1_000_000_000_000:  
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

async def GAGMessageParser(sentence, threshold=80):
    mutations = [row[0] for row in await (await VC.vdb.execute("SELECT mutation_name FROM GAG_MutationData")).fetchall()]
    parser = sentence.split()

    sheckle_value = re.findall(r'\b(\d+(?:\.\d+)?[kKmMbBtT])\b', sentence)
    if sheckle_value:
        return ("Bone Blossom", "", tuple(), "", "", 1, value_parser(sheckle_value[0])), []

    plant_names = [row[0] for row in await (await VC.vdb.execute("SELECT name FROM GAG_PlantsData")).fetchall()]
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
    plant_set = {name.lower() for name in plant_names}

    if fruit_name is not None and fruit_name.lower() in plant_set:
        fruit_data = fruit_name
    else:
        fruit_data = None

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
    for mutation in mutations:
        match_score = fuzz.partial_ratio(mutation.lower(), sentence.lower())
        if match_score >= threshold:
            mutations_found.append(mutation)

    fruit_type = [row[0] for row in await (await VC.vdb.execute("SELECT fruit_type FROM GAG_FruitTypeData")).fetchall()]
    fruittype = ""
    for fruittype in fruit_type:
        match_score = fuzz.partial_ratio(fruittype.lower(), sentence.lower())
        if match_score >= threshold:
            fruit_type = fruittype
            break
    return (fruit_name, weight, tuple(mutations_found), fruit_type, quantity, 0, 0), best_match

async def GAGPetMessageParser(sentence, threshold=75):
    parser = sentence.split()
    
    cursor = await VC.vdb.execute("SELECT PetName FROM GAG_PetValue")
    rows = await cursor.fetchall()
    pet_names = [row[0] for row in rows]
    pet_name_map = {p.lower(): p for p in pet_names}
    
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
    age_keywords = {"yr", "yrs", "year", "years", "age"}
    
    for i, word in enumerate(parser):
        lw = word.lower().strip(":= ")
        if any(lw.startswith(k) or lw.endswith(k) for k in age_keywords):
            digits = re.findall(r"\d+", word)
            if digits:
                pet_age = int(digits[0])
                break
        if word.isdigit() and i + 1 < len(parser):
            if parser[i + 1].lower().strip(":= ") in age_keywords:
                pet_age = int(word)
                break
        if lw in age_keywords and i + 1 < len(parser):
            if parser[i + 1].isdigit():
                pet_age = int(parser[i + 1])
                break
        if lw in age_keywords and i + 2 < len(parser):
            if parser[i + 1].lower() in {"is", "was"} and parser[i + 2].isdigit():
                pet_age = int(parser[i + 2])
                break
    if pet_age == 0:
        pet_age = 1
    
    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', sentence, re.IGNORECASE)
    pet_weight = float(weight_match.group(1)) if weight_match else 1

    quantity = 1
    for word in parser:
        if word.isdigit():
            quantity = int(word)
            break
    
    pet_mutation = ""
    cursor = await VC.vdb.execute("SELECT name FROM GAG_PetMutationData")
    rows = await cursor.fetchall()
    mutation_names = [row[0] for row in rows]
    
    for mutation in mutation_names:
        if fuzz.partial_ratio(mutation.lower(), sentence.lower()) >= 80:
            pet_mutation = mutation
            break
    
    return {
        "name": pet_name[0],
        "age": pet_age,
        "weight": pet_weight,
        "quantity": quantity,
        "pet_mutation": pet_mutation
    }, pet_name

async def ParserType(sentence):
    seed_Data, fuzzresultant = await GAGMessageParser(sentence)
    pet_Data, secondary_fuzzresultant = await GAGPetMessageParser(sentence)

    if seed_Data[-2] == 1 and seed_Data[-1]:
        print(seed_Data[-1])
        return "SeedType", seed_Data
    elif seed_Data[0] != None and (fuzzresultant[1] > secondary_fuzzresultant[1]):
        return "SeedType", seed_Data
    elif pet_Data['name'] != None and ((fuzzresultant[1] < secondary_fuzzresultant[1])):
        return "PetType", pet_Data,
    else:
        return "None", {}

async def GAGValue(fruit_data):
    name, weight, mutations, variant, quantity, shecklebool, sheckles = fruit_data

    if shecklebool == 1:
        return {
            'value': int(sheckles),
            "Name": str(name),
            "Weight": str(weight),
            "Variant": str(variant),
            "Mutation": ",".join(mutations) if mutations else ""
        }, 1

    cursor = await VC.vdb.execute(
        "SELECT baseValue, weightDivisor FROM GAG_PlantsData WHERE name = ?",
        (name,)
    )
    row = await cursor.fetchone()
    baseValue, weightDivisor = row if row else (1, 1)

    if mutations:
        placeholders = ",".join("?" for _ in mutations)
        query = f"SELECT value FROM GAG_MutationData WHERE mutation_name IN ({placeholders})"
        cursor = await VC.vdb.execute(query, mutations)
        mutation_rows = await cursor.fetchall()
        mutation_values = [row[0] for row in mutation_rows]
    else:
        mutation_values = []

    mutation_multiplier = sum(mutation_values) - len(mutations)

    cursor = await VC.vdb.execute(
        "SELECT value FROM GAG_FruitTypeData WHERE fruit_type = ?",
        (variant,)
    )
    row = await cursor.fetchone()
    fruit_type_multiplier = row[0] if row else 1.0

    Total_Value = baseValue * ((weight / weightDivisor) ** 2) * fruit_type_multiplier * (1 + mutation_multiplier)

    params = {
        "Name": str(name),
        "Weight": str(weight),
        "Variant": str(variant),
        "Mutation": ",".join(mutations) if mutations else "",
        "value": Total_Value * quantity
    }

    return params, quantity
    
async def GAGPetValue(pet_data):
    #-------------------MATH FUNCTION STARTS----------------------#
    def interpolate_nonlinear(value, in_min, in_max, out_min, out_max):
        return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)

    def age_factor(age):
        return interpolate_nonlinear(max(0, min(age, 100)), 0, 100, 0.00000001, 0.00001)

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

    def compute_value(min_value, max_value, age, weight, mutation_multiplier=0):
        a_factor = age_factor(age)
        w_factor = weight_factor(weight)

        combined_factor = (a_factor + w_factor) / 2
        value = interpolate_nonlinear(combined_factor, 0, 1, min_value, max_value)

        # Mutation multiplier
        if mutation_multiplier:
            value += value * mutation_multiplier

        return value
    #-----------MATH FUNCTION ENDS------------------------#

    cursor = await VC.vdb.execute(
        "SELECT MinValue, MaxValue FROM GAG_PetValue WHERE PetName = ?",
        (pet_data['name'],)
    )
    row = await cursor.fetchone()
    if not row:
        raise ValueError(f"Pet '{pet_data['name']}' not found in database.")
    min_value, max_value = row

    mutation_multiplier = 0
    pet_mutation = pet_data.get('pet_mutation')
    if pet_mutation:
        cursor = await VC.vdb.execute(
            "SELECT value FROM GAG_PetMutationData WHERE name = ?",
            (pet_mutation,)
        )
        mutation_row = await cursor.fetchone()
        if mutation_row:
            mutation_multiplier = mutation_row[0]

    return compute_value(
        int(min_value),
        int(max_value),
        int(pet_data['age']),
        float(pet_data['weight']),
        mutation_multiplier
    )

def PetWeightChart(age: int, weight: float, max_age: int = 100):
    weight_chart = []
    
    for a in range(1, max_age + 1):
        estimated_weight = weight / (age + 10) * (a + 10)
        weight_chart.append(round(estimated_weight, 2))
    
    return weight_chart

'''
def EvaluatePetSkill(name, Age=1, Weight=1):
    def time_to_seconds(t: str) -> int:
        m, s = map(int, t.split(":"))
        return m * 60 + s

    def seconds_to_time(sec: int) -> str:
        m, s = divmod(sec, 60)
        return f"{m:02}:{s:02}"

    def interpolate(start, end, age, stat_type, weight=10):
        factor = (age - 1) / 99 * (weight / 10)

        if stat_type == "time":
            start_sec = time_to_seconds(start)
            end_sec = time_to_seconds(end)
            val = start_sec + (end_sec - start_sec) * factor
            return seconds_to_time(round(val))
        elif stat_type == "float":
            val = start + (end - start) * factor
            return round(val, 2)
        elif stat_type == "int":
            val = start + (end - start) * factor
            return int(round(val))
        return start

    def get_ability_text(ability, age, weight=10):
        stats = {}
        for k, v in ability["stats"].items():
            stats[k] = interpolate(v["start"], v["end"], age, v["type"], weight)
        return ability["description"].format(**stats)
    for ability in Data["PetAbilities"]['abilities']:
        if ability['name'] == name:
            if Weight == 1:
                Weight = PetWeightChart(1, 1)[-1]
            return get_ability_text(ability, Age, Weight)
    else:
        return "Not Available :("
'''
async def WORL(message:str=None):
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
            valuedata, quantity = await GAGValue(Tuple)
            your_side_items.append(valuedata['Name'])
            your_side_values.append(int(valuedata['value']) * quantity)
        if type == "PetType":
            value = await GAGPetValue(data)
            your_side_items.append(data['name'])
            your_side_values.append(value)

    for split in their_side_split:
        type, data = ParserType(split)
        if type == "SeedType":
            Tuple  = data
            valuedata, quantity = await GAGValue(Tuple)
            their_side_items.append(valuedata['Name'])
            their_side_values.append(int(valuedata['value']) * quantity)
        if type == "PetType":
            value = await GAGPetValue(data)
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
    channel_configs = Config.load_channel_config(await bot.get_context(message))
    if message.channel.id == channel_configs.get('gag_values', 0):
            type, Data = await ParserType(message.content.lower())
            if type == "SeedType":
                data, quantity = await GAGValue(Data)
                name = Data[0].replace(" ", "_")
                cursor = await VC.vdb.execute("SELECT icon_link FROM GAG_PlantsData WHERE name = ?", (name,))
                row = await cursor.fetchone()
                if row is not None:
                    link = row[0]
                else:
                    link = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Question_opening-closing.svg/800px-Question_opening-closing.svg.png"  # or handle empty result             
                view = CV2.GAGFruitValueComponent(price_formatter(int(data['value'])), f"{data['Weight']}kg", data["Variant"], data['Name'],data['Mutation'], link)

            elif type == "PetType":
                pet_value = await GAGPetValue(Data)
                name = Data["name"].replace(" ", "_")
                cursor = await VC.vdb.execute("SELECT icon_link FROM GAG_PetValue WHERE PetName = ?", (name,))
                row = await cursor.fetchone()
                if row is not None:
                    link = row[0]
                else:
                    link = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Question_opening-closing.svg/800px-Question_opening-closing.svg.png"
                classification = ""
                classification_mapping = {
                        "Small": (0.7, 1.4),
                        "Normal": (1.4, 3.9),
                        "Semi Huge": (3.9, 4.9),
                        "Huge": (4.9, 7.9),
                        "Titanic": (7.9, 8.9),
                        "Godly": (8.9, 11)
                    }

                value = float(PetWeightChart(int(Data['age']), int(Data['weight']))[0])
                for category, (low, high) in classification_mapping.items():
                    if low <= value < high:
                        classification = category
                        break

                view = CV2.GAGPetValueComponent(price_formatter(int(pet_value) * 1), f'{Data['weight']} kg', f'{Data['age']}', Data['name'], link, Data['pet_mutation'], classification)
            await message.reply(view=view)

    elif message.channel.id == channel_configs.get('gag_worl', 0):
        try:
            org_message = await message.reply("Thinking...")
            outcome_data, your_side_items, your_side_values, their_side_items, their_side_values = await WORL(message.content.lower())
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
        except:
            await message.delete()
            await org_message.delete()