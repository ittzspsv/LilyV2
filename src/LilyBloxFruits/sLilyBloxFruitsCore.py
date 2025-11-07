import discord

import Config.sValueConfig as VC
import LilyAlgorthims.sFruitDetectionAlgorthimEmoji as FDAE
import LilyAlgorthims.sFruitDetectionAlgorthim as FDA
import LilyAlgorthims.sFruitSuggestorAlgorthim as FSA
import LilyAlgorthims.sStockProcessorAlgorthim as SPA
import Combo.LilyComboManager as LCM
import ui.sStockGenerator as SG
import Config.sBotDetails as Config
import LilyAlgorthims.sTradeFormatAlgorthim as TFA
from Stock.sCurrentStock import *
import Values.sStockValueJSON as StockValueJSON
import Config.sValueConfig as LilyConfig
from Misc.sFruitImageFetcher import *
import Misc.sLilyComponentV2 as CV2
import ui.sFruitValueGenerator as FVG
import ui.sComboImageGenerator as CIG
import aiohttp

import re
import json
import io
import ast

async def MessageEvaluate(self, bot, message):
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
            try:
                ctx = await bot.get_context(message)
                cursor = await LilyConfig.cdb.execute(
                    "SELECT bf_fruit_value_channel_id FROM ConfigData WHERE guild_id = ?", 
                    (ctx.guild.id,)
                )
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return

                fChannel = self.get_channel(int(row[0]))
                if message.channel != fChannel:
                    return
                status_msg = await message.reply("Thinking...")
                match = re.search(r"\b(?:fruit value of|value of|value)\s+(.+)", message.content.lower())
                if not match:
                    await message.delete()
                    return

                item_name = match.group(1).strip()
                item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()

                cursor = await VC.vdb.execute("SELECT name FROM BF_ItemValues")
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
                    "demand_type": jsonfruitdata['demand_type']
                }

                img = await FVG.GenerateValueImage(overload_data)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG", optimize=True)
                buffer.seek(0)

                file = discord.File(fp=buffer, filename="trade_result.png")

                await status_msg.edit(content=None, attachments=[file])

            except Exception as e:
                print(e)
                try:
                    await status_msg.delete()
                except:
                    pass

        elif await TFA.is_valid_trade_format(message.content.lower()): 
                    your_fruits = []
                    your_fruit_types=[]
                    their_fruits = []
                    their_fruits_types=[]
                    your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDA.extract_trade_details(message.content)

                    ctx = await bot.get_context(message)
                    cursor = await LilyConfig.cdb.execute("SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,))
                    row = await cursor.fetchone()
                    if row and row[0]:
                        w_or_l_channel = self.get_channel(row[0])
                    else:
                        return
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

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

        elif await TFA.is_valid_emoji_trade_format(message.content):
                    your_fruits = []
                    your_fruit_types=[]
                    their_fruits = []
                    their_fruits_types=[]
                    your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDAE.extract_fruits_emoji(message.content)


                    ctx = await bot.get_context(message)
                    cursor = await LilyConfig.cdb.execute("SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,))
                    row = await cursor.fetchone()
                    if row and row[0]:
                        w_or_l_channel = self.get_channel(row[0])
                    else:
                        return
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

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

        elif await TFA.is_valid_trade_suggestor_format(message.content.lower()):
            your_fruits1, your_fruit_types1, _, _ = await FDA.extract_trade_details(message.content)
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
            
            _w_or_l_channel = self.get_channel(row[0])
            if not _w_or_l_channel:
                return
            
            
            if message.channel != _w_or_l_channel:
                return
            
            
            view = CV2.TradeSuggestorComponent(bot, your_fruits1, your_fruit_types1, message)
            await message.reply(view=view)

        elif LCM.ComboScope(message.content.lower()) != None:
                    try:
                        ctx = await bot.get_context(message)
                        channel_config = Config.load_channel_config(ctx)
                        combo_channel_id = channel_config.get('combo_channel_id', 0)
                    except:
                        combo_channel_id = 0
                    if not message.channel.id == combo_channel_id:
                        return
                    message_refined = " ".join(line.strip() for line in message.content.splitlines() if line.strip())
                    message_refined = message_refined.lower()
                    result = LCM.ComboScope(message_refined)
                    parsed_build, combo_data = LCM.ComboPatternParser(message_refined)
                    data = (parsed_build, combo_data)

                    if result == 'Suggesting':
                        if LCM.ValidComboDataType(data):
                            cid = LCM.RegisterCombo(str(message.author.id), parsed_build, combo_data)
                            combo = LCM.ComboLookupByID(cid)

                            id = combo['id']
                            user_id = combo['user_id']
                            combo_data = combo['combo_data']
                            Item_List = {}
                            if combo.get("Fruit"):
                                Item_List[combo["Fruit"]] = "fruit_icons"
                            if combo.get("Sword"):
                                Item_List[combo["Sword"]] = "sword_icons"
                            if combo.get("Fighting Style"):
                                Item_List[combo["Fighting Style"]] = "fighting_styles"
                            if combo.get("Gun"):
                                Item_List[combo["Gun"]] = "gun_icons"
                            Item_Icon_List = []
                            
                            for key, value in Item_List.items():
                                if key and key.strip():
                                    imod = key.replace(" ", "_")
                                    icon = f'src/ui/{value}/{imod}.png'
                                    Item_Icon_List.append(icon)

                            combo_text = ""
                            #Parsing Combo Texts
                            for base, nested in ast.literal_eval(combo_data):
                                combo_ = " ".join(nested)
                                name_formatted = base.title()
                                combo_text += f"- **{name_formatted}: {combo_}**\n"

                            img = CIG.CreateBaseBuildIcon(Item_Icon_List)
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='PNG')
                            img_byte_arr.seek(0)

                            embeds = []
                            imgfile = discord.File(img_byte_arr, filename="image.png")
                            embed = discord.Embed(title="__BUILD__",colour=0xf5008f)

                            embed.set_author(name=f"{Config.server_name} Combos")
                            embed.set_image(url="attachment://image.png")

                            embeds.append(embed)

                            divider_text = "<:divider:1374032878760886342>"
                            divider_texts = ""
                            for i in range(0, 22):
                                divider_texts += divider_text

                            embed = discord.Embed(title=f"__COMBO__",
                            description=combo_text,
                            colour=0xf5008f)
                            
                            embed.add_field(name="",
                                value=divider_texts,
                                inline=False)
                            
                            embed.add_field(name="",
                                value=f"Combo ID : {id} \nCombo By <@{user_id}>",
                                inline=False)
                            embed.set_footer(text='This system is still in WIP')
                            embeds.append(embed)


                            await message.reply(content=f'Success! \nHere is The Preview of your combo', file=imgfile, embeds=embeds)
                        else:
                            await message.reply("Error Paring Combo structure")

                    elif result == 'Asking':
                        try:
                            if parsed_build:
                                combo = LCM.ComboLookup(message.content.lower())
                                id = combo['id']
                                user_id = combo['user_id']
                                combo_data = combo['combo_data']
                                Item_List = {}
                                if combo.get("Fruit"):
                                    Item_List[combo["Fruit"]] = "fruit_icons"
                                if combo.get("Sword"):
                                    Item_List[combo["Sword"]] = "sword_icons"
                                if combo.get("Fighting Style"):
                                    Item_List[combo["Fighting Style"]] = "fighting_styles"
                                if combo.get("Gun"):
                                    Item_List[combo["Gun"]] = "gun_icons"
                                Item_Icon_List = []
                                
                                for key, value in Item_List.items():
                                    if key and key.strip():
                                        imod = key.replace(" ", "_")
                                        icon = f'src/ui/{value}/{imod}.png'
                                        Item_Icon_List.append(icon)

                                combo_text = ""
                                #Parsing Combo Texts
                                for base, nested in ast.literal_eval(combo_data):
                                    combo_ = " ".join(nested)
                                    name_formatted = base.title()
                                    combo_text += f"- **{name_formatted}: {combo_}**\n"

                                img = CIG.CreateBaseBuildIcon(Item_Icon_List)
                                img_byte_arr = io.BytesIO()
                                img.save(img_byte_arr, format='PNG')
                                img_byte_arr.seek(0)

                                embeds = []
                                imgfile = discord.File(img_byte_arr, filename="image.png")
                                embed = discord.Embed(title="__BUILD__",colour=0xf5008f)

                                embed.set_author(name=f"{Config.server_name} Combos")
                                embed.set_image(url="attachment://image.png")

                                embeds.append(embed)

                                divider_text = "<:divider:1374032878760886342>"
                                divider_texts = ""
                                for i in range(0, 22):
                                    divider_texts += divider_text

                                embed = discord.Embed(title=f"__COMBO__",
                                description=combo_text,
                                colour=0xf5008f)
                                
                                embed.add_field(name="",
                                    value=divider_texts,
                                    inline=False)
                                
                                embed.add_field(name="",
                                    value=f"Combo ID : {id} \nCombo By <@{user_id}>",
                                    inline=False)
                                embed.set_footer(text='This system is still in WIP')
                                embeds.append(embed)

                                await message.reply(file=imgfile, embeds=embeds)
                        except Exception as e:
                            await message.reply(f"Exception {e}")
                    else:
                        pass