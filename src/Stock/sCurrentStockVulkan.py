import requests
from bs4 import BeautifulSoup
import random
import asyncio

url = "https://vulcanvalues.com/blox-fruits/stock"


previous_normal_stock = []
previous_mirage_stock = []


def vGetStock(stock_type=str):
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

        def extract_fruit_data(section_class):
            stock_section = soup.find("div", class_=section_class)
            if not stock_section:
                return []
            
            fruit_list = []
            fruit_items = stock_section.select("ul > li")

            for item in fruit_items:
                fruit_name_tag = item.select_one("span.text-md.font-bold")
                price_tags = item.select("span.text-sm.font-bold")

                fruit_name = fruit_name_tag.text.strip() if fruit_name_tag else "Unknown"
                beli = price_tags[0].text.strip() if len(price_tags) > 0 else "N/A"
                price_robux = price_tags[1].text.strip() if len(price_tags) > 1 else "N/A"

                fruit_list.append({
                    "name": fruit_name,
                    "beli": beli,
                    "robux_price": price_robux
                })

            return fruit_list

        if stock_type == "Normal Stock":
            normal_stock = extract_fruit_data("text-center md:pr-4 md:flex-grow")
            return normal_stock
        else:
            mirage_stock = extract_fruit_data("text-center md:pl-4 md:flex-grow")
            return mirage_stock

        # Display results
        print("=== NORMAL STOCK FRUITS ===")
        for fruit in normal_stock:
            print(f"{fruit['name']}: {fruit['beli']} | {fruit['robux_price']}")

        print("\n=== MIRAGE STOCK FRUITS ===")
        for fruit in mirage_stock:
            print(f"{fruit['name']}: {fruit['beli']} | {fruit['robux_price']}")

    else:
        print("Failed to fetch the webpage.")
