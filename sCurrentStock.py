import requests
from bs4 import BeautifulSoup
import asyncio
import random



good_fruits = ["Buddha", "Portal", "Mammoth", "Shadow", "Venom", "Spirit", "T-Rex", "Dough", "Control", "Leopard", "Gas", "Yeti", "Kitsune", "Dragon"]


def get_stock(url, stock_filter):
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        ])
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Fruit Names
        fruit_names = [name.get_text(strip=True) for name in soup.select("h3.font-medium")]

        # Fruit Values
        fruit_values = []
        value_elements = soup.select("span.text-sm.font-medium")
        for value in value_elements:
            text = value.get_text(strip=True)
            if "$" in text:
                fruit_values.append(text)

        # Type of stock
        stock_types = [stock.get_text(strip=True) for stock in soup.select("span.text-xs.text-gray-400")]


        while len(fruit_values) < len(fruit_names):
            fruit_values.append("Unknown")
        while len(stock_types) < len(fruit_names):
            stock_types.append("Unknown")

        data = {}

        for name, value, stock_type in zip(fruit_names, fruit_values, stock_types):
            if stock_filter.lower() in stock_type.lower():
                if name in data:
                    data[name]["Stock Type"].append(stock_type)

                else:
                    data[name] = {"Value": value, "Stock Type": [stock_type]}  # Store as list

        return data
    else:
        return "Failed to scrape web data"



async def fetch_stock_until_update(stock_filter, retry_delay=100, max_retries=500):    
    retries = 0
    url = "https://fruityblox.com/stock"
    while retries < max_retries:
        stock_data = get_stock(url, stock_filter)
        if stock_data:
            return stock_data
        await asyncio.sleep(retry_delay)
        retries += 1

    return {}


# Fetch only Normal Stock fruits
def get_normal_stock():
    url = "https://fruityblox.com/stock"
    return get_stock(url, "Normal Stock")

# Fetch only Mirage Stock fruits
def get_mirage_stock():
    url = "https://fruityblox.com/stock"
    return get_stock(url, "Mirage Stock")

# Fetch and print Normal Stock data
def PrintNormalStock():
    current_good_fruits = []
    normal_stock_data = get_normal_stock()
    print("Normal Stock")
    if isinstance(normal_stock_data, dict) and normal_stock_data:
        for fruit, details in normal_stock_data.items():
            stock_display = ", ".join(details['Stock Type'])
            print(f"\033[1m {fruit}\033[0m - Value = {details['Value']}, Stock Type - {stock_display}")

        for fruit, details in normal_stock_data.items():
            if fruit in good_fruits:
                current_good_fruits.append(fruit)

        if current_good_fruits != []:
            print("@User_Tag", current_good_fruits, "Are in", "Normal Stock Make sure to buy them")

    else:
        print("No Normal Stock fruits found.")

def PrintMirageStock():
    mirage_stock_data = get_mirage_stock()
    current_good_fruits = []
    print("Mirage Stock")
    if isinstance(mirage_stock_data, dict) and mirage_stock_data:
        for fruit, details in mirage_stock_data.items():
            stock_display = ", ".join(details['Stock Type'])
            print(f"\033[1m {fruit}\033[0m - Value = {details['Value']}, Stock Type - {stock_display}")

        for fruit, details in mirage_stock_data.items():
            if fruit in good_fruits:
                current_good_fruits.append(fruit)

        if current_good_fruits != []:
            print("@User_Tag", current_good_fruits, "Are in", "Mirage Stock Make sure to buy them")
    else:
        print("No Mirage Stock fruits found.")