import json
import re
from sBotDetails import *
from sTradeFormatAlgorthim import *

value_data_path = "ValueData.json"

fruit_dict = {}
fruit_names = {}

def UpdateFruitDict():
    global fruit_dict
    global fruit_names
    try:
        with open(value_data_path, "r", encoding="utf-8") as file:
            value_data = json.load(file)  # Load JSON data

        fruit_dict = {fruit["name"].lower(): fruit for fruit in value_data}
        fruit_names = {fruit["name"].lower() for fruit in value_data}

    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error: Unable to load {value_data_path}. Check if the file exists and has valid JSON.")

UpdateFruitDict()

def fetch_fruit_details(fruit_name):
    fruit_name = fruit_name.lower()
    
    if fruit_name in fruit_dict:
        fruit = fruit_dict[fruit_name]
        
        return fruit
        '''return {
            "Name": fruit["name"],
            "Physical Value": fruit["physical_value"],
            "Permanent Value": fruit["permanent_value"],
            "Physical Demand": fruit["physical_demand"],
            "Permanent Demand": fruit["permanent_demand"],
            "Demand Type": fruit["demand_type"],
            "Permanent Demand Type": fruit["permanent_demand_type"]
        }'''
    
    return f"Fruit '{fruit_name}' not found in database."

def fetch_all_fruits():
    return value_data

def j_LorW(your_fruits=[], your_fruit_type=[], their_fruits=[], their_fruit_type=[]):
    # Check if trade exceeds the 4-fruit limit
    fruit_exceed_limit = 0
    if len(your_fruits) > 4 or len(their_fruits) > 4:
        fruit_exceed_limit = 1
    
    total_value_of_your_fruit = 0
    total_value_of_their_fruit = 0

    your_fruit_individual_values = []
    their_fruit_individual_values = []

    # Calculate total value of your fruits
    for fruit, fruit_type in zip(your_fruits, your_fruit_type):
        ydata = fetch_fruit_details(fruit)

        if isinstance(ydata, dict):
            fruit_type = fruit_type.lower()
            if fruit_type == "permanent":
                value_key = "permanent_value"
            else:
                value_key = "physical_value"

            refined_value = ydata[value_key].replace(",", "")
            value = int(refined_value)
            your_fruit_individual_values.append(value)
            total_value_of_your_fruit += value

    # Calculate total value of their fruits
    for fruit, fruit_type in zip(their_fruits, their_fruit_type):
        ydata = fetch_fruit_details(fruit)

        if isinstance(ydata, dict):
            fruit_type = fruit_type.lower()
            if fruit_type == "permanent":
                value_key = "permanent_value"
            else:
                value_key = "physical_value"

            refined_value = ydata[value_key].replace(",", "")
            value = int(refined_value)
            their_fruit_individual_values.append(value)
            total_value_of_their_fruit += value

        output_dict = {
            "TradeConclusion" : "W or L",
            "TradeDescription" : "",
            "Your_IndividualValues" : [],
            "Their_IndividualValues" : [],
            "Your_TotalValue" : "",
            "Their_TotalValue" : "",
            "ColorKey" : ""

        }

    if (total_value_of_your_fruit < total_value_of_their_fruit and fruit_exceed_limit != 1):
        WORLT = "W"
        output_dict["TradeConclusion"] = f"It's a {WORLT} Trade"
        output_dict["TradeDescription"] = f"**The trade that you are trying to do or you have already done is a {WORLT} trade.  here's why**"
        output_dict["Your_IndividualValues"] = your_fruit_individual_values
        output_dict["Their_IndividualValues"] = their_fruit_individual_values
        output_dict["Your_TotalValue"] = total_value_of_your_fruit
        output_dict["Their_TotalValue"] = total_value_of_their_fruit
        output_dict["ColorKey"] = 0xffd500


        return output_dict
    elif (total_value_of_your_fruit == total_value_of_their_fruit) and fruit_exceed_limit != 1:
        WORLT = "Fair"
        output_dict["TradeConclusion"] = f"It's a {WORLT} Trade"
        output_dict["TradeDescription"] = f"**The trade that you are trying to do or you have already done is a {WORLT} trade.  here's why**"
        output_dict["Your_IndividualValues"] = your_fruit_individual_values
        output_dict["Their_IndividualValues"] = their_fruit_individual_values
        output_dict["Your_TotalValue"] = total_value_of_your_fruit
        output_dict["Their_TotalValue"] = total_value_of_their_fruit
        output_dict["ColorKey"] = 0xff6600

        return output_dict
    
    elif fruit_exceed_limit != 1:
        WORLT = "L"
        output_dict["TradeConclusion"] = f"It's a {WORLT} Trade"
        output_dict["TradeDescription"] = f"**The trade that you are trying to do or you have already done is a {WORLT} trade.  here's why**"
        output_dict["Your_IndividualValues"] = your_fruit_individual_values
        output_dict["Their_IndividualValues"] = their_fruit_individual_values
        output_dict["Your_TotalValue"] = total_value_of_your_fruit
        output_dict["Their_TotalValue"] = total_value_of_their_fruit
        output_dict["ColorKey"] = 0x79817d

        return output_dict
    
    else:
        output_dict["TradeConclusion"] = f"Fruit Value exceeded for one of the trader"
        output_dict["TradeDescription"] = f"In Blox fruit you can only trade upto 4 fruits at a time. \n\nIf you wanna trade multiple fruits like that then make sure to use **{server_name}'s Middlemen System** for a **safe** and **trusted multiple trades**.  You can request for a middlemen here <#{middle_men_channel_id}>"
        output_dict["ColorKey"] = 0xff0000

        return output_dict

def calculate_win_loss(my_value, opponent_value):
    try:
        my_value = float(my_value)
        opponent_value = float(opponent_value)
    except ValueError:
        return "Invalid input. Please enter numerical values."
    
    if my_value > opponent_value:
        loss_percentage = (1 - (opponent_value / my_value)) * 100
        return f"Loss Percentage: {100:.1f}%" if loss_percentage > 99.9 else f"Loss Percentage: {loss_percentage:.1f}%"
    elif my_value < opponent_value:
        win_percentage = (1 - (my_value / opponent_value)) * 100
        return f"Win Percentage: {100:.1f}%" if win_percentage > 99.9 else f"Win Percentage: {win_percentage:.1f}%"
    else:
        return "0% - Fair match"


#Custom algorthim that extracts your fruit and their fruits based on commas
#Example - I wanna trade my perm leopard for his kitsune, kitsune, kitsune, kitsune
#UPDATE - i wana trade my 2 leopard for 4 dough
def extract_fruits(text):
    fruits = []
    fruit_types = []
    words = re.split(r",\s*|\s+", text)
    i = 0
    while i < len(words):
        item = words[i]

        if item.isdigit():
            quantity = int(item)
            i += 1
            if i < len(words):
                item = words[i]
        else:
            quantity = 1

        is_permanent = PermanentMatch(item)
        if is_permanent:
            i += 1
            if i < len(words):
                item = words[i]

        matched_fruit = None
        for length in range(3, 0, -1):
            possible_fruit = " ".join(words[i:i+length])
            matched_fruit = MatchFruitSet(possible_fruit, fruit_names)
            if matched_fruit:
                i += length - 1
                break

        if matched_fruit:
            fruit_type = "permanent" if is_permanent else "physical"
            fruits.extend([matched_fruit.title()] * quantity)
            fruit_types.extend([fruit_type] * quantity)

        i += 1
    
    return fruits, fruit_types

def extract_trade_details(sentence):
    sentence = sentence.lower().replace("?", "")

    sentence = re.sub(r"\b(w|l)\s*or\s*(w|l)\??", "", sentence).strip()

    trade_parts = sentence.split(" for ")
    if len(trade_parts) < 2:
        return [], [], [], []

    clean_your_side = predict_trade_message(trade_parts[0], TradeInitializer)
    clean_their_side = predict_trade_message(trade_parts[1], OpponentTradeSplitter)

    your_fruits, your_fruit_type = extract_fruits(clean_your_side)
    their_fruits, their_fruit_type = extract_fruits(clean_their_side)

    return your_fruits, your_fruit_type, their_fruits, their_fruit_type



def update_fruit_data_json_type(json_file_path, updated_fruits):
    with open(json_file_path, "r", encoding="utf-8") as json_file:
        fruit_data = json.load(json_file)

    fruit_dict = {fruit["name"].lower(): fruit for fruit in fruit_data}

    for new_fruit in updated_fruits:
        fruit_name = new_fruit["name"].lower()
        
        if fruit_name in fruit_dict:
            fruit_dict[fruit_name].update(new_fruit)
        else:
            print(f"Warning: {new_fruit['name']} not found in the JSON. Skipping update.")

    updated_fruit_data = list(fruit_dict.values())

    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(updated_fruit_data, json_file, indent=4, ensure_ascii=False)

    UpdateFruitDict()
    print("JSON successfully updated!")

def update_fruit_data(name, physical_value, permanent_value, physical_demand, permanent_demand, demand_type, permanent_demand_type):
    updated_fruits = [
    {
        "name": name,
        "physical_value": physical_value,
        "permanent_value": permanent_value,
        "physical_demand": physical_demand,
        "permanent_demand": permanent_demand,
        "demand_type": demand_type,
        "permanent_demand_type": permanent_demand_type
    }
]
    
    update_fruit_data_json_type(value_data_path, updated_fruits)


'''
sentence = "i wana trade 2 leopard for 4 doughs"
print(sentence)
print("is it a valid trade format : " , is_valid_trade_format(sentence, fruit_names))
print(extract_trade_details(sentence))'''