import json
import websockets
import Config.sBotDetails as Config
import LilyGAG.sLilyGAGCore as GAG
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

            formatted_lines = []
            for item in seedstock:
                display_name = item["display_name"].title()
                quantity = item["quantity"]

                emoji = discord.utils.get(guild.emojis, name=display_name.replace(" ", "_")) or "❓"
                role = discord.utils.get(guild.roles, name=display_name)

                if role:
                    pings.append(role.mention)

                line = f"{emoji} {display_name:<{longest_name}}   **{quantity}x**"
                formatted_lines.append(line)

            seedstock_format_string = "\n".join(formatted_lines)
            await bot.PostStock("SEED STOCK", seedstock_format_string, Config.seed_gear_stock_channel_id, pings)

        #GEAR STOCK
        gearstock = parsed["gear_stock"]
        if gearstock:
            longest_name = max(len(item["display_name"]) for item in gearstock)
            formatted_lines = [
                f"{item['display_name'].title():<{longest_name}}   **{item['quantity']}x**"
                for item in gearstock
            ]
            gearstock_format_string = "\n".join(formatted_lines)
            pings = []
            for items in gearstock:
                role = discord.utils.get(guild.roles, name=items["display_name"].title())
                if role:
                    pings.append(role.mention)
            await bot.PostStock("GEAR STOCK", gearstock_format_string, Config.seed_gear_stock_channel_id, pings)

        #EGG STOCK
        eggstock = parsed["egg_stock"]
        pings = set()
        if eggstock:
            longest_name = max(len(item["display_name"]) for item in eggstock)

            formatted_lines = []
            for item in eggstock:
                display_name = item["display_name"].title()
                quantity = item["quantity"]

                emoji = discord.utils.get(guild.emojis, name=display_name.replace(" ", "_")) or "❓"
                role = discord.utils.get(guild.roles, name=display_name)

                if role:
                    pings.add(role.mention)

                line = f"{emoji} {display_name:<{longest_name}}   **{quantity}x**"
                formatted_lines.append(line)

            eggstock_format_string = "\n".join(formatted_lines)
            await bot.PostStock("SEED STOCK", eggstock_format_string, Config.eggstock_channel_id, list(pings))

        #COSMETICS STOCK
        cosmeticsshop = parsed["cosmetic_stock"]
        if cosmeticsshop:
            longest_name = max(len(item["display_name"]) for item in cosmeticsshop)
            formatted_lines = [
                f"{item['display_name'].title():<{longest_name}}   **{item['quantity']}x**"
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
                    weather_data = GAG.Data.get('WeatherData', {}).get(name, ["No description available.", "None"])
                    description_text = weather_data[0] if weather_data[0] else "No description available."
                    mutation_text = weather_data[1] if weather_data[1] and weather_data[1] != "None" else "None"
                    description = f"{description_text}\n**MUTATIONS:** {mutation_text}"
                    role = discord.utils.get(guild.roles, name=name)
                    if role:
                        pings.append(role.mention)
                    await bot.PostStock(name, description, Config.weatherupdate_channel_id, pings)
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
        