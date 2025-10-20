import Misc.sLilyComponentV2 as CV2
import Config.sBotDetails as Config
import LilyAlgorthims.sStockProcessorAlgorthim as SPA
import discord
import Config.sValueConfig as VC
import aiohttp

DEFAULT_ICON_URL = "https://static.wikia.nocookie.net/plants-vs-brainro-ts/images/4/47/Placeholder.png"

async def build_stock(items: dict, category: str):
        stock = []
        pings = []
        for name, qty in items.items():
            cursor = await VC.vdb.execute(
                "SELECT icon_url, rarity FROM PVB_ItemData WHERE name = ? AND category = ?",
                (name, category)
            )
            row = await cursor.fetchone()
            icon_url = row[0] if row and row[0] else DEFAULT_ICON_URL
            rarity = row[1] if row and row[1] else "Unknown"

            if rarity.title() in ['Mythic', 'Godly', 'Secret']:
                pings.append(rarity)

            stock.append({
                "display_name": name,
                "quantity": qty,
                "icon": icon_url,
                "rarity" : rarity
            })

        return stock, pings

async def MessageEvaluate(self, bot, message):
    if message.guild and message.guild.id == Config.stock_fetch_guild_id and message.channel.id == Config.stock_fetch_channel_id_pvb:
        msg = await message.channel.fetch_message(message.id)
        if msg.embeds:
            embed = msg.embeds[0]
            parsed = SPA.StockMessageProcessorPVB(embed)

            stock_name = "PVB Stocks"
            sections = parsed.get("sections", {})

            seeds = sections.get("Seeds", {})
            gears = sections.get("Gear", {})

            seed_stock, seed_pings = await build_stock(seeds, "seed")
            gear_stock, gear_pings = await build_stock(gears, "Gear")

            if seed_stock or gear_stock:
                if seed_stock:
                    seed_embed = CV2.PVBStockComponent(stock_name, seed_stock)
                else:
                    seed_embed = None

                if gear_stock:
                    gear_embed = CV2.PVBStockComponent(stock_name, gear_stock)
                else:
                    gear_embed = None

                cursor = await VC.cdb.execute(
                    "SELECT pvb_stock_webhook, mythical_ping, godly_ping, secret_ping FROM PVB_StockHandler WHERE pvb_stock_webhook IS NOT NULL"
                )
                rows = await cursor.fetchall()

                async with aiohttp.ClientSession() as session:
                    for webhook_url, mythical_ping, godly_ping, secret_ping in rows:
                        ping_builder = ""
                        mythical_ping = mythical_ping or 0
                        godly_ping = godly_ping or 0
                        secret_ping = secret_ping or 0

                        if 'Mythic' in seed_pings:
                            ping_builder += f'<@&{mythical_ping}>'
                        if 'Godly' in seed_pings:
                            ping_builder += f'<@&{godly_ping}>'
                        if 'Secret' in seed_pings:
                            ping_builder += f'<@&{secret_ping}>'

                        ping_builder = ping_builder.strip()

                        try:
                            webhook = discord.Webhook.from_url(webhook_url, session=session)

                            if seed_embed:
                                await webhook.send(
                                    view=seed_embed,
                                    file=discord.File("src/ui/Border.png", filename="border.png"),
                                )

                            if gear_embed:
                                await webhook.send(
                                    view=gear_embed,
                                    file=discord.File("src/ui/Border.png", filename="border.png"),
                                )

                            if ping_builder:
                                await webhook.send(content=ping_builder)

                        except Exception as e:
                            print(e)
                            continue