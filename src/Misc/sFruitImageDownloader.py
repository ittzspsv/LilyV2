import asyncio
import aiohttp
import os




'''
items = ["T-Rex", "Spinosaurus"]

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

async def DownloadImage(name, dir, url, name_type=0):
    os.makedirs(dir, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.read()
                filename = f"{name.replace(' ', '_')}.png" if name_type == 1 else f"{name}.png"
                filepath = os.path.join(dir, filename)

                with open(filepath, "wb") as file:
                    file.write(data)
                return True
            else:
                return False