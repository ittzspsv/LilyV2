import discord


import LilyBloxFruits.core.sFruitDetectionAlgorthimEmoji as FDAE
import LilyBloxFruits.core.sFruitDetectionAlgorthim as FDA
import LilyAlgorthims.sStockProcessorAlgorthim as SPA
import LilyBloxFruits.modules.combo.LilyComboManager as LCM
import ui.sStockGenerator as SG
import Config.sBotDetails as Config
import LilyBloxFruits.core.sTradeFormatAlgorthim as TFA
from .core import sBloxFruitsCalculations as StockValueJSON
import Config.sValueConfig as LilyConfig
from Misc.sFruitImageFetcher import *
import ui.sFruitValueGenerator as FVG
import ui.sComboImageGenerator as CIG

import LilyBloxFruits.components.sBloxFruitsComponent as Components

from . import sLilyBloxFruitsCache as BFC
import ast

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

async def MessageEvaluate(bot, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if any(word in message.content.lower().split() for word in ("value",)):
                img_mode: int = 0
                if not message.channel.id == LilyConfig.guild_configs.get(message.guild.id).get("channels").get("bf_fruit_values_channel_id", 0):
                    return
                match = re.search(r"\b(?:fruit value of|value of|value)\s+(.+)", message.content.lower())
                if not match:
                    return

                item_name = match.group(1).strip()
                item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()

                fruit_set = BFC.fruit_set

                fruit_names, alias_map = await StockValueJSON.get_all_fruit_names()
                item_name = await StockValueJSON.MatchFruitSet(item_name, fruit_set, alias_map)
                item_name_capital = item_name.title() if item_name else ""

                jsonfruitdata = await StockValueJSON.fetch_fruit_details(item_name)
                if not isinstance(jsonfruitdata, dict):
                    await message.delete()
                    return

                overload_data = {
                    "fruit_name": item_name_capital or "Unknown",
                    "physical_value": jsonfruitdata.get("physical_value") or "0",
                    "permanent_value": jsonfruitdata.get("permanent_value") or "0",
                    "value": jsonfruitdata.get("physical_value") or "0",
                    "demand": jsonfruitdata.get("physical_demand") or "0",
                    "demand_type": jsonfruitdata.get("demand_type") or "..",
                    "icon_url": (
                        jsonfruitdata.get("icon_url")
                        or getattr(message.author.display_avatar, "url", None)
                    ),
                }


                if img_mode == 1:
                    status_msg = await message.reply("Thinking...")
                    img = await FVG.GenerateValueImage(overload_data)
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG", optimize=True)
                    buffer.seek(0)

                    file = discord.File(fp=buffer, filename="trade_result.png")

                    await status_msg.edit(content=None, attachments=[file])

                else:
                    embed = discord.Embed(title=item_name_capital,
                      colour=0xffffff)

                    embed.set_author(name="Item Value Calculator")

                    if jsonfruitdata.get('physical_value'):
                        embed.add_field(
                            name="Physical Value",
                            value=format_currency(jsonfruitdata['physical_value']),
                            inline=False
                        )

                    if jsonfruitdata.get('permanent_value'):
                        embed.add_field(
                            name="Permanent Value",
                            value=format_currency(jsonfruitdata['permanent_value']),
                            inline=False
                        )

                    if jsonfruitdata.get('physical_demand'):
                        embed.add_field(
                            name="Demand",
                            value=jsonfruitdata['physical_demand'],
                            inline=False
                        )

                    if jsonfruitdata.get('demand_type'):
                        embed.add_field(
                            name="Demand Type",
                            value=jsonfruitdata['demand_type'],
                            inline=False
                        )

                    if jsonfruitdata.get("icon_url"):
                        embed.set_thumbnail(url=jsonfruitdata['icon_url'])

                    embed.set_footer(text="Powered By LilyValues")

                    await message.reply(content=None, embed=embed)

        elif await TFA.is_valid_trade_format(message.content.lower()):
            if not message.channel.id == LilyConfig.guild_configs.get(message.guild.id).get("channels").get("bf_win_loss_channel_id", 0):
                return

            img_mode: int = 0     
            your_fruits = []
            your_fruit_types=[]
            their_fruits = []
            their_fruits_types=[]
            your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDA.extract_trade_details(message.content)

            if img_mode == 1:
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
                embed = discord.Embed(description=f"## {data['TradeConclusion']}",
                    colour=16777215)

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
                embed.set_image(url=Config.img.get("border"))
                await message.reply(content=None, embed=embed)

        elif await TFA.is_valid_emoji_trade_format(message.content):
            if not message.channel.id == LilyConfig.guild_configs.get(message.guild.id).get("channels").get("bf_win_loss_channel_id", 0):
                return
            img_mode: int = 0
            your_fruits = []
            your_fruit_types=[]
            their_fruits = []
            their_fruits_types=[]
            your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDAE.extract_fruits_emoji(message.content)

            if img_mode == 1: 
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

                embed = discord.Embed(description=f"## {data['TradeConclusion']}", colour=16777215)

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
                embed.set_image(url=Config.img.get("border"))

                await message.reply(content=None, embed=embed)

        elif await TFA.is_valid_trade_suggestor_format(message.content.lower()):
            if not message.channel.id == LilyConfig.guild_configs.get(message.guild.id).get("channels").get("bf_win_loss_channel_id", 0):
                return
            img_mode: int = 0
            
            msg = re.sub(r"(for\b.*?\b)nlf\b", r"\1", message.content.lower())
            your_fruits1, your_fruit_types1, neglect_fruits, _ = await FDA.extract_trade_details(msg)
            
            view = Components.TradeSuggestorComponent(bot, your_fruits1, your_fruit_types1, message, neglect_fruits, img_mode)
            await message.reply(view=view)

        elif await TFA.is_valid_trade_suggestor_format_emoji(message.content):
            if not message.channel.id == LilyConfig.guild_configs.get(message.guild.id).get("channels").get("bf_win_loss_channel_id", 0):
                return
            
            img_mode: int = 0
            your_fruits1, your_fruit_types1, _, _ = await FDAE.extract_fruits_emoji(message.content)
        
            
            view = Components.TradeSuggestorComponent(bot, your_fruits1, your_fruit_types1, message, img_mode)
            await message.reply(view=view)

        elif LCM.ComboScope(message.content.lower()) is not None:
            if not message.channel.id == LilyConfig.guild_configs.get(message.guild.id).get("channels").get("bf_combo_channel_id", 0):
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
                        view = Components.RatingComponent(message.author, combo['combo_id'])
                        await message.reply(file=imgfile, view=view)
                except Exception as e:
                    await message.reply(f"Exception: {e}")    
