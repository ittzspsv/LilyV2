import json
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

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        fruit_names = [tag.get_text(strip=True) for tag in soup.select("h1.text-2xl.font-semibold")]

        fruit_values = [tag.get_text(strip=True) for tag in soup.select("h2.text-2xl.contents") if "," in tag.get_text()]

        fruit_demand = [tag.get_text(strip=True) for tag in soup.select("h2.text-2xl.contents") if "/" in tag.get_text()]

        fruit_demand_type = [tag.get_text(strip=True) for tag in soup.select("h1.text-sm.font-medium")]

        while len(fruit_values) < len(fruit_names):
            fruit_values.append("Unknown")
        while len(fruit_demand) < len(fruit_names):
            fruit_demand.append("Unknown")
        while len(fruit_demand_type) < len(fruit_names):
            fruit_demand_type.append("Unknown")

        fruit_data_list = []
        for name, value, demand, demand_type in zip(fruit_names, fruit_values, fruit_demand, fruit_demand_type):
            fruit_data_list.append({
                "name": name,
                "physical_value": value,
                "permanent_value": "",
                "physical_demand": demand,
                "permanent_demand": "",
                "demand_type": demand_type,
                "permanent_demand_type": ""
            })

        return fruit_data_list
    else:
        return None

def fetch_all_fruit_data():
    all_fruit_data = []
    for rarity_type in rarity[1:]:  # Skipping the empty string
        url = f'https://bloxfruitsvalues.com/{rarity_type}'
        fruit_data = get_fruit_data(url)
        if fruit_data:
            all_fruit_data.extend(fruit_data)

    return all_fruit_data

all_fruit_data = fetch_all_fruit_data()

with open("blox_fruits_data.json", "w", encoding="utf-8") as json_file:
    json.dump(all_fruit_data, json_file, indent=4, ensure_ascii=False)