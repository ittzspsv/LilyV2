import requests
from bs4 import BeautifulSoup

rarity = ["", "common", "uncommon", "rare", "legendary", "mythical", "gamepass", "limited"]


def get_fruit_data(url):
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://google.com",
}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:  # 200 = pass
        soup = BeautifulSoup(response.text, "html.parser")

        # Get all fruit names
        fruit_names = []
        name_elements = soup.select("h1.text-2xl.font-semibold")
        for name in name_elements:
            fruit_names.append(name.get_text(strip=True))

        # Get fruit values
        fruit_values = []
        value_elements = soup.select("h2.text-2xl.contents")
        for value in value_elements:
            text = value.get_text(strip=True)
            if "," in text:
                fruit_values.append(text)

        # Get fruit demand
        fruit_demand = []
        demand_elements = soup.select("h2.text-2xl.contents")
        for demand in demand_elements:
            text = demand.get_text(strip=True)
            if "/" in text:
                fruit_demand.append(text)

        # Get fruit demand type (Overpaid, Fair, etc.)
        fruit_demand_type = []
        demand_type_elements = soup.select("h1.text-sm.font-medium")
        for demand_type in demand_type_elements:
            fruit_demand_type.append(demand_type.get_text(strip=True))

        # Ensure lists have the same length
        while len(fruit_values) < len(fruit_names):
            fruit_values.append("Unknown")
        while len(fruit_demand) < len(fruit_names):
            fruit_demand.append("Unknown")
        while len(fruit_demand_type) < len(fruit_names):
            fruit_demand_type.append("Unknown")

        # Store in dictionary
        fruit_data = {}
        for name, value, demand, demand_type in zip(fruit_names, fruit_values, fruit_demand, fruit_demand_type):
            fruit_data[name] = {"Value": value, "Demand": demand, "Demand Type": demand_type}

        return fruit_data
    else:
        return "Failed to retrieve the webpage."

def FetchRarity(rarity_type):
    url = f'https://bloxfruitsvalues.com/{rarity_type.lower()}'
    fruit_data = get_fruit_data(url)

    if isinstance(fruit_data, dict):
        return fruit_data
    else:
        return None

def PrintRarity(rarity_type):
    for fruit, details in FetchRarity(rarity_type).items():
        print(f"\033[1m{fruit}\033[0m - Value: {details['Value']}, Demand: {details['Demand']}, Demand Type: {details['Demand Type']}")
    
def PrintAllRarity():
    for i in range(1, len(rarity), 1):
        for fruit, details in FetchRarity(rarity[i]).items():
            print(f"\033[1m{fruit}\033[0m - Value: {details['Value']}, Demand: {details['Demand']}, Demand Type: {details['Demand Type']}")

        print("")  #Newline

def FetchFruitDetails(fruit_name):
    for rarity_type in rarity:
        url = f'https://bloxfruitsvalues.com/{rarity_type}'
        fruit_data = get_fruit_data(url)

        if isinstance(fruit_data, dict) and fruit_name.title() in fruit_data:
            details = fruit_data[fruit_name.title()]
            return f"\033[1m{fruit_name.title()}\033[0m - Value: {details['Value']}, Demand: {details['Demand']}, Demand Type: {details['Demand Type']}"

    return f"Fruit '{fruit_name}' not found."

def FetchFruitDetails_DictionaryType(fruit_name):
    for rarity_type in rarity:
        url = f'https://bloxfruitsvalues.com/{rarity_type}'
        fruit_data = get_fruit_data(url)

        if isinstance(fruit_data, dict) and fruit_name.title() in fruit_data:
            details = fruit_data[fruit_name.title()]
            return {"FruitName" : fruit_name.title(), "Value" : details['Value'], "Demand" : details['Demand'], "Demand Type" : details['Demand Type']}

def LorW(your_fruit=[], their_fruits=[]):

    #Capatilizing only the first letter of the list but using titles cuz if there is space beteween strings in a list it also capatilizes that
    your_fruit_proper = your_fruit#[word.title() for word in your_fruit]
    their_fruits_proper = their_fruits#[word.title() for word in their_fruits]

    if len(your_fruit_proper) > 4 or len(their_fruits_proper) > 4:
        return "Fruit Value Exceeded. Remember we can trade only 4 fruits"
    
    total_value_of_your_fruit = 0
    total_value_of_their_fruit = 0

    # Calculate total value of your fruits
    for fruit in your_fruit_proper:
        ydata = FetchFruitDetails_DictionaryType(fruit)
        if isinstance(ydata, dict):
            #Removing commas from values to convert that to an integer
            value = ydata['Value'].replace(",", "")
            total_value_of_your_fruit += int(value)

    # Calculate total value of their fruits
    for fruit in their_fruits_proper:
        tdata = FetchFruitDetails_DictionaryType(fruit)  # Fetch fruit details as dictionary
        if isinstance(tdata, dict):  # Ensure it's a dictionary
            value = tdata['Value'].replace(",", "")  # Remove commas from value
            total_value_of_their_fruit += int(value)
        else:
            return (f"Warning: '{fruit}' not found in the database.")

    if(total_value_of_your_fruit < total_value_of_their_fruit):
        return f"Hey its a W offer for you:blush:  Your fruit Total value is {total_value_of_your_fruit}, Their Fruit total Value is {total_value_of_their_fruit}", total_value_of_your_fruit, total_value_of_their_fruit
    elif(total_value_of_their_fruit == total_value_of_your_fruit):
        return f'Its a Fair Offer! Your fruit Total value is {total_value_of_your_fruit}, Their Fruit total Value is {total_value_of_their_fruit}', total_value_of_your_fruit, total_value_of_their_fruit
    else:
        return f"Its a L offer for you :sob: Look Your fruit Total value is {total_value_of_your_fruit}, Their Fruit total Value is {total_value_of_their_fruit}", total_value_of_your_fruit, total_value_of_their_fruit

#print(LorW(["Kitsune", "Kitsune", "West Dragon"], ["Kitsune", "Leopard"]))