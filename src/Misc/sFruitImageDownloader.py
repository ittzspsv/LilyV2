import requests
import os
import json
import sFruitImageFetcher as FIF

'''
with open("ValueData.json", "r") as file:
    value_data = json.load(file)
    fruit_dict = {fruit["name"] for fruit in value_data}

save_directory = "ui/fruit_icons"
os.makedirs(save_directory, exist_ok=True)

for fruit in fruit_dict:
    try:
        link = FIF.FetchFruitImage(fruit)
        if link:
            response = requests.get(link)
            if response.status_code == 200:
                ext = os.path.splitext(link)[-1]
                if not ext or len(ext) > 5:
                    ext = ".png"

                file_path = os.path.join(save_directory, f"{fruit}{ext}")
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded: {fruit}")
            else:
                print(f"Failed to download {fruit}: Status {response.status_code}")
        else:
            print(f"No link returned for {fruit}")
    except Exception as e:
        print(f"Error processing {fruit}: {e}")'''

response = requests.get("https://static.wikia.nocookie.net/roblox-blox-piece/images/5/51/Dragon_%28West%29Fruit.png")

if response.status_code == 200:
    with open("downloaded_image.png", "wb") as file:
        file.write(response.content)
    print("Image downloaded successfully!")
else:
    print(f"Failed to download image. Status code: {response.status_code}")
