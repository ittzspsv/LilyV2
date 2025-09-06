import json
import websockets
import Config.sBotDetails as Config
import LilyGAG.sLilyGAGCore as GAG
import discord
import asyncio
import Misc.sLilyComponentV2 as CV2

class StockWebSocket:
    def __init__(self, url, bot):
        self.url = url
        self.bot = bot
        self.ws = None
        self.reconnect_interval = 5
        self.headers = {
            'jstudio-key': 'js_27705665c75f87322866d14423c114a7595c0f24151a407e5befc22c1f6841af'
        }

    async def run(self):
        while True:
            try:
                print(f"Connecting to Api ...")
                self.ws = await websockets.connect(self.url, extra_headers=self.headers)
                await self.on_open(self.ws)

                pong_waiter = asyncio.create_task(self.ping_loop())
                async for message in self.ws:
                    await self.on_message(self.ws, message)

            except websockets.exceptions.ConnectionClosed as e:
                await self.on_close(self.ws, e.code, e.reason)
            except Exception as e:
                await self.on_error(self.ws, e)
            finally:
                print(f"Reconnecting in {self.reconnect_interval} seconds...")
                await asyncio.sleep(self.reconnect_interval)

    async def ping_loop(self):
        while self.ws and self.ws.open:
            try:
                await self.ws.ping()
                print("Ping sent.")
                await asyncio.sleep(25)
            except Exception as e:
                print("Ping error:", e)
                break

    async def on_open(self, ws):
        print("WebSocket connected.")

    async def on_message(self, ws, message):
        await self.GAGEndPointParser(self.bot, message)

    async def on_error(self, ws, error):
        print("WebSocket error:", error)

    async def on_close(self, ws, code, reason):
        print(f"WebSocket closed. Code: {code}, Reason: {reason}")
    
    async def GAGEndPointParser(self, bot, data):
        guild = bot.get_guild(Config.GUILD_ID)
        data = json.loads(data)

        sections = [
            "seed_stock",
            "gear_stock",
            "egg_stock",
            "cosmetic_stock",
            "eventshop_stock",
            "weather",
            "notification",
        ]
        parsed = {section: data.get(section, []) for section in sections}

        #SEED STOCK
        seedstock = parsed["seed_stock"]
        gearstock = parsed["gear_stock"]
        seed_pings = []
        gear_pings = []
        if seedstock and gearstock:
            longest_name = max(len(item["display_name"]) for item in seedstock)

            formatted_lines = []
            for item in seedstock:
                display_name = item["display_name"].title()
                role = discord.utils.get(guild.roles, name=display_name)

                if role:
                    seed_pings.append(role.mention)

            for item in gearstock:
                display_name = item["display_name"].title()

                role = discord.utils.get(guild.roles, name=display_name)

                if role:
                    gear_pings.append(role.mention)
            seed_view = CV2.GAGStockComponent("🌱Seed Stock", seedstock, seed_pings)
            gear_view = CV2.GAGStockComponent("⚙️Gear Stock", gearstock, gear_pings)
            await bot.PostCV2View(seed_view, Config.seed_gear_stock_channel_id)
            await bot.PostCV2View(gear_view, Config.seed_gear_stock_channel_id)

        #EGG STOCK
        eggstock = parsed["egg_stock"]
        egg_pings = set()
        if eggstock:
            for item in eggstock:
                display_name = item["display_name"].title()

                role = discord.utils.get(guild.roles, name=display_name)

                if role:
                    egg_pings.add(role.mention)
            egg_view = CV2.GAGStockComponent("🥚Egg Stock", eggstock, egg_pings)
            await bot.PostCV2View(egg_view, Config.eggstock_channel_id)

        #COSMETICS STOCK
        cosmeticsshop = parsed["cosmetic_stock"]
        if cosmeticsshop:
            cosmetic_pings = []
            for items in cosmeticsshop:
                role = discord.utils.get(guild.roles, name=items["display_name"])
                if role:
                    cosmetic_pings.append(role.mention)
            cos_View = CV2.GAGStockComponent("📦Cosmetics Stock", cosmeticsshop, cosmetic_pings)
            await bot.PostCV2View(cos_View, Config.cosmeticsstock_channel_id)

        #WEATHER INFO
        pings = []
        weatherinfo = parsed["weather"]
        if weatherinfo:
            for w in weatherinfo:
                if w.get('active'):
                    name = w['weather_name']
                    if name == "JoshLei":
                        return
                    weather_data = GAG.Data.get('WeatherData', {}).get(name, ["No description available.", "None"])
                    description_text = weather_data[0] if weather_data[0] else "No description available."
                    mutation_text = weather_data[1] if weather_data[1] and weather_data[1] != "None" else "None"
                    try:
                        img = weather_data[2] 
                    except:
                        img = None
                    description = f"{description_text}\n**MUTATIONS:** {mutation_text}"
                    role = discord.utils.get(guild.roles, name=name)
                    if role:
                        pings.append(role.mention)
                    await bot.PostStock(name, description, Config.weatherupdate_channel_id, pings, img)
        pings = ["Event Stock"]
        event_shop_stock = parsed['eventshop_stock']

        if event_shop_stock:
            longest_name = max(len(item["display_name"]) for item in event_shop_stock)
            formatted_lines = [
                f"{item['display_name'].title():<{longest_name}}   **{item['quantity']}x**"
                for item in event_shop_stock
            ]
            eventshop_format_string = "\n".join(formatted_lines)
            pings = []
            for items in event_shop_stock:
                role = discord.utils.get(guild.roles, name=items["display_name"])
                if role:
                    pings.append(role.mention)
            await bot.PostStock("EVENT STOCK", eventshop_format_string, Config.eventshop_channel_id, pings) 
        