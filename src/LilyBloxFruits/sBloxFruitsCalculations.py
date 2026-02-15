import json
try:
    import Config.sValueConfig as VC
    import Config.sBotDetails as Config
    from LilyBloxFruits.core.sTradeFormatAlgorthim import *
    from ui.sWinOrLossImageGenerator import *

    from . import sLilyBloxFruitsCache as FruitCache
except:
    pass

from PIL import Image

async def fetch_fruit_details(fruit_name: str):
    data = FruitCache.item_dict.get(fruit_name.title(), {})
    return data

def calculate_win_loss(my_value, opponent_value, Type=0):
    try:
        my_value = float(my_value)
        opponent_value = float(opponent_value)
    except ValueError:
        return "Invalid input. Please enter numerical values."
    if Type==0:
        if my_value > opponent_value:
            loss_percentage = (1 - (opponent_value / my_value)) * 100
            return f"Loss Percentage: {100:.1f}%" if loss_percentage > 99.9 else f"Loss Percentage: {loss_percentage:.1f}%"
        elif my_value < opponent_value:
            win_percentage = (1 - (my_value / opponent_value)) * 100
            return f"Win Percentage: {100:.1f}%" if win_percentage > 99.9 else f"Win Percentage: {win_percentage:.1f}%"
        else:
            return "0% - Fair match"
    else:
        if my_value > opponent_value:
            loss_percentage = (1 - (opponent_value / my_value)) * 100
            return 100 if loss_percentage > 99.9 else int(loss_percentage)
        elif my_value < opponent_value:
            win_percentage = (1 - (my_value / opponent_value)) * 100
            return 100 if win_percentage > 99.9 else int(win_percentage)
        else:
            return 0

async def j_LorW(your_fruits=[], your_fruit_type=[], their_fruits=[], their_fruit_type=[], Type=0, suggestion=0):
    fruit_exceed_limit = 0
    if len(your_fruits) > 4 or len(their_fruits) > 4:
        fruit_exceed_limit = 1
    
    total_value_of_your_fruit = 0
    total_value_of_their_fruit = 0

    your_fruit_individual_values = []
    their_fruit_individual_values = []

    # Calculate total value of your fruits
    for fruit, fruit_type in zip(your_fruits, your_fruit_type):
        ydata = await fetch_fruit_details(fruit)

        if isinstance(ydata, dict):
            fruit_type = fruit_type.lower()
            if fruit_type == "permanent":
                value_key = "permanent_value"
            else:
                value_key = "physical_value"

            value = ydata[value_key]
            your_fruit_individual_values.append(value)
            total_value_of_your_fruit += value

    # Calculate total value of their fruits
    for fruit, fruit_type in zip(their_fruits, their_fruit_type):
        ydata = await fetch_fruit_details(fruit)

        if isinstance(ydata, dict):
            fruit_type = fruit_type.lower()
            if fruit_type == "permanent":
                value_key = "permanent_value"
            else:
                value_key = "physical_value"

            value = ydata[value_key]
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

    if Type == 0:
        percentage = calculate_win_loss(total_value_of_your_fruit, total_value_of_their_fruit)
        if (total_value_of_your_fruit < total_value_of_their_fruit and fruit_exceed_limit != 1):
            WORLT = "W"
            output_dict["TradeConclusion"] = f"It's a {WORLT} Trade"
            output_dict["TradeDescription"] = f"**The trade that you are trying to do or you have already done is a {WORLT} trade.  here's why**"
            output_dict["Your_IndividualValues"] = your_fruit_individual_values
            output_dict["Their_IndividualValues"] = their_fruit_individual_values
            output_dict["Your_TotalValue"] = total_value_of_your_fruit
            output_dict["Their_TotalValue"] = total_value_of_their_fruit
            output_dict["ColorKey"] = 0xffd500
            output_dict['Percentage'] = percentage


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
            output_dict['Percentage'] = percentage

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
            output_dict['Percentage'] = percentage

            return output_dict
        
        else:
            output_dict["TradeConclusion"] = f"Fruit Value exceeded for one of the trader"
            output_dict["TradeDescription"] = f""
            output_dict["ColorKey"] = 0xff0000

            return output_dict

    else:
        if (total_value_of_your_fruit < total_value_of_their_fruit and fruit_exceed_limit != 1):
            return GenerateWORLImage(your_fruits, your_fruit_individual_values, their_fruits, their_fruit_individual_values,your_fruit_type, their_fruit_type, trade_winorlose="WIN", trade_conclusion="YOUR TRADE IS AN W", percentage_Calculation=calculate_win_loss(total_value_of_your_fruit, total_value_of_their_fruit, Type=1), winorloseorfair=0, background_type=suggestion)
        elif (total_value_of_your_fruit == total_value_of_their_fruit) and fruit_exceed_limit != 1:
            return GenerateWORLImage(your_fruits, your_fruit_individual_values, their_fruits, their_fruit_individual_values,your_fruit_type, their_fruit_type, trade_winorlose="FAIR", trade_conclusion="YOUR TRADE IS FAIR", percentage_Calculation=calculate_win_loss(total_value_of_your_fruit, total_value_of_their_fruit, Type=1), winorloseorfair=2, background_type=suggestion)
        elif fruit_exceed_limit != 1:
            return GenerateWORLImage(your_fruits, your_fruit_individual_values, their_fruits, their_fruit_individual_values,your_fruit_type, their_fruit_type, trade_winorlose="LOSE", trade_conclusion="YOUR TRADE IS A L", percentage_Calculation=calculate_win_loss(total_value_of_your_fruit, total_value_of_their_fruit, Type=1), winorloseorfair=1, background_type=suggestion)
        else:
            img = Image.open('src/ui/TooManyFruitRequests.png')
            img.resize((int(img.width * 0.7), int(img.height * 0.7)))
            return img


'''
sentence = "i wana trade 2 leopard for 4 doughs"
print(sentence)
print("is it a valid trade format : " , is_valid_trade_format(sentence, fruit_names))
print(extract_trade_details(sentence))'''