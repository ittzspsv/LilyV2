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

if Config.port == 0:
    emoji_data_path = "src/EmojiData.json"
    with open(emoji_data_path, "r", encoding="utf-8") as json_file:
        emoji_data = json.load(json_file)

    emoji_id_to_name = {}
    for fruit_name, emoji_value in emoji_data.items():
        for emoji_values in emoji_value:
            match = re.search(r"<:(\w+):(\d+)>", emoji_values)
            if match:
                emoji_id_to_name[match.group(2)] = fruit_name.title()

else:
    emoji_data_path = "src/bEmojiData.json"
    with open(emoji_data_path, "r", encoding="utf-8") as json_file:
        emoji_data = json.load(json_file)

    emoji_id_to_name = {}
    for fruit_name, emoji_value in emoji_data.items():
        for emoji_values in emoji_value:
            match = re.search(r"<:(\w+):(\d+)>", emoji_values)
            if match:
                emoji_id_to_name[match.group(2)] = fruit_name.title()


class TradeSuggestorWindow(discord.ui.View):
            def __init__(self, bot, user, your_fruits, your_types):
                super().__init__(timeout=60)
                self.bot = bot
                self.user = user
                self.state = False

                self.your_fruits = your_fruits
                self.your_types = your_types

                self.include_permanent = False
                self.include_gamepass = False
                self.image_generated = False

            @discord.ui.button(label="Permanent ❎", style=discord.ButtonStyle.secondary, row=0)
            async def PermanentButton(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.user:
                    return

                self.include_permanent = not self.include_permanent
                button.label = f"Permanent {'✅' if self.include_permanent else '❎'}"
                await interaction.response.edit_message(view=self)

            @discord.ui.button(label="Gamepass ❎", style=discord.ButtonStyle.secondary, row=0)
            async def GamepassButton(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.user:
                    return

                self.include_gamepass = not self.include_gamepass
                button.label = f"Gamepass {'✅' if self.include_gamepass else '❎'}"
                await interaction.response.edit_message(view=self)

            @discord.ui.button(label="Suggest", style=discord.ButtonStyle.success, row=1)
            async def SuggestButton(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.user:
                    return

                if self.image_generated:
                    return

                await interaction.response.edit_message(embed=None, content="Reasoning.....", attachments=[], view=None)

                try:
                    their_fruits, their_types, success = await FSA.trade_suggestor(
                        self.your_fruits, self.your_types,
                        self.include_permanent,
                        self.include_gamepass
                    )

                    if success:
                        image = await StockValueJSON.j_LorW(
                            self.your_fruits, self.your_types,
                            their_fruits, their_types,
                            1, 1
                        )

                        if image is None:
                            raise ValueError("Reasoning Failure")

                        buffer = io.BytesIO()
                        image.save(buffer, format="WebP", quality=20, optimize=True)
                        buffer.seek(0)
                        file = discord.File(fp=buffer, filename="trade_result.webp")
                        await interaction.edit_original_response(embed=None, content=None, attachments=[file], view=None)
                        self.image_generated = True
                    else:
                        raise ValueError("Reasoning Failure")
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"Unhandled Exception: {str(e)}"
                    )

async def MessageEvaluate(self, bot, message):
        if message.guild and message.guild.id == Config.stock_fetch_guild_id and message.channel.id == Config.stock_fetch_channel_id:
            try:
                cursor = await LilyConfig.cdb.execute("SELECT value FROM GlobalConfigs WHERE key = 'StockImage'")
                row = await cursor.fetchone()
                use_image_mode = (row and row[0] == 1)
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

            CurrentGoodFruits = [
                key for key in Fruit_Items.keys()
                if ("normal" in Title.lower() and key in good_fruits) or (key in m_good_fruits)
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

            try:
                cursor = await LilyConfig.cdb.execute(
                    "SELECT StockPingID, bf_stock_webhook FROM BF_StockHandler WHERE bf_stock_webhook IS NOT NULL"
                )
                rows = await cursor.fetchall()
            except Exception as e:
                print(f"DB error getting ConfigData: {e}")
                return

            if not rows:
                return

            async with aiohttp.ClientSession() as session:
                for stock_ping, webhook_url in rows:
                    try:
                        webhook = discord.Webhook.from_url(webhook_url, session=session)

                        sent_msg = None
                        if use_image_mode and stock_image_bytes:
                            file = discord.File(io.BytesIO(stock_image_bytes), filename="stock_image.png")
                            sent_msg = await webhook.send(file=file, wait=True)
                        else:
                            stock_view = await CV2.BloxFruitStockComponent.create((Title, Fruit_Items))
                            file = discord.File("src/ui/Border.png", filename="border.png")
                            sent_msg = await webhook.send(file=file, view=stock_view, wait=True)

                        if sent_msg:
                            try:
                                await sent_msg.add_reaction("🇼")
                                await sent_msg.add_reaction("🇱")
                            except Exception as e:
                                pass

                        if CurrentGoodFruits and stock_ping:
                            await webhook.send(
                                content=f"<@&{stock_ping}> {', '.join(CurrentGoodFruits)} is in {Title}. Make sure to buy them!",
                                wait=True
                            )

                    except Exception as e:
                        print(f"Webhook error: {e}")
                        continue

                    except Exception as e:
                        pass

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
                try:
                    await status_msg.delete()
                except:
                    pass

        elif await TFA.is_valid_trade_format(message.content.lower()): 
            lowered_message = message.content.lower()
            match = await TFA.is_valid_trade_format(lowered_message)
            if match:
                your_fruits = []
                your_fruit_types=[]
                their_fruits = []
                their_fruits_types=[]
                your_fruits, your_fruit_types, their_fruits, their_fruits_types = await FDA.extract_trade_details(message.content)
                with open("src/Values/valueconfig.logs", "r") as fileptr:
                    Type = int(fileptr.read().strip())
                if Type == 0:
                    output_dict = StockValueJSON.j_LorW(your_fruits, your_fruit_types, their_fruits, their_fruits_types, Type)
                    #await message.channel.send(resultant)
                    if isinstance(output_dict, dict):

                        percentage_calculation = StockValueJSON.calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                    
                        embed = discord.Embed(title=output_dict["TradeConclusion"],description=output_dict["TradeDescription"],color=output_dict["ColorKey"],)
                        embed.set_author(
                            name=Config.bot_name,
                            icon_url=Config.bot_icon_link_url
                        )

                        your_fruit_values = [
                            f"- {emoji_data[your_fruit_types[i].title()][0]} {emoji_data[your_fruits[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_IndividualValues'][i])}**"
                            for i in range(min(len(your_fruit_types), len(your_fruits), len(output_dict["Your_IndividualValues"])))
                        ]

                        their_fruit_values = [
                            f"- {emoji_data[their_fruits_types[i].title()][0]} {emoji_data[their_fruits[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_IndividualValues'][i])}**"
                            for i in range(min(len(their_fruits_types), len(their_fruits), len(output_dict["Their_IndividualValues"])))
                        ]

                        embed.add_field(
                            name="**Your Offered Fruits**",
                            value=" \n".join(your_fruit_values) if your_fruit_values else "*No fruits offered*",
                            inline=True
                        )

                        embed.add_field(
                            name="**Their Offered Fruits**",
                            value="\n".join(their_fruit_values) if their_fruit_values else "*No fruits offered*",
                            inline=True
                        )

                        embed.add_field(
                            name="**Your Total Value:**",
                            value=f"{emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_TotalValue'])}**" if output_dict['Your_TotalValue'] else "*No values available*",
                            inline=False
                        )

                        embed.add_field(
                            name="**Their Total Value:**",
                            value=f"{emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_TotalValue'])}**" if output_dict['Their_TotalValue'] else "*No values available*",
                            inline=False
                        )

                        if percentage_calculation != "Invalid input. Please enter numerical values.":
                            embed.add_field(
                                name=f"{percentage_calculation}",
                                value="",
                                inline=False
                            )

                        embed.add_field(
                            name="",
                            value=f"[{Config.server_name}]({Config.server_invite_link})",
                            inline=False
                        )
                        ctx = await bot.get_context(message)
                        channel_data = Config.load_channel_config(ctx)
                        if "w_or_l_channel_id" in channel_data:
                            w_or_l_channel_sid = channel_data["w_or_l_channel_id"]
                        else:
                            return

                        w_or_l_channel = self.get_channel(w_or_l_channel_sid)
                        if message.channel == w_or_l_channel:
                            await message.reply(embed=embed)

                else:
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
                            Type
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
            your_fruits1, your_fruit_types1, garbage_type, garbage_type1 = await FDA.extract_trade_details(message.content)
            ctx = await bot.get_context(message)
            cursor = await LilyConfig.cdb.execute("SELECT bf_win_loss_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,))
            row = await cursor.fetchone()
            if row and row[0]:
                        _w_or_l_channel_sid = self.get_channel(row[0])
            else:
                        return
            if message.channel == self.get_channel(_w_or_l_channel_sid):
                view = TradeSuggestorWindow(bot=self,user=message.author,your_fruits=your_fruits1,your_types=your_fruit_types1)

                embed = discord.Embed(title="Trade Suggestion Configuration",description="",color=discord.Color.red())
                
                embed.add_field(name="• Customize your Suggestor Settings, Then Click Suggest", value="")

                await message.reply(embed=embed, view=view)

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