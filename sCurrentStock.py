import requests
from bs4 import BeautifulSoup



good_fruits = ["Buddha", "Portal", "Mammoth", "Shadow", "Venom", "Spirit", "T-Rex", "Dough", "Control", "Leopard", "Gas", "Yeti", "Kitsune", "Dragon"]


def get_stock(url, stock_filter):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:  # 200 = Success
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

def get_current_stock_remaining_time():
    url = 'https://www.gamersberg.com/blox-fruits/stock'
    headers = {"User-Agent": "Mozilla/5.0"}  # Prevents blocking
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Use a valid CSS selector (escaped class names)
    timer_div = soup.select_one("div.lg\\:text-6xl.sm\\:text-5xl.text-4xl.font-bold")

    if timer_div:
        timer_value = timer_div.get_text(strip=True)
        print(f'Timer Value: {timer_value}')
    else:
        print('Timer element not found.')

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