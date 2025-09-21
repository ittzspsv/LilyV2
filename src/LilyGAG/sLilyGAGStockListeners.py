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
        backoff = self.reconnect_interval
        while True:
            try:
                print(f"Connecting to API ...")
                self.ws = await websockets.connect(
                    self.url,
                    extra_headers=self.headers,
                    ping_interval=30, 
                    ping_timeout=15
                )
                print("WebSocket connected.")
                backoff = self.reconnect_interval

                async for message in self.ws:
                    await self.on_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                await self.on_close(e.code, e.reason)
            except Exception as e:
                await self.on_error(e)
            finally:
                print(f"Reconnecting in {backoff} seconds...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)

    async def on_message(self, message):
        try:
            await self.GAGEndPointParser(self.bot, message)
        except Exception as e:
            print(f"Message parse error: {e}")

    async def on_error(self, error):
        print("WebSocket error:", error)

    async def on_close(self, code, reason):
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

        # ---- SEED & GEAR ----
        seedstock, gearstock = parsed["seed_stock"], parsed["gear_stock"]
        if seedstock or gearstock:
            seed_pings, gear_pings = [], []

            for item in seedstock:
                role = discord.utils.get(guild.roles, name=item["display_name"].title())
                if role:
                    seed_pings.append(role.mention)

            for item in gearstock:
                role = discord.utils.get(guild.roles, name=item["display_name"].title())
                if role:
                    gear_pings.append(role.mention)

            if seedstock:
                seed_view = CV2.GAGStockComponent("🌱Seed Stock", seedstock, seed_pings)
                await bot.PostCV2View(seed_view, Config.seed_gear_stock_channel_id)

            if gearstock:
                gear_view = CV2.GAGStockComponent("⚙️Gear Stock", gearstock, gear_pings)
                await bot.PostCV2View(gear_view, Config.seed_gear_stock_channel_id)

        # ---- EGGS ----
        eggstock = parsed["egg_stock"]
        if eggstock:
            egg_pings = {
                discord.utils.get(guild.roles, name=item["display_name"].title()).mention
                for item in eggstock
                if discord.utils.get(guild.roles, name=item["display_name"].title())
            }
            egg_view = CV2.GAGStockComponent("🥚Egg Stock", eggstock, egg_pings)
            await bot.PostCV2View(egg_view, Config.eggstock_channel_id)

        # ---- COSMETICS ----
        cosmeticsshop = parsed["cosmetic_stock"]
        if cosmeticsshop:
            cosmetic_pings = [
                role.mention
                for items in cosmeticsshop
                if (role := discord.utils.get(guild.roles, name=items["display_name"]))
            ]
            cos_View = CV2.GAGStockComponent("📦Cosmetics Stock", cosmeticsshop, cosmetic_pings)
            await bot.PostCV2View(cos_View, Config.cosmeticsstock_channel_id)

        # ---- WEATHER ----
        weatherinfo = parsed["weather"]
        if weatherinfo:
            pings = []
            for w in weatherinfo:
                if not w.get("active"):
                    continue
                name = w["weather_name"]
                if name == "JoshLei":
                    continue

                weather_data = GAG.Data.get("WeatherData", {}).get(
                    name, ["No description available.", "None"]
                )
                description_text = weather_data[0] or "No description available."
                mutation_text = weather_data[1] if weather_data[1] != "None" else "None"
                img = weather_data[2] if len(weather_data) > 2 else None

                role = discord.utils.get(guild.roles, name=name)
                if role:
                    pings.append(role.mention)

                description = f"{description_text}\n**MUTATIONS:** {mutation_text}"
                await bot.PostStock(name, description, Config.weatherupdate_channel_id, pings, img)

        # ---- EVENT SHOP ----
        event_shop_stock = parsed["eventshop_stock"]
        if event_shop_stock:
            longest_name = max(len(item["display_name"]) for item in event_shop_stock)
            eventshop_format_string = "\n".join(
                f"{item['display_name'].title():<{longest_name}}   **{item['quantity']}x**"
                for item in event_shop_stock
            )
            pings = [
                role.mention
                for items in event_shop_stock
                if (role := discord.utils.get(guild.roles, name=items["display_name"]))
            ]
            await bot.PostStock("EVENT STOCK", eventshop_format_string, Config.eventshop_channel_id, pings)
