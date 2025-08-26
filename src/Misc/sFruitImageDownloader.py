import requests
import os
import json
import sFruitImageFetcher as FIF




'''
items = ["Dairy_Cow", "Bacon_Pig", "Jackalope", "Hotdog_Daschund", "Golem", "Lobster_Thermidor", "Golden_Goose", "French_Fry_Ferret", "Junkbot", "Mochi_Mouse", "Spaghetti_Sloth", "Gorilla_Chef", "Mizuchi", "Sushi_Bear"]

save_directory = "src/ui/GAG"
os.makedirs(save_directory, exist_ok=True)

for fruit in items:
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
        print(f"Error processing {fruit}: {e}")

'''

'''
response = requests.get("https://bloxfruitsvalues.com/_next/image?url=https%3A%2F%2Fi.postimg.cc%2FMKcKbW5Z%2FGreen-Lightning.png&w=1920&q=95")


if response.status_code == 200:
    with open("Green Lightning.png", "wb") as file:
        file.write(response.content)
    print("Image downloaded successfully!")
else:
    print(f"Failed to download image. Status code: {response.status_code}")

'''