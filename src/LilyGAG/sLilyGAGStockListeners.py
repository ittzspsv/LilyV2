import json
import websockets
import Config.sBotDetails as Config
import discord

class StockWebSocket:
    def __init__(self, url, bot):
        self.url = url
        self.bot = bot

    async def run(self):
        try:
            async with websockets.connect(self.url) as ws:
                await self.on_open(ws)
                async for message in ws:
                    await self.on_message(ws, message)

        except websockets.exceptions.ConnectionClosed as e:
            await self.on_close(ws, e.code, e.reason)
        except Exception as e:
            await self.on_error(ws, e)

    async def on_open(self, ws):
        print("Socket Opened")

    async def on_message(self, ws, message):
        await self.GAGEndPointParser(self.bot, message)

    async def on_error(self, ws, error):
        print("Throwed an Error:", error)

    async def on_close(self, ws, code, msg):
        print(f"SocketClosed: {code}, {msg}")
    
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
        pings = []
        if seedstock:
            longest_name = max(len(item["display_name"]) for item in seedstock)
            formatted_lines = [
                f"{item['display_name']:<{longest_name}}   **{item['quantity']}x**"
                for item in seedstock
            ]
            seedstock_format_string = "\n".join(formatted_lines)
            pings = []
            for items in seedstock:
                role = discord.utils.get(guild.roles, name=items["display_name"])
                if role:
                    pings.append(role.mention)

            await bot.PostStock("SEED STOCK", seedstock_format_string, Config.seed_gear_stock_channel_id, pings)

        #GEAR STOCK
        gearstock = parsed["gear_stock"]
        if gearstock:
            longest_name = max(len(item["display_name"]) for item in gearstock)
            formatted_lines = [
                f"{item['display_name']:<{longest_name}}   **{item['quantity']}x**"
                for item in gearstock
            ]
            gearstock_format_string = "\n".join(formatted_lines)
            pings = []
            for items in gearstock:
                role = discord.utils.get(guild.roles, name=items["display_name"])
                if role:
                    pings.append(role.mention)
            await bot.PostStock("GEAR STOCK", gearstock_format_string, Config.seed_gear_stock_channel_id, pings)

        #EGG STOCK
        eggstock = parsed["egg_stock"]
        if eggstock:
            longest_name = max(len(item["display_name"]) for item in eggstock)
            formatted_lines = [
                f"{item['display_name']:<{longest_name}}   **{item['quantity']}x**"
                for item in eggstock
            ]
            eggstock_format_string = "\n".join(formatted_lines)
            await bot.PostStock("EGG STOCK", eggstock_format_string, Config.eggstock_channel_id)

        #COSMETICS STOCK
        cosmeticsshop = parsed["cosmetic_stock"]
        if cosmeticsshop:
            longest_name = max(len(item["display_name"]) for item in cosmeticsshop)
            formatted_lines = [
                f"{item['display_name']:<{longest_name}}   **{item['quantity']}x**"
                for item in cosmeticsshop
            ]
            cosmeticsshop_format_string = "\n".join(formatted_lines)
            pings = []
            for items in cosmeticsshop:
                role = discord.utils.get(guild.roles, name=items["display_name"])
                if role:
                    pings.append(role.mention)
            await bot.PostStock("COSMETICS STOCK", cosmeticsshop_format_string, Config.cosmeticsstock_channel_id, pings)

        #WEATHER INFO
        pings = []
        weatherinfo = parsed["weather"]
        if weatherinfo:
            for w in weatherinfo:
                if w.get('active'):
                    name = w['weather_name']
                    role = discord.utils.get(guild.roles, name=name)
                    if role:
                        pings.append(role.mention)
                    await bot.PostStock(name, "", Config.weatherupdate_channel_id, pings)
        