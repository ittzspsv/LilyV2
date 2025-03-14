import requests
from bs4 import BeautifulSoup

url = "https://vulcanvalues.com/blox-fruits/stock"


headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

def vGetStock(stock_type=str):
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

        if stock_type.lower() == "normalstock":
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