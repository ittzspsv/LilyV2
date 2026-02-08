import discord


import LilyAlgorthims.sFruitDetectionAlgorthimEmoji as FDAE
import LilyAlgorthims.sFruitDetectionAlgorthim as FDA
import LilyAlgorthims.sStockProcessorAlgorthim as SPA
import Combo.LilyComboManager as LCM
import ui.sStockGenerator as SG
import Config.sBotDetails as Config
import LilyAlgorthims.sTradeFormatAlgorthim as TFA
import Values.sStockValueJSON as StockValueJSON
import Config.sValueConfig as LilyConfig
from Misc.sFruitImageFetcher import *
import Misc.sLilyComponentV2 as CV2
import ui.sFruitValueGenerator as FVG
import ui.sComboImageGenerator as CIG
import ast
import aiohttp

import re
import io


def format_currency(val):
    value = int(val)
    if value >= 1_000_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000_000:.1f}DX"
    elif value >= 1_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000:.1f}NX"
    elif value >= 1_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000:.1f}OX"
    elif value >= 1_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000:.1f}SPX"
    elif value >= 1_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000:.1f}SX"
    elif value >= 1_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000:.1f}QI"
    elif value >= 1_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000:.1f}QT"
    elif value >= 1_000_000_000_000: 
        return f"{value / 1_000_000_000_000:.1f}T"
    elif value >= 1_000_000_000:  
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:  
        return f"{value / 1_000:.1f}k"
    else:
        return str(int(value))


async def MessageEvaluate(bot, message):
        if message.guild and message.guild.id == Config.stock_fetch_guild_id and message.channel.id == Config.stock_fetch_channel_id:
            try:
                cursor = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key = 'StockImage'")
                row = await cursor.fetchone()
                use_image_mode = (row and int(row[0]) == 1)
            except Exception as e:
                print(f"DB error reading GlobalConfig: {e}")
                use_image_mode = False

            try:
                source_channel = bot.get_channel(Config.stock_fetch_channel_id)
                if source_channel is None:
                    return

                fetched_message = await source_channel.fetch_message(message.id)
                if not fetched_message.embeds:
                    return
            except Exception as e:
                print(f"Failed to fetch message: {e}")
                return

            embeded_string = ""
            for embed in fetched_message.embeds:
                title = embed.title or "-"
                description = embed.description or "-"
                embeded_string += f"Title: {title} Description: {description}"

            Title, Fruit_Items = SPA.StockMessageProcessor(embeded_string)

            async with LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key = 'BF_Normal_GoodFruits'") as cursor:
                row = await cursor.fetchone()
                good_fruits = [fruit.strip() for fruit in row[0].split(",")] if row and row[0] else []

            async with LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key = 'BF_Mirage_GoodFruits'") as cursor:
                row = await cursor.fetchone()
                m_good_fruits = [fruit.strip() for fruit in row[0].split(",")] if row and row[0] else []

            CurrentGoodFruits = [
                key for key in Fruit_Items.keys()
                if ("normal" in Title.lower() and key in good_fruits)
                or ("mirage" in Title.lower() and key in m_good_fruits)
            ]

            stock_image_bytes = None
            if use_image_mode:
                try:
                    img = SG.StockImageGenerator(Fruit_Items, Title.lower())
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    stock_image_bytes = buffer.getvalue()
                except Exception as e:
                    print(f"Error generating stock image: {e}")
                    return
            else:
                try:
                    stock_view = await CV2.BloxFruitStockComponent.create((Title, Fruit_Items))
                except Exception as e:
                    return

            try:
                cursor = await LilyConfig.cdb.execute(
                    "SELECT StockPingID, bf_stock_webhook, rowid FROM BF_StockHandler WHERE bf_stock_webhook IS NOT NULL"
                )
                rows = await cursor.fetchall()
            except Exception as e:
                print(f"DB error getting ConfigData: {e}")
                return

            if not rows:
                return

            async with aiohttp.ClientSession() as session:
                for stock_ping, webhook_url, rowid in rows:
                    try:
                        webhook = discord.Webhook.from_url(webhook_url, session=session)

                        if use_image_mode and stock_image_bytes:
                            file = discord.File(io.BytesIO(stock_image_bytes), filename="stock_image.png")
                            await webhook.send(file=file, wait=True)
                        else:
                            
                            file = discord.File("src/ui/Border.png", filename="border.png")
                            await webhook.send(file=file, view=stock_view, wait=True)

                        if CurrentGoodFruits and stock_ping:
                            await webhook.send(
                                content=f"<@&{stock_ping}> {', '.join(CurrentGoodFruits)} is in {Title}. Make sure to buy them!",
                                wait=True
                            )

                    except discord.NotFound:
                        try:
                            await LilyConfig.cdb.execute(
                                "DELETE FROM BF_StockHandler WHERE rowid = ?", (rowid,)
                            )
                            await LilyConfig.cdb.commit()
                        except Exception as db_err:
                            print(f"Error deleting invalid webhook: {db_err}")

                    except Exception as e:
                        print(f"Webhook error: {e}")
                        continue

        if re.search(r"\b(fruit value of|value of|value)\b", message.content.lower()):
            cursor1 = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key IN ('WORLImage', 'FruitValuesImage')")
            crow = await cursor1.fetchall()
            config_rows = (crow[0][0], crow[1][0])
            try:
                ctx = await bot.get_context(message)
                cursor = await LilyConfig.cdb.execute(
                    "SELECT bf_fruit_value_channel_id FROM ConfigData WHERE guild_id = ?", 
                    (ctx.guild.id,)
                )
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return

                fChannel = bot.get_channel(int(row[0]))
                if message.channel != fChannel:
                    return
                status_msg = await message.reply("Thinking...")
                match = re.search(r"\b(?:fruit value of|value of|value)\s+(.+)", message.content.lower())
                if not match:
                    await message.delete()
                    return

                item_name = match.group(1).strip()
                item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()

                cursor = await LilyConfig.vdb.execute("SELECT name FROM BF_ItemValues")
                rows = await cursor.fetchall()
                fruit_names = [row[0].lower() for row in rows]
                fruit_names = sorted(fruit_names, key=len, reverse=True)
                fruit_set = set(fruit_names)

                fruit_names, alias_map = await StockValueJSON.get_all_fruit_names()
                item_name = await StockValueJSON.MatchFruitSet(item_name, fruit_set, alias_map)
                item_name_capital = item_name.title() if item_name else ""

                jsonfruitdata = await StockValueJSON.fetch_fruit_details(item_name)
                if not isinstance(jsonfruitdata, dict):
                    await message.delete()
                    return

                overload_data = {
                    "fruit_name": item_name_capital,
                    "physical_value": jsonfruitdata['physical_value'],
                    "permanent_value": jsonfruitdata['permanent_value'],
                    "value": jsonfruitdata['physical_value'],
                    "demand": jsonfruitdata['physical_demand'],
                    "demand_type": jsonfruitdata['demand_type'],
                    "icon_url" : jsonfruitdata['icon_url']
                }

                if int(config_rows[1]) == 1:
                    img = await FVG.GenerateValueImage(overload_data)
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG", optimize=True)
                    buffer.seek(0)

                    file = discord.File(fp=buffer, filename="trade_result.png")

                    await status_msg.edit(content=None, attachments=[file])

                else:
                    embed = discord.Embed(title=item_name_capital,
                      colour=0x1000f5)

                    embed.set_author(name="Item Value Calculator")

                    if jsonfruitdata['physical_value']:
                        embed.add_field(
                            name="Physical Value",
                            value=format_currency(jsonfruitdata['physical_value']),
                            inline=False
                        )

                    if jsonfruitdata['permanent_value']:
                        embed.add_field(
                            name="Permanent Value",
                            value=format_currency(jsonfruitdata['permanent_value']),
                            inline=False
                        )

                    if jsonfruitdata['physical_demand']:
                        embed.add_field(
                            name="Demand",
                            value=jsonfruitdata['physical_demand'],
                            inline=False
                        )

                    if jsonfruitdata['demand_type']:
                        embed.add_field(
                            name="Demand Type",
                            value=jsonfruitdata['demand_type'],
                            inline=False
                        )

                    embed.set_thumbnail(url=jsonfruitdata['icon_url'])

                    embed.set_footer(text="Powered By LilyValues")

                    await status_msg.edit(content=None, embed=embed)

            except Exception as e:
                print(e)
                try:
                    await status_msg.delete()
                except:
                    pass

        elif await TFA.is_valid_trade_format(message.content.lower()):       
                    cursor1 = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key IN ('WORLImage', 'FruitValuesImage')")
                    crow = await cursor1.fetchall()
                    config_rows = (crow[0][0], crow[1][0])         
                    your_fruits = []
                    your_fruit_types=[]
                    their_fruits = []
                    their_fruits_types=[]
                    your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDA.extract_trade_details(message.content)

                    ctx = await bot.get_context(message)
                    cursor = await LilyConfig.cdb.execute("SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,))
                    row = await cursor.fetchone()
                    if row and row[0]:
                        w_or_l_channel = bot.get_channel(row[0])
                    else:
                        return
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

                        if int(config_rows[0]) == 1:
                            image = await StockValueJSON.j_LorW(
                                your_fruits, your_fruit_types,
                                their_fruits, their_fruits_types,
                                1
                            )

                            if image is None:
                                await status_msg.edit(content="AttributeError: 'NoneType' object has no attribute 'save'")
                                return

                            buffer = io.BytesIO()
                            image.save(buffer, format="PNG", optimize=True)
                            buffer.seek(0)

                            file = discord.File(fp=buffer, filename="trade_result.png")
                            await status_msg.edit(content=None, attachments=[file])

                        else:
                            data = await StockValueJSON.j_LorW(
                                your_fruits, your_fruit_types,
                                their_fruits, their_fruits_types,
                                0
                            )

                            your_fruit_details = ""
                            their_fruit_details = ""

                            for i in range(len(your_fruits)):
                                fruit_name = your_fruits[i].replace(" ", "_").replace("-", "_").lower()
                                fruit_emoji = Config.fruit_emojis.get(fruit_name, "🍎")
                                beli_emoji = Config.emoji.get("beli", "💸")
                                perm_emoji = Config.emoji.get("perm", "🔒")

                                value = data['Your_IndividualValues'][i]
                                formatted_value = f"{value:,}"
                                if your_fruit_types[i].lower() == "permanent":
                                    your_fruit_details += f"- {perm_emoji}{fruit_emoji} {beli_emoji} {formatted_value}\n"
                                else:
                                    your_fruit_details += f"- {fruit_emoji} {beli_emoji} {formatted_value}\n"

                            for i in range(len(their_fruits)):
                                fruit_name = their_fruits[i].replace(" ", "_").replace("-", "_").lower()
                                fruit_emoji = Config.fruit_emojis.get(fruit_name, "🍎")
                                beli_emoji = Config.emoji.get("beli", "💸")
                                perm_emoji = Config.emoji.get("perm", "🔒")

                                value = data['Their_IndividualValues'][i]
                                formatted_value = f"{value:,}"
                                if their_fruits_types[i].lower() == "permanent":
                                    their_fruit_details += f"- {perm_emoji}{fruit_emoji} {beli_emoji} {formatted_value}\n"
                                else:
                                    their_fruit_details += f"- {fruit_emoji} {beli_emoji} {formatted_value}\n"
                            embed = discord.Embed(title=data['TradeConclusion'],
                                description=f"**{data['TradeDescription']}**",
                                colour=data['ColorKey'])

                            embed.set_author(name="Lily W OR L Calculator")

                            embed.add_field(name="Your Fruit Values",
                                            value=your_fruit_details,
                                            inline=True)
                            embed.add_field(name="Their Fruit Values",
                                            value=their_fruit_details,
                                            inline=True)
                            embed.add_field(name="Your Total Values:",
                                            value=format_currency(data['Your_TotalValue']),
                                            inline=False)
                            embed.add_field(name="Their Total Values:",
                                            value=format_currency(data['Their_TotalValue']),
                                            inline=False)
                            embed.add_field(name=data['Percentage'],
                                            value="",
                                            inline=False)
                            await status_msg.edit(content=None, embed=embed)

        elif await TFA.is_valid_emoji_trade_format(message.content):
                    cursor1 = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key IN ('WORLImage', 'FruitValuesImage')")
                    crow = await cursor1.fetchall()
                    config_rows = (crow[0][0], crow[1][0])
                    your_fruits = []
                    your_fruit_types=[]
                    their_fruits = []
                    their_fruits_types=[]
                    your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDAE.extract_fruits_emoji(message.content)


                    ctx = await bot.get_context(message)
                    cursor = await LilyConfig.cdb.execute("SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,))
                    row = await cursor.fetchone()
                    if row and row[0]:
                        w_or_l_channel = bot.get_channel(row[0])
                    else:
                        return
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

                        if int(config_rows[0]) == 1: 
                            image = await StockValueJSON.j_LorW(
                                your_fruits, your_fruit_types,
                                their_fruits, their_fruits_types,
                                1
                            )

                            if image is None:
                                await status_msg.edit(content="AttributeError: 'NoneType' object has no attribute 'save'")
                                return

                            buffer = io.BytesIO()
                            image.save(buffer, format="PNG", optimize=True)
                            buffer.seek(0)

                            file = discord.File(fp=buffer, filename="trade_result.png")
                            await status_msg.edit(content=None, attachments=[file])
                        else:
                            data = await StockValueJSON.j_LorW(
                                your_fruits, your_fruit_types,
                                their_fruits, their_fruits_types,
                                0
                            )

                            your_fruit_details = ""
                            their_fruit_details = ""

                            for i in range(len(your_fruits)):
                                fruit_name = your_fruits[i].replace(" ", "_").replace("-", "_").lower()
                                fruit_emoji = Config.fruit_emojis.get(fruit_name, "🍎")
                                beli_emoji = Config.emoji.get("beli", "💸")
                                perm_emoji = Config.emoji.get("perm", "🔒")

                                value = data['Your_IndividualValues'][i]
                                formatted_value = f"{value:,}"
                                your_fruit_details += f"- {fruit_emoji} {beli_emoji} {formatted_value}\n"

                            for i in range(len(their_fruits)):
                                fruit_name = their_fruits[i].replace(" ", "_").replace("-", "_").lower()
                                fruit_emoji = Config.fruit_emojis.get(fruit_name, "🍎")
                                beli_emoji = Config.emoji.get("beli", "💸")
                                perm_emoji = Config.emoji.get("perm", "🔒")

                                value = data['Their_IndividualValues'][i]
                                formatted_value = f"{value:,}"
                                their_fruit_details += f"- {fruit_emoji} {beli_emoji} {formatted_value}\n"

                            embed = discord.Embed(title=data['TradeConclusion'],
                                description=f"**{data['TradeDescription']}**",
                                colour=data['ColorKey'])

                            embed.set_author(name="Lily W OR L Calculator")

                            embed.add_field(name="Your Fruit Values",
                                            value=your_fruit_details,
                                            inline=True)
                            embed.add_field(name="Their Fruit Values",
                                            value=their_fruit_details,
                                            inline=True)
                            embed.add_field(name="Your Total Values:",
                                            value=format_currency(data['Your_TotalValue']),
                                            inline=False)
                            embed.add_field(name="Their Total Values:",
                                            value=format_currency(data['Their_TotalValue']),
                                            inline=False)
                            embed.add_field(name=data['Percentage'],
                                            value="",
                                            inline=False)
                            await status_msg.edit(content=None, embed=embed)

        elif await TFA.is_valid_trade_suggestor_format(message.content.lower()):
            cursor1 = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key IN ('WORLImage')")
            crow = await cursor1.fetchone()
            
            msg = re.sub(r"(for\b.*?\b)nlf\b", r"\1", message.content.lower())
            your_fruits1, your_fruit_types1, neglect_fruits, _ = await FDA.extract_trade_details(msg)
            ctx = await bot.get_context(message)
            if not ctx.guild:
                return
            
            cursor = await LilyConfig.cdb.execute(
                "SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?",
                (ctx.guild.id,)
            )
            row = await cursor.fetchone()
            
            if not row or not row[0]:
                return
            
            _w_or_l_channel = bot.get_channel(row[0])
            if not _w_or_l_channel:
                return
            
            
            if message.channel != _w_or_l_channel:
                return
            
            
            view = CV2.TradeSuggestorComponent(bot, your_fruits1, your_fruit_types1, message, neglect_fruits, int(crow[0]))
            await message.reply(view=view)

        elif await TFA.is_valid_trade_suggestor_format_emoji(message.content):
            cursor1 = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key IN ('WORLImage', 'FruitValuesImage')")
            crow = await cursor1.fetchall()
            config_rows = (crow[0][0], crow[1][0])
            your_fruits1, your_fruit_types1, _, _ = await FDAE.extract_fruits_emoji(message.content)

            ctx = await bot.get_context(message)
            if not ctx.guild:
                return
            
            cursor = await LilyConfig.cdb.execute(
                "SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?",
                (ctx.guild.id,)
            )
            row = await cursor.fetchone()
            
            if not row or not row[0]:
                return
            
            _w_or_l_channel = bot.get_channel(row[0])
            if not _w_or_l_channel:
                return
            
            
            if message.channel != _w_or_l_channel:
                return
            
            
            view = CV2.TradeSuggestorComponent(bot, your_fruits1, your_fruit_types1, message, config_rows[0])
            await message.reply(view=view)

        elif LCM.ComboScope(message.content.lower()) is not None:
            try:
                ctx = await bot.get_context(message)
            except Exception as e:
                return

            try:
                cursor = await LilyConfig.cdb.execute(
                    "SELECT bf_combo_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,)
                )
                row = await cursor.fetchone()
            except Exception as e:
                return

            if not row:
                return

            if message.channel.id != row[0]:
                return

            try:
                message_refined = " ".join(line.strip() for line in message.content.splitlines() if line.strip()).lower()
                result = LCM.ComboScope(message_refined)
                parsed_build, combo_data = await LCM.ComboPatternParser(message_refined)
                data = (parsed_build, combo_data)
            except Exception as e:
                await message.reply(f"Parsing failed: {e}")
                return

            if result == 'Suggesting':
                try:
                    if await LCM.ValidComboDataType(data):
                        cid = await LCM.RegisterCombo(str(message.author.id), parsed_build, combo_data)
                        combo = await LCM.ComboLookupByID(cid)

                        combo_data_text = combo.get('combo_data', '[]')
                        Item_List = {}
                        for key_type in ["fruit", "sword", "fighting_style", "gun"]:
                            if combo.get(key_type):
                                mapping = {
                                    "fruit": "fruit_icons",
                                    "sword": "sword_icons",
                                    "fighting_style": "fighting_styles",
                                    "gun": "gun_icons"
                                }
                                Item_List[combo[key_type]] = mapping[key_type]

                        Item_Icon_List = [
                            f'src/ui/{value}/{key.replace(" ", "_")}.png'
                            for key, value in Item_List.items() if key and key.strip()
                        ]

                        combo_text = ""
                        for base, nested in ast.literal_eval(combo_data_text):
                            combo_ = " ".join(nested)
                            combo_text += f"{base.title()}: {combo_}\n"

                        name_raw = message.author.name or "Unknown"
                        name = re.sub(r'[^A-Za-z ]+', '', name_raw)
                        img = CIG.CreateBaseBuildIcon(Item_Icon_List, combo_text=combo_text, rating_text=f'{combo.get("rating", "0")}/10', combo_id=str(combo['combo_id']), combo_by=name)
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)

                        imgfile = discord.File(img_byte_arr, filename="image.png")
                        await message.reply(content='Success!\nHere is the preview of your combo', file=imgfile)
                    else:
                        await message.reply("Error parsing combo structure")
                except Exception as e:
                    await message.reply(f"Unexpected error: {e}")

            elif result == 'Asking':
                try:
                    if parsed_build:
                        combo = await LCM.ComboLookup(message.content.lower())
                        if not combo:
                            await message.reply("No matching combo found.")
                            return

                        combo_data_text = combo.get('combo_data', '[]')
                        Item_List = {}
                        for key_type in ["fruit", "sword", "fighting_style", "gun"]:
                            if combo.get(key_type):
                                mapping = {
                                    "fruit": "fruit_icons",
                                    "sword": "sword_icons",
                                    "fighting_style": "fighting_styles",
                                    "gun": "gun_icons"
                                }
                                Item_List[combo[key_type]] = mapping[key_type]

                        Item_Icon_List = [
                            f'src/ui/{value}/{key.replace(" ", "_")}.png'
                            for key, value in Item_List.items() if key and key.strip()
                        ]

                        combo_text = ""
                        for base, nested in ast.literal_eval(combo_data_text):
                            combo_ = " ".join(nested)
                            combo_text += f"{base.title()}: {combo_}\n"

                        combo_author_id = combo.get("combo_author")
                        combo_by = None

                        if combo_author_id:
                            combo_by = message.guild.get_member(int(combo_author_id))
                            if combo_by is None:
                                try:
                                    combo_by = await message.guild.fetch_member(int(combo_author_id))
                                except discord.NotFound:
                                    combo_by = None

                        name_raw = combo_by.name if combo_by else "Unknown"
                        name = re.sub(r'[^A-Za-z ]+', '', name_raw)

                        img = CIG.CreateBaseBuildIcon(Item_Icon_List, combo_text=combo_text, rating_text=f"{combo.get('rating', '0')}/10", combo_id=str(combo['combo_id']), combo_by=name)
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)

                        imgfile = discord.File(img_byte_arr, filename="image.png")
                        view = CV2.RatingComponent(message.author, combo['combo_id'])
                        await message.reply(file=imgfile, view=view)
                except Exception as e:
                    await message.reply(f"Exception: {e}")
                        

                    