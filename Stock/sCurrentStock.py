import requests
from bs4 import BeautifulSoup
import asyncio
import random
import datetime
import pytz


ist = pytz.timezone('Asia/Kolkata')
good_fruits = ["Buddha", "Portal", "Mammoth", "Shadow", "Venom", "Spirit", "T-Rex", "Dough", "Control", "Leopard", "Gas", "Yeti", "Kitsune", "Dragon"]

previous_normal_stock = {}
previous_mirage_stock = {}

def get_stock(url, stock_filter):
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/537.36",
        ]),
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
                    data[name] = {"Value": value, "Stock Type": [stock_type]}

        return data
    else:
        return "Failed to scrape web data"


def is_past_update_time(update_times, max_extra_time=30):
    now = datetime.datetime.now(ist)
    for hour, minute in update_times:
        update_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= update_time and (now - update_time).total_seconds() <= max_extra_time * 60:
            return True
    return False

async def fetch_stock_until_update(stock_filter, retry_delay=300, max_retries=500, post_update_retry=180, max_runtime=1800):   
    global previous_normal_stock, previous_mirage_stock
    retries = 0
    url = "https://fruityblox.com/stock"

    normal_update_times = [
        (5, 30), (9, 30), (13, 30), (17, 30), (21, 30), (1, 30)
    ]
    mirage_update_times = [
        (3, 30), (5, 30), (7, 30), (9, 30), (11, 30), (13, 30),
        (15, 30), (17, 30), (19, 30), (21, 30), (23, 30)
    ]

    start_time = asyncio.get_event_loop().time()

    while retries < max_retries:
        stock_data = get_stock(url, stock_filter)

        if stock_data:
            if stock_filter == "Normal Stock":
                print(is_past_update_time(normal_update_times))
                if stock_data != previous_normal_stock:
                    previous_normal_stock = stock_data
                    return stock_data
                elif is_past_update_time(normal_update_times):
                    print("No stock change", post_update_retry, "seconds.")
                    await asyncio.sleep(post_update_retry)
                    continue
                else:
                    return {}

            elif stock_filter == "Mirage Stock":
                print(is_past_update_time(normal_update_times))
                if stock_data != previous_mirage_stock:
                    previous_mirage_stock = stock_data
                    return stock_data
                elif is_past_update_time(mirage_update_times):
                    print("No Stock Change", post_update_retry, "seconds.")
                    await asyncio.sleep(post_update_retry)
                    continue
                else:
                    return {}

        else:
            print("No stock data received.")

        # Check if max runtime is exceeded
        if asyncio.get_event_loop().time() - start_time > max_runtime:
            print(f"Max runtime of {max_runtime} seconds exceeded. Exiting fetch_stock_until_update.")
            return {}

        await asyncio.sleep(retry_delay)
        retries += 1

    print("Max retries reached. Exiting fetch_stock_until_update.")
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