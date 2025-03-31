import requests
from bs4 import BeautifulSoup

predefined_images = {
    "Fruit Notifier": "https://static.wikia.nocookie.net/roblox-blox-piece/images/9/98/BadgeFruitNotifier.png/",
    "2x Money": "https://static.wikia.nocookie.net/roblox-blox-piece/images/c/cf/BadgeMoneyx2.png/",
    "2X Money": "https://static.wikia.nocookie.net/roblox-blox-piece/images/c/cf/BadgeMoneyx2.png/",
    "2x Mastery": "https://static.wikia.nocookie.net/roblox-blox-piece/images/1/16/BadgeMasteryx2.png/",
    "2X Mastery": "https://static.wikia.nocookie.net/roblox-blox-piece/images/1/16/BadgeMasteryx2.png/",
    "2x Boss Drops": "https://static.wikia.nocookie.net/roblox-blox-piece/images/3/3a/BadgeBossDrops.png/",
    "2X Boss Drops": "https://static.wikia.nocookie.net/roblox-blox-piece/images/3/3a/BadgeBossDrops.png/",
    "Fast Boats": "https://static.wikia.nocookie.net/roblox-blox-piece/images/f/fa/BadgeBoats.png/",
    "Chromatic Skin": "https://static.wikia.nocookie.net/roblox-blox-piece/images/d/d9/Chromaticdragon.png/",
    "Mythical Scrolls": "https://static.wikia.nocookie.net/roblox-blox-piece/images/9/9f/BadgeMythicalScrollx3.png/",
    "Legendary Scrolls": "https://static.wikia.nocookie.net/roblox-blox-piece/images/3/3e/BadgeLegendaryScrollx5.png/",
    "Dragon Token": "https://static.wikia.nocookie.net/roblox-blox-piece/images/6/61/DragonTokenPhysical.png/",
    "Permanent Dragon Token": "https://static.wikia.nocookie.net/roblox-blox-piece/images/2/29/Dragon_Token_%28Permanent%29.png/",
    "Fruit Storage"  : "https://static.wikia.nocookie.net/roblox-blox-piece/images/6/6a/BadgeFruitStorage.png",
    "Trex" : "https://static.wikia.nocookie.net/roblox-blox-piece/images/e/ea/T-RexFruit.png"
}

def FetchFruitImage(fruit_name, imgsize):
    fruit_name_1 = "Dragon" if fruit_name in ["East Dragon", "West Dragon", "Dragon"] else fruit_name

    if fruit_name_1 in predefined_images:
        return predefined_images[fruit_name_1]

    url = f"https://blox-fruits.fandom.com/wiki/{fruit_name_1}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        figure_tag = soup.find("figure", class_="pi-item pi-image")
        
        if figure_tag:
            img_tag = figure_tag.find("img")
            if img_tag and "src" in img_tag.attrs:
                img_url = img_tag["src"]
                clean_url = img_url.split("/revision")[0]  # Remove unnecessary URL parts
                return clean_url

    return None
