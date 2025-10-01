import Misc.sLilyComponentV2 as CV2
import Config.sBotDetails as Config
import LilyAlgorthims.sStockProcessorAlgorthim as SPA
import discord
import Config.sValueConfig as VC


DEFAULT_ICON_URL = "https://static.wikia.nocookie.net/plants-vs-brainro-ts/images/4/47/Placeholder.png"

async def build_stock(items: dict, category: str, guild: discord.Guild):
    stock = []
    pings = []
    for name, qty in items.items():
        cursor = await VC.vdb.execute(
            "SELECT icon_url FROM PVB_ItemData WHERE name = ? AND category = ?",
            (name, category)
        )
        row = await cursor.fetchone()
        icon_url = row[0] if row and row[0] else DEFAULT_ICON_URL

        stock.append({
            "display_name": name,
            "quantity": qty,
            "icon": icon_url
        })

        role = discord.utils.get(guild.roles, name=name.title())
        if role:
            pings.append(role.mention)

    return stock, pings

async def MessageEvaluate(self, bot, message):
    if message.guild and message.guild.id == Config.stock_fetch_guild_id and message.channel.id == Config.stock_fetch_channel_id_pvb:
        if message.embeds:
            embed = message.embeds[0]
            parsed = SPA.StockMessageProcessorPVB(embed)

            stock_name = "PVB Stocks"
            sections = parsed.get("sections", {})

            seeds = sections.get("Seeds", {})
            gears = sections.get("Gear", {})

            guild = message.guild

            seed_stock, seed_pings = await build_stock(seeds, "seed", guild)
            gear_stock, gear_pings = await build_stock(gears, "Gear", guild)

            seed_view = CV2.GAGStockComponent(stock_name, seed_stock, seed_pings)
            gear_view = CV2.GAGStockComponent(stock_name, gear_stock, gear_pings)

            cursor = await VC.cdb.execute(
                "SELECT guild_id, pvb_stock_channel_id FROM ConfigData WHERE pvb_stock_channel_id IS NOT NULL"
            )
            rows = await cursor.fetchall()

            for guild_id, channel_id in rows:
                guild = VC.bot.get_guild(int(guild_id))
                if guild is None:
                    continue

                channel = guild.get_channel(int(channel_id))
                if channel is None:
                    continue

                try:
                    await channel.send(
                        view=seed_view,
                        file=discord.File("src/ui/Border.png", filename="border.png")
                    )
                    await channel.send(
                        view=gear_view,
                        file=discord.File("src/ui/Border.png", filename="border.png")
                    )
                except discord.Forbidden:
                    print(f"Missing permission to send messages in {guild.name} ({channel_id})")
                except discord.HTTPException as e:
                    print(f"Failed to send message in {guild.name}: {e}")