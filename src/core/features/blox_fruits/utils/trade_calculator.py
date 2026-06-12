from ....database.integrations.blox_fruits import BloxFruitsDatabase 
from typing import List, Dict, Any

def calculate_percentage(my_value, opponent_value):
    try:
        my_value = float(my_value)
        opponent_value = float(opponent_value)
    except ValueError:
        return "Invalid input"

    if my_value == opponent_value:
        return 0

    if my_value > opponent_value:
        return round((1 - opponent_value / my_value) * 100, 2)

    return round((1 - my_value / opponent_value) * 100, 2)

def calculate_fruit_values(fruits, fruit_types, db: BloxFruitsDatabase):
    individual_values = []
    total_value = 0

    for fruit, fruit_type in zip(fruits, fruit_types):
        data = db.fetch_fruit_details(fruit)

        if isinstance(data, dict):
            fruit_type = fruit_type.lower()
            value_key = "permanent_value" if fruit_type == "permanent" else "physical_value"

            value = data.get(value_key, 0)
            individual_values.append(value)
            total_value += value

    return individual_values, total_value

def win_or_lose(
        db: BloxFruitsDatabase, 
        your_fruits: List[str]=[], 
        your_fruit_type: List[str]=[], 
        their_fruits: List[str]=[], 
        their_fruit_type: List[str]=[]
    ) -> Dict[str, Any]:
    total_value_of_your_fruit: int = 0
    total_value_of_their_fruit: int = 0

    your_fruit_individual_values: List = []
    their_fruit_individual_values: List = []

    your_fruit_individual_values, total_value_of_your_fruit = calculate_fruit_values(
        your_fruits, your_fruit_type, db
    )

    their_fruit_individual_values, total_value_of_their_fruit = calculate_fruit_values(
        their_fruits, their_fruit_type, db
    )

    percentage = calculate_percentage(total_value_of_your_fruit, total_value_of_their_fruit)
    if total_value_of_your_fruit < total_value_of_their_fruit:
        conclusion = "W"
        conclusion_expansion = "Win"
        color = 0xffd500

    elif total_value_of_your_fruit == total_value_of_their_fruit:
        conclusion = "Fair"
        conclusion_expansion = "Fair"
        color = 0xff6600

    else:
        conclusion = "L"
        conclusion_expansion = "Lose"
        color = 0x79817d


    return {
        "conclusion": conclusion,
        "conclusion_expansion": conclusion_expansion,
        "your_individual_values": your_fruit_individual_values,
        "their_individual_values": their_fruit_individual_values,
        "your_total_values": total_value_of_your_fruit,
        "their_total_values": total_value_of_their_fruit,
        "color_key": color,
        "percentage": percentage
    }