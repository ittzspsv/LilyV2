import discord


import LilyAlgorthims.sFruitDetectionAlgorthimEmoji as FDAE
import LilyAlgorthims.sFruitDetectionAlgorthim as FDA
import LilyAlgorthims.sFruitSuggestorAlgorthim as FSA
import LilyAlgorthims.sStockProcessorAlgorthim as SPA
import Combo.LilyComboManager as LCM
import Config.sBotDetails as Config
import LilyAlgorthims.sTradeFormatAlgorthim as TFA
from Stock.sCurrentStock import *
import Values.sStockValueJSON as StockValueJSON
from Misc.sFruitImageFetcher import *
import ui.sComboImageGenerator as CIG

import re
import json
import asyncio
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

fruit_names = sorted([fruit["name"].lower() for fruit in StockValueJSON.value_data], key=len, reverse=True)
fruit_set = set(fruit_names)


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
                    their_fruits, their_types, success = FSA.trade_suggestor(
                        self.your_fruits, self.your_types,
                        self.include_permanent,
                        self.include_gamepass
                    )

                    if success:
                        image = await asyncio.to_thread(
                            StockValueJSON.j_LorW,
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
        if message.guild.id == 1240215331071594536 and message.channel.id == 1362321135231959112:
            message_id = message.id 
            source_channel = bot.get_channel(1362321135231959112)

            if source_channel is None:
                return

            try:
                fetched_message = await source_channel.fetch_message(message_id)
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

            processed_fruits = ""
            CurrentGoodFruits = []
            stock_counter = 1

            for keys, values in Fruit_Items.items():
                SubEntry_emoji = emoji_data["SubEntries"][0] if stock_counter == 1 else emoji_data["SubEntries"][1]
                processed_fruits += f"\n{SubEntry_emoji}{emoji_data[keys][0]} **{keys}** {emoji_data['beli'][0]} {values:,}"

                if "normal" in title.lower():
                    if keys in good_fruits:
                        CurrentGoodFruits.append(keys)
                else:
                    if keys in m_good_fruits:
                        CurrentGoodFruits.append(keys)

                stock_counter += 1

            stock_embed = discord.Embed(
                title=Title.upper(),
                description=f"{processed_fruits}",
                colour=0x4900f5
            )
            stock_embed.set_author(name=f"{Config.bot_name.title()} Stock", icon_url=Config.bot_icon_link_url)

            stock_embed.add_field(
                name="",
                value=f"[{Config.server_name}]({Config.server_invite_link})",
                inline=False
            )

            if "normal" in Title.lower():
                stock_embed.set_thumbnail(url="https://static.wikia.nocookie.net/roblox-blox-piece/images/b/b6/BloxFruitDealer.png")
            else:
                stock_embed.set_thumbnail(url="https://static.wikia.nocookie.net/roblox-blox-piece/images/0/0d/Advanced_Blox_Fruit_Dealer%282%29.png")

            for guild in bot.guilds:
                try:
                    channel_data = Config.load_channel_config(None, guild.id, 1)

                    if "stock_update_channel_id" not in channel_data:
                        continue

                    stock_update_channel_id = channel_data["stock_update_channel_id"]
                    stock_update_channel = bot.get_channel(stock_update_channel_id)

                    if stock_update_channel is None:
                        continue

                    stock_message = await stock_update_channel.send(embed=stock_embed)
                    await stock_message.add_reaction("🇼")
                    await stock_message.add_reaction("🇱")

                    if CurrentGoodFruits:
                        await stock_update_channel.send(
                            f"<@&{Config.stock_ping_role_id}> {', '.join(CurrentGoodFruits)} is in {Title}. Make sure to buy them!"
                        )

                except Exception as e:
                    print(f"Error posting stock to guild {guild.id}: {e}")        

        elif re.search(r"\b(fruit value of|value of|value)\b", message.content.lower()):
            ctx = await bot.get_context(message)
            channel_data = Config.load_channel_config(ctx)
            if "fruit_values_channel_id" in channel_data:
                fruit_values_channel_sid = channel_data["fruit_values_channel_id"]
            else:
                return
            fChannel = self.get_channel(fruit_values_channel_sid)
            if message.channel == fChannel:
                match = re.search(r"\b(?:fruit value of|value of|value)\s+(.+)", message.content.lower())
                if match:
                        item_name = match.group(1).strip()
                        item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()
                        item_name = StockValueJSON.MatchFruitSet(item_name, fruit_names)
                        item_name_capital = item_name.title() if item_name else ""
                        jsonfruitdata = StockValueJSON.fetch_fruit_details(item_name)
                        if isinstance(jsonfruitdata, dict):
                            fruit_img_link = FetchFruitImage(item_name_capital)
                            #await message.channel.send(f"> # {item_name.title()}\n> - **Physical Value**: {jsonfruitdata['physical_value']} \n> - **Physical Demand**: {jsonfruitdata['physical_demand']} \n> - **Physical DemandType **: {jsonfruitdata['demand_type']} \n> - **Permanent Value**: {jsonfruitdata['permanent_value']} \n> - **Permanent Demand**: {jsonfruitdata['permanent_demand']} \n> - **Permanent Demand Type**: {jsonfruitdata['permanent_demand_type']}")
                            embed = discord.Embed(title=f"{item_name.title()}",
                            colour=Config.embed_color_codes[jsonfruitdata['category']])

                            embed.set_author(name=Config.bot_name,
                            icon_url=Config.bot_icon_link_url)

                            embed.add_field(name=f"{emoji_data['BulletIn'][0]}Physical Value",
                                            value=f"{emoji_data['SubEntries'][1]}{jsonfruitdata['physical_value']}",
                                            inline=False)
                            embed.add_field(name=f"{emoji_data['BulletIn'][0]}Physical Demand",
                                            value=f"{emoji_data['SubEntries'][1]}{jsonfruitdata['physical_demand']}",
                                            inline=False)
                            if jsonfruitdata.get('permanent_value'):
                                embed.add_field(name=f"{emoji_data['BulletIn'][0]}Permanent Value",
                                                value=f"{emoji_data['SubEntries'][1]}{jsonfruitdata['permanent_value']}",
                                                inline=False)
                            if jsonfruitdata.get('permanent_demand'):
                                embed.add_field(name=f"{emoji_data['BulletIn'][0]}Permanent Demand",
                                                value=f"{emoji_data['SubEntries'][1]}{jsonfruitdata['permanent_demand']}",
                                                inline=False)
                            embed.add_field(name=f"{emoji_data['BulletIn'][0]}Demand Type",
                                            value=f"{emoji_data['SubEntries'][1]}{jsonfruitdata['demand_type']}",
                                            inline=False)
                            if Config.fruit_value_embed_type == 0:
                                embed.set_image(url=fruit_img_link)
                            else:
                                embed.set_thumbnail(url=fruit_img_link)

                            embed.add_field(name="",
                            value=f"[{Config.server_name}]({Config.server_invite_link})",
                            inline=False)

                            await message.reply(embed=embed)                    

                else:
                    message.delete()

        elif TFA.is_valid_trade_format(message.content.lower(), fruit_names): 
            lowered_message = message.content.lower()
            match = TFA.is_valid_trade_format(lowered_message, fruit_names)
            if match:
                your_fruits = []
                your_fruit_types=[]
                their_fruits = []
                their_fruits_types=[]
                your_fruits, your_fruit_types, their_fruits, their_fruits_types = FDA.extract_trade_details(message.content)
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
                    channel_data = Config.load_channel_config(ctx)
                    if "w_or_l_channel_id" in channel_data:
                            w_or_l_channel_sid = channel_data["w_or_l_channel_id"]
                    else:
                        return
                    w_or_l_channel = self.get_channel(w_or_l_channel_sid)
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

                        image = await asyncio.to_thread(
                            StockValueJSON.j_LorW,
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

        elif FDAE.is_valid_trade_sequence(message.content, emoji_id_to_name):   
            your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess = FDAE.extract_fruit_trade(message.content, emoji_id_to_name)
            with open("src/Values/valueconfig.logs", "r") as fileptr:
                    Type = int(fileptr.read().strip())

            if Type == 0:
                output_dict = StockValueJSON.j_LorW(your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess)
                
                if(isinstance(output_dict, dict)):
                    percentage_calculation = StockValueJSON.calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                    
                    embed = discord.Embed(title=output_dict["TradeConclusion"],description=output_dict["TradeDescription"],color=output_dict["ColorKey"])

                    embed.set_author(name=Config.bot_name, icon_url=Config.bot_icon_link_url)

                    your_fruit_values = [
                        f"- {emoji_data[your_fruit_typess[i].title()][0]} {emoji_data[your_fruitss[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_IndividualValues'][i])}**"
                        for i in range(min(len(your_fruit_typess), len(your_fruitss), len(output_dict["Your_IndividualValues"])))
                    ]

                    their_fruit_values = [
                        f"- {emoji_data[their_fruits_typess[i].title()][0]} {emoji_data[their_fruitss[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_IndividualValues'][i])}**"
                        for i in range(min(len(their_fruits_typess), len(their_fruitss), len(output_dict["Their_IndividualValues"])))
                    ]

                    embed.add_field(
                        name="**Your Fruits & Values**",
                        value="\n".join(your_fruit_values) if your_fruit_values else "*No fruits offered*",
                        inline=True
                    )

                    embed.add_field(
                        name="**Their Fruits & Values**",
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
                            name=f"**Trade Balance:** {percentage_calculation}",
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
                            _w_or_l_channel_sid = channel_data["w_or_l_channel_id"]
                    else:
                        return
                    _w_or_l_channel = self.get_channel(_w_or_l_channel_sid)
                    if message.channel == _w_or_l_channel:
                        await message.reply(embed=embed) 

            else:
                    ctx = await bot.get_context(message)
                    channel_data = Config.load_channel_config(ctx)
                    if "w_or_l_channel_id" in channel_data:
                        _w_or_l_channel_sid = channel_data["w_or_l_channel_id"]
                    else:
                        return
                    w_or_l_channel = self.get_channel(_w_or_l_channel_sid)
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

                        image = await asyncio.to_thread(
                            StockValueJSON.j_LorW,
                            your_fruitss, your_fruit_typess,
                            their_fruitss, their_fruits_typess,
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

        elif TFA.is_valid_trade_suggestor_format(message.content.lower(), fruit_names): 
            your_fruits1, your_fruit_types1, garbage_type, garbage_type1 = FDA.extract_trade_details(message.content)
            ctx = await bot.get_context(message)
            channel_data = Config.load_channel_config(ctx)
            _w_or_l_channel_sid = channel_data["w_or_l_channel_id"]
            if message.channel == self.get_channel(_w_or_l_channel_sid):
                view = TradeSuggestorWindow(bot=self,user=message.author,your_fruits=your_fruits1,your_types=your_fruit_types1)

                embed = discord.Embed(title="Trade Suggestion Configuration",description="",color=discord.Color.red())
                
                embed.add_field(name="• Customize your Suggestor Settings, Then Click Suggest", value="")

                await message.reply(embed=embed, view=view)

        elif FDAE.is_valid_trade_suggestor_sequence(message.content):
            your_fruits1, your_fruit_types1, their_fruits1, their_fruits_types1 = FDAE.extract_fruit_trade(message.content, emoji_id_to_name)
            ctx = await bot.get_context(message)
            channel_data = Config.load_channel_config(ctx)
            _w_or_l_channel_sid = channel_data["w_or_l_channel_id"]
            if message.channel == self.get_channel(_w_or_l_channel_sid):
                view = TradeSuggestorWindow(bot=self,user=message.author,your_fruits=your_fruits1,your_types=your_fruit_types1)

                embed = discord.Embed(title="Trade Suggestion Configuration",description="",color=discord.Color.red())
                
                embed.add_field(name="• Customize your Suggestor Settings, Then Click Suggest", value="")

                await message.reply(embed=embed, view=view)

        elif LCM.ComboScope(message.content.lower()) != None:
                    try:
                        ctx = await bot.get_context(message)
                        channel_config = Config.load_channel_config(ctx)
                        combo_channel_id = channel_config['combo_channel_id']
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