import discord
from Stock.sCurrentStock import *
from Values.sStockValueJSON import *
from discord.ext import commands
from Misc.sFruitImageFetcher import *
from Config.sBotDetails import *
import Algorthims.sTradeFormatAlgorthim as TFA
from datetime import datetime, timedelta
from discord import SelectOption, Interaction, ui
from enum import Enum

import Algorthims.sFruitDetectionAlgorthimEmoji as FDAE
import Algorthims.sFruitDetectionAlgorthim as FDA
import Algorthims.sFruitSuggestorAlgorthim as FSA
import Algorthims.sStockProcessorAlgorthim as SPA
import Moderation.sLilyModeration as mLily
import Vouch.sLilyVouches as vLily
import Misc.sLilyEmbed as LilyEmbed

from Values.sStockValueJSON import *

import os
import random
import asyncio
import io
import polars as pl
import json
import aiohttp

    
import re

#ACCESSING DATA FORMATS

if port == 0:
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

fruit_names = sorted([fruit["name"].lower() for fruit in value_data], key=len, reverse=True)
fruit_set = set(fruit_names)


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.message_content = True
        intents.members = True
        intents.presences = True 
        intents.guilds = True
        super().__init__(command_prefix=bot_command_prefix, intents=discord.Intents.all())

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
                            j_LorW,
                            self.your_fruits, self.your_types,
                            their_fruits, their_types,
                            1, 1
                        )

                        if image is None:
                            raise ValueError("Reasoning Failure")

                        buffer = io.BytesIO()
                        image.save(buffer, format="PNG", optimize=True)
                        buffer.seek(0)
                        file = discord.File(fp=buffer, filename="trade_result.png")
                        await interaction.edit_original_response(embed=None, content=None, attachments=[file], view=None)
                        self.image_generated = True
                    else:
                        raise ValueError("Reasoning Failure")
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"Unhandled Exception: {str(e)}"
                    )

    async def MemoryButtonSetup(self):
        if not os.path.exists(ButtonSessionMemory):
            return
        try:
            with open(ButtonSessionMemory, "r") as f:
                content = f.read().strip()
                if not content:
                    return
                all_views = json.loads(content)
        except json.JSONDecodeError as e:
            with open(ButtonSessionMemory, "w") as f:
                f.write("[]")
            return

        valid_views = []
        for view_data in all_views:
            channel_id = view_data.get("channel_id")
            message_id = view_data.get("message_id")
            buttons_data = view_data.get("buttons", [])

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue

            view = discord.ui.View(timeout=None)

            for btn_data in buttons_data:
                button = discord.ui.Button(
                    label=btn_data.get("label", "Unnamed"),
                    style=discord.ButtonStyle(btn_data.get("style", discord.ButtonStyle.secondary)),
                    custom_id=btn_data["custom_id"]
                )

                embed_dict = btn_data.get("embed")
                if not embed_dict:
                    continue

                embed = discord.Embed.from_dict(embed_dict)

                async def callback(interaction, embed=embed):
                    await interaction.response.send_message(embed=embed, ephemeral=True)

                button.callback = callback
                view.add_item(button)

            bot.add_view(view)
            valid_views.append(view_data)
        with open(ButtonSessionMemory, "w") as f:
            json.dump(valid_views, f, indent=4)

    async def on_ready(self):
        print('Logged on as', self.user)
        await self.MemoryButtonSetup()

        await self.tree.sync()

    async def send_discord_message(message):
        await bot.wait_until_ready()
        channel = bot.get_channel(stock_update_channel_id)
        
        if channel:
            await channel.send(message)
        else:
            pass

    async def WriteLog(self, user_id, log_txt):
        log_file_path = "storage/botlogs/logs.csv"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_log = pl.DataFrame({
            "user_id": [str(user_id)],
            "timestamp": [timestamp],
            "log": [log_txt]
        })

        if os.path.exists(log_file_path):
            existing_logs = pl.read_csv(log_file_path)

            new_log = new_log.cast(existing_logs.schema)

            updated_logs = pl.concat([existing_logs, new_log], how="vertical")
        else:
            updated_logs = new_log

        updated_logs.write_csv(log_file_path)

    async def load_flagged_users(self):
        log_file_path = "src/flag.log"
        if not os.path.exists(log_file_path):
            return set()
        
        with open(log_file_path, "r", encoding="utf-8") as file:
            return {int(line.strip()) for line in file if line.strip().isdigit()}

    async def log_flagged_user(self, user_id):
        log_file_path = "src/flag.log"
        with open(log_file_path, "a", encoding="utf-8") as file:
            file.write(f"{user_id}\n")

    async def FindActiveModeratorRandom(self, guild, role_name):
        mod_role = discord.utils.get(guild.roles, name=role_name)
        if not mod_role:
            return None

        active_mods = [member for member in mod_role.members if member.status in (discord.Status.online, discord.Status.idle)]

        return random.choice(active_mods) if active_mods else None
    
    async def on_message(self, message): 

        if message.author == self.user:
              return    
          
        #Receives Message from ShreeSPSV's Server For Stock Updates
        if message.guild.id == 1240215331071594536 and message.channel.id == 1362321135231959112:
            message_id = message.id
            channel = bot.get_channel(1362321135231959112)

            embeded_string = ""
            if channel is None:
                return

            try:
                fetched_message = await channel.fetch_message(message_id)
                if fetched_message.embeds:
                    for i, embed in enumerate(fetched_message.embeds):           
                        title = embed.title or "-"
                        description = embed.description or "-"
                        
                        embeded_string += f"Title: {title}"
                        embeded_string += f"Description: {description}"

                    Title, Fruit_Items =  SPA.StockMessageProcessor(embeded_string)
                else:
                    return
            except Exception as e:
                return

            processed_fruits = ""

            CurrentGoodFruits = []
            for keys, values in Fruit_Items.items():
                processed_fruits += f"\n- {emoji_data[keys][0]} **{keys}** {emoji_data['beli'][0]} {values}"
                if "normal" in title.lower():
                    if keys in good_fruits:
                        CurrentGoodFruits.append(keys)
                else:
                    if keys in m_good_fruits:
                        CurrentGoodFruits.append(keys)


            embed = discord.Embed(title=Title.upper(),
                            description=f"{processed_fruits}",
                                    colour=embed_color_code)
                
            embed.set_author(name=bot_name,
                    icon_url=bot_icon_link_url)

            embed.add_field(name="",
                value=f"[{server_name}]({server_invite_link})",
                inline=False)
            
            if "normal" in Title.lower():
                embed.set_thumbnail(url="https://static.wikia.nocookie.net/roblox-blox-piece/images/b/b6/BloxFruitDealer.png")
            else:
                embed.set_thumbnail(url="https://static.wikia.nocookie.net/roblox-blox-piece/images/0/0d/Advanced_Blox_Fruit_Dealer%282%29.png")
            
            stock_update_channel = bot.get_channel(stock_update_channel_id)
            stock_message = await stock_update_channel.send(embed=embed)
            await stock_message.add_reaction("🇼")
            await stock_message.add_reaction("🇱")

            if CurrentGoodFruits != []:
                    await stock_update_channel.send(f"<@&{stock_ping_role_id}>{', '.join(CurrentGoodFruits)} is in {Title}.  Make sure to buy them")

        elif re.search(r"\b(fruit value of|value of)\b", message.content.lower()):
            fChannel = self.get_channel(fruit_values_channel_id)
            if message.channel == fChannel:
                match = re.search(r"\b(?:fruit value of|value of)\s+(.+)", message.content.lower())
                if match:
                        item_name = match.group(1).strip()
                        item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()
                        item_name = MatchFruitSet(item_name, fruit_names)
                        item_name_capital = item_name.title() if item_name else ""
                        jsonfruitdata = fetch_fruit_details(item_name)
                        if isinstance(jsonfruitdata, dict):
                            fruit_img_link = FetchFruitImage(item_name_capital)
                            #await message.channel.send(f"> # {item_name.title()}\n> - **Physical Value**: {jsonfruitdata['physical_value']} \n> - **Physical Demand**: {jsonfruitdata['physical_demand']} \n> - **Physical DemandType **: {jsonfruitdata['demand_type']} \n> - **Permanent Value**: {jsonfruitdata['permanent_value']} \n> - **Permanent Demand**: {jsonfruitdata['permanent_demand']} \n> - **Permanent Demand Type**: {jsonfruitdata['permanent_demand_type']}")
                            embed = discord.Embed(title=f"{item_name.title()}",
                            colour=embed_color_codes[jsonfruitdata['category']])

                            embed.set_author(name=bot_name,
                            icon_url=bot_icon_link_url)

                            embed.add_field(name="Physical Value",
                                            value=f"{jsonfruitdata['physical_value']}",
                                            inline=False)
                            embed.add_field(name="Physical Demand",
                                            value=f"{jsonfruitdata['physical_demand']}",
                                            inline=False)
                            if jsonfruitdata.get('permanent_value'):
                                embed.add_field(name="Permanent Value",
                                                value=f"{jsonfruitdata['permanent_value']}",
                                                inline=False)
                            if jsonfruitdata.get('permanent_demand'):
                                embed.add_field(name="Permanent Demand",
                                                value=f"{jsonfruitdata['permanent_demand']}",
                                                inline=False)
                            embed.add_field(name="Demand Type",
                                            value=f"{jsonfruitdata['demand_type']}",
                                            inline=False)
                            if fruit_value_embed_type == 0:
                                embed.set_image(url=fruit_img_link)
                            else:
                                embed.set_thumbnail(url=fruit_img_link)

                            embed.add_field(name="",
                            value=f"[{server_name}]({server_invite_link})",
                            inline=False)

                            await message.reply(embed=embed)                    

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
                    output_dict = j_LorW(your_fruits, your_fruit_types, their_fruits, their_fruits_types, Type)
                    #await message.channel.send(resultant)
                    if isinstance(output_dict, dict):

                        percentage_calculation = calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                    
                        embed = discord.Embed(title=output_dict["TradeConclusion"],description=output_dict["TradeDescription"],color=output_dict["ColorKey"],)
                        embed.set_author(
                            name=bot_name,
                            icon_url=bot_icon_link_url
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
                            value=f"[{server_name}]({server_invite_link})",
                            inline=False
                        )

                        w_or_l_channel = self.get_channel(w_or_l_channel_id)
                        if message.channel == w_or_l_channel:
                            await message.reply(embed=embed)

                else:
                    w_or_l_channel = self.get_channel(w_or_l_channel_id)
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

                        image = await asyncio.to_thread(
                            j_LorW,
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
                output_dict = j_LorW(your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess)
                
                if(isinstance(output_dict, dict)):
                    percentage_calculation = calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                    
                    embed = discord.Embed(title=output_dict["TradeConclusion"],description=output_dict["TradeDescription"],color=output_dict["ColorKey"])

                    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)

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
                        value=f"[{server_name}]({server_invite_link})",
                        inline=False
                    )

                    _w_or_l_channel = self.get_channel(w_or_l_channel_id)
                    if message.channel == _w_or_l_channel:
                        await message.reply(embed=embed) 

            else:
                    w_or_l_channel = self.get_channel(w_or_l_channel_id)
                    if message.channel == w_or_l_channel:
                        status_msg = await message.reply("Thinking...")

                        image = await asyncio.to_thread(
                            j_LorW,
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

            if message.channel == self.get_channel(w_or_l_channel_id):
                view = self.TradeSuggestorWindow(bot=self,user=message.author,your_fruits=your_fruits1,your_types=your_fruit_types1)

                embed = discord.Embed(title="Trade Suggestion Configuration",description="",color=discord.Color.red())
                
                embed.add_field(name="• Customize your Suggestor Settings, Then Click Suggest", value="")

                await message.reply(embed=embed, view=view)

        elif FDAE.is_valid_trade_suggestor_sequence(message.content):
            your_fruits1, your_fruit_types1, their_fruits1, their_fruits_types1 = FDAE.extract_fruit_trade(message.content, emoji_id_to_name)

            if message.channel == self.get_channel(w_or_l_channel_id):
                view = self.TradeSuggestorWindow(bot=self,user=message.author,your_fruits=your_fruits1,your_types=your_fruit_types1)

                embed = discord.Embed(title="Trade Suggestion Configuration",description="",color=discord.Color.red())
                
                embed.add_field(name="• Customize your Suggestor Settings, Then Click Suggest", value="")

                await message.reply(embed=embed, view=view)

        elif "value.update" in message.content.lower():
            if message.author.id in ids:
                user_message = message.content.lower()
                message_parsed = user_message.split()

                fields = {
                    "name": "",
                    "physical_value": "",
                    "permanent_value": "",
                    "physical_demand": "",
                    "permanent_demand": "",
                    "demand_type": "",
                    "permanent_demand_type": ""
                }

                field_keys = list(fields.keys())

                current_key = None
                for word in message_parsed:
                    if word in field_keys:
                        current_key = word
                        fields[current_key] = ""
                    elif current_key:
                        if fields[current_key]:
                            fields[current_key] += " "
                        fields[current_key] += word

                if any(not value.strip() for value in fields.values()):
                    await message.channel.send("Format Invalidation Error")
                    return

                fields["name"] = fields["name"].title()
                fields["demand_type"] = fields["demand_type"].title()
                fields["permanent_demand_type"] = fields["permanent_demand_type"].title()

                update_fruit_data(
                    fields["name"],
                    fields["physical_value"],
                    fields["permanent_value"],
                    fields["physical_demand"],
                    fields["permanent_demand"],
                    fields["demand_type"],
                    fields["permanent_demand_type"]
                )

                await message.channel.send("Value of fruit updated successfully!")
                await self.WriteLog(message.author.id,f"Updated {fields['name']} value!")

            else:
                user_message = message.content.lower()
                message_parsed = user_message.split()

                try:
                    name_index = message_parsed.index("name")
                    name = message_parsed[name_index + 1].title()
                except (ValueError, IndexError):
                    name = "Unknown"

                await message.channel.send("No Permission")
                await self.WriteLog(message.author.id, f"Attempted to update **{name}** value without permission!")

        elif "update logs" in message.content.lower():
            if message.author.id in ids + owner_ids:

                parser = message.content.lower().split()
                log_min = 0
                log_max = 10
                user_id_filter = None

                if "logs" in parser:
                    log_index = parser.index("logs")

                    if log_index + 1 < len(parser) and parser[log_index + 1].isdigit():
                        user_id_filter = parser[log_index + 1]

                        if log_index + 2 < len(parser):
                            range_part = parser[log_index + 2]
                            if ':' in range_part:
                                try:
                                    log_min, log_max = map(int, range_part.split(":"))
                                except ValueError:
                                    log_min, log_max = 0, 10
                            else:
                                try:
                                    log_max = int(range_part)
                                except ValueError:
                                    log_max = 10

                    elif log_index + 1 < len(parser):
                        range_part = parser[log_index + 1]
                        if ':' in range_part:
                            try:
                                log_min, log_max = map(int, range_part.split(":"))
                            except ValueError:
                                log_min, log_max = 0, 10
                        else:
                            try:
                                log_max = int(range_part)
                            except ValueError:
                                log_max = 10

                logs_string = ""
                log_file_path = "storage/botlogs/logs.csv"

                try:
                    df = pl.read_csv(log_file_path)

                    if user_id_filter:
                        df = df.filter(pl.col("user_id") == int(user_id_filter))

                    df = df.reverse()
                    total_rows = df.height
                    log_min = max(0, log_min)
                    log_max = min(total_rows, log_max)

                    df = df.slice(log_min, log_max)

                    embed = discord.Embed(
                        title="LOGS",
                        description=f"Showing logs for user <@{user_id_filter}>" if user_id_filter else "Latest logs",
                        colour=0xfe169d
                    )
                    
                    embed.set_author(name=f"{bot_name}")

                    for row in df.iter_rows():
                        user_id, timestamp, log_text = row
                        embed.add_field(
                            name="",
                            value=f"**User** <@{user_id}> at {timestamp}\n**Log-** {log_text}",
                            inline=False
                        )

                except Exception as e:
                    logs_string = f"Error reading logs: {str(e)}"
                
                await message.channel.send(embed=embed)

            else:
                await message.channel.send("You don't have access to use this command!") 

        elif "clear logs keeplast" in message.content.lower():
            if message.author.id in ids:
                log_file_path = "storage/botlogs/logs.csv"
                parser = message.content.lower().split()
                
                if "keeplast" in parser:
                    log_index = parser.index("keeplast")
                    if log_index + 1 < len(parser):
                        try:
                            lines_to_keep = int(parser[log_index + 1])
                        except ValueError:
                            lines_to_keep = 10
                    else:
                        lines_to_keep = 10
                else:
                    lines_to_keep = 10

                try:
                    df = pl.read_csv(log_file_path)

                    if df.height > lines_to_keep:
                        df = df.tail(lines_to_keep)

                        df.write_csv(log_file_path)
                        await message.channel.send(f"Logs deleted, keeping the last {lines_to_keep} logs!")
                    else:
                        await message.channel.send("Not enough logs to delete. Keeping existing logs.")

                except Exception as e:
                    await message.channel.send(f"Error clearing logs: {e}")

            else:
                await message.channel.send("You don't have access to use this command!")         

        #TEMPORARY FUNCTIONS : WILL BE REMOVED IN THE FUTURE UPDATE
        elif "switch ui mode" in message.content.lower():
            if message.author.id in ids + owner_ids:
                parts = message.content.lower().split()
                if len(parts) >= 4 and parts[2] == "mode":
                    number = parts[3]
                    with open("Values/valueconfig.logs", "w") as fileptr:
                        fileptr.write(number)
                        await message.reply("Switched Mode!")

        elif "assign ban log channel id:" in message.content.lower():
            if message.author.id in ids + owner_ids:
                channel_id = message.content.replace("assign ban log channel id:", "").strip()
                
                with open("src/Moderation/logchannelid.log", "w") as file:
                    file.write(str(channel_id))
        
                await message.channel.send(f"Ban log channel ID set to <#{channel_id}>.")

        await bot.process_commands(message)

bot = MyBot()

@bot.command()
async def ban(ctx, member: str = "", *, reason="No reason provided"):
    proofs = []
    role_ids = [role.id for role in ctx.author.roles if role.name != "@everyone"]

    for attachment in ctx.message.attachments:
        if attachment.content_type and any(attachment.content_type.startswith(t) for t in ["image/", "video/"]):
            file = await attachment.to_file()
            proofs.append(file)
        else:
            await ctx.send(f"File type {attachment.filename} Not Supported, so it will not be sent to logs channel")

    try:
        target_user = None
        try:
            target_user = await commands.MemberConverter().convert(ctx, member)
        except commands.MemberNotFound:
            try:
                user_id = int(member)
                target_user = await ctx.bot.fetch_user(user_id)
            except ValueError:
                await ctx.send(embed=mLily.SimpleEmbed(f"Value Error {ValueError}"))
                return
            except discord.NotFound:
                await ctx.send(embed=mLily.SimpleEmbed(f"User ID {member} not found. Please check the ID."))
                return
            except discord.HTTPException as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user data: {e}"))
                return

        if not target_user:
            await ctx.send(embed=mLily.SimpleEmbed("No Valid Users to Ban"))
            return

        if not mLily.exceeded_ban_limit(ctx.author.id, role_ids):
            await mLily.ban_user(ctx, target_user, reason, proofs)
        else:
            await ctx.send(embed=mLily.SimpleEmbed(
                f"Cannot ban the user! I'm Sorry But you have exceeded your daily limit\n"
                f"You can ban in {mLily.remaining_Ban_time(ctx.author.id, role_ids)}"
            ))

    except Exception as e:
        await ctx.send(embed=mLily.SimpleEmbed(f"An error occurred: {e}"))

@bot.command()
async def unban(ctx, user_id: str):
    if ctx.author.id not in trusted_moderator_ids:
        await ctx.send(embed=mLily.SimpleEmbed("You Don't Have Permission to Unban!"))
        return
    user_id = int(user.replace("<@", "").replace(bot_command_prefix, "").replace(">", ""))
    user = await bot.fetch_user(user_id)
    try:
        await ctx.guild.unban(user)
        await ctx.send(embed=mLily.SimpleEmbed(f"Unbanned {user.mention}"))
    except discord.NotFound:
        await ctx.send(embed=mLily.SimpleEmbed("This user is not banned!"))
    except discord.Forbidden:
        await ctx.send(f"Exception Raised: {discord.Forbidden}")
    except discord.HTTPException as e:
        await ctx.send(f"Exception Raised: {e}")

@bot.command()
async def banlogs(ctx, slice_exp: str = None, member: str = ""):
    try:
        try:
            start, stop = (int(x) if x else 0 for x in slice_exp.split(":"))
        except ValueError:
            await ctx.send(embed=mLily.SimpleEmbed("Slicing Error. Make sure your slicing is in the format 'start:stop'"))
            return
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Error while parsing slice: {e}"))
            return

        accessible_roles = []
        for keys, values in limit_Ban_details.items():
            accessible_roles.append(keys)

        if not any(role.id in accessible_roles for role in ctx.author.roles):
            await ctx.send("Access Denied!", delete_after=5)
            return

        if not member:
            try:
                user = await bot.fetch_user(ctx.author.id)
                embed = mLily.display_logs(ctx.author.id, user, slice_expr=slice(start, stop))
            except Exception as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user or display logs: {e}"))
                return
        else:
            try:
                user = await bot.fetch_user(int(member))
                embed = mLily.display_logs(int(member), user, slice_expr=slice(start, stop))
            except ValueError:
                await ctx.send(embed=mLily.SimpleEmbed("Member ID must be a integer"))
                return
            except Exception as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch member ban logs csv: {e}"))
                return

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=mLily.SimpleEmbed(f"An unexpected error occurred: {e}"))

@bot.hybrid_command(name='vouch', description='Vouch a service handler')
async def vouch(ctx: commands.Context,  member: discord.Member, note: str = "", received: str = ""):
    if concurrent_guild_id != ctx.guild.id:
        await ctx.send("You Cannot Vouch Due to Server Change!")
        return
    if not member:
        pass
    elif member == ctx.author:
        await ctx.send(embed=mLily.SimpleEmbed("You cannot vouch yourself!"))
    else:
        account_age = (discord.utils.utcnow() - ctx.author.created_at).days
        if account_age < 90:
            await ctx.send(embed=mLily.SimpleEmbed("Your Account is Not Old Enough to Vouch! a Service provider"))
        else:
            await ctx.send(embed=vLily.store_vouch(ctx, member, note, received))
    pass

@bot.hybrid_command(name='show_vouches', description='displays recent 5 vouches for a  service handler')
async def show_vouches(ctx: commands.Context,  member: discord.Member, min:int = 0, max:int = 3):
    if not member:
        pass
    else:
        await ctx.send(embed=vLily.display_vouch_embed(member, min, max))
    pass

@bot.hybrid_command(name='verify_service_provider', description='if a service provider is trusted then he can be verified')
async def verify_service_provider(ctx: commands.Context,  member: discord.Member):
    if not member:
        await ctx.send(embed=mLily.SimpleEmbed("No Members Passed in!"))
    else:
        role = discord.utils.get(ctx.author.roles, id=service_manager_roll_id)

        if role:
            await ctx.send(embed=vLily.verify_servicer(member.id))
        else:
            await ctx.send(embed=mLily.SimpleEmbed("Access Denied!"))

@bot.hybrid_command(name='unverify_service_provider', description='if a service provider is found to be  fraud after verification then he can be un-verified')
async def unverify_service_provider(ctx: commands.Context,  member: discord.Member):
    if not member:
        await ctx.send(embed=mLily.SimpleEmbed("No Members Passed in!"))
    else:
        role = discord.utils.get(ctx.author.roles, id=service_manager_roll_id)

        if role:
            await ctx.send(embed=vLily.unverify_servicer(member.id))
        else:
            await ctx.send(embed=mLily.SimpleEmbed("Access Denied!"))

@bot.hybrid_command(name='delete_vouch', description='deletes a vouch from mentioned service provider at a particular timeframe')
async def delete_vouch(ctx: commands.Context,  member: discord.Member, timestamp_str: str):
    if not member:
        await ctx.send(embed=mLily.SimpleEmbed("No Members Passed in!"))
    else:
        role = discord.utils.get(ctx.author.roles, id=service_manager_roll_id)

        if role:
            success = vLily.delete_vouch(member.id, timestamp_str)
            if success:
                await ctx.send(embed=mLily.SimpleEmbed("Successfully deleted vouch from the service provider"))
            else:
                await ctx.send(embed=mLily.SimpleEmbed("Unable to delete vouch from the service provider!  Verify correct timestamp"))
        else:
            await ctx.send(embed=mLily.SimpleEmbed("Access Denied!"))

@bot.hybrid_command(name="blacklist_user", description="Blacklist a user ID from using limited ban command.")
async def blacklist_user(ctx: commands.Context, user: discord.Member):
    if isinstance(ctx.author, discord.Member):
        if not ctx.author.id in owner_ids + staff_manager_ids:
            await ctx.send(embed=mLily.SimpleEmbed("You do not have permission to use this command."))
            return
    current_ids = load_exceptional_ban_ids()

    if user.id in current_ids:
        await ctx.send(embed=mLily.SimpleEmbed("User is already blacklisted"))
        return

    current_ids.append(user.id)
    save_exceptional_ban_ids(current_ids)

    await ctx.send(embed=mLily.SimpleEmbed(f"<@{user.id}> Got Blacklisted"))
    await bot.WriteLog(ctx.author.id, f"has Blacklisted <@{user.id}> from using **Limited Bans**")

@bot.hybrid_command(name="unblacklist_user", description="Remove a user ID from the limited ban blacklist.")
async def unblacklist_user(ctx: commands.Context, user: discord.Member):
    if isinstance(ctx.author, discord.Member):
        if not ctx.author.id in owner_ids + staff_manager_ids:
            await ctx.send(embed=mLily.SimpleEmbed("You do not have permission to use this command."))
            return

    current_ids = load_exceptional_ban_ids()

    if user.id not in current_ids:
        await ctx.send(embed=mLily.SimpleEmbed("User is not blacklisted."))
        return

    current_ids.remove(user.id)
    save_exceptional_ban_ids(current_ids)

    await ctx.send(embed=mLily.SimpleEmbed(f"<@{user.id}> has been removed from the blacklist."))
    await bot.WriteLog(ctx.author.id, f"has removed <@{user.id}> from the **Limited Bans** blacklist.")

@bot.hybrid_command(name="assign_role", description="Assign a role to a user if it's allowed")
async def assign_role(ctx: commands.Context, user: discord.Member, role: discord.Role):
    assignable_roles = load_roles()
    role_id_str = str(role.id)

    if role_id_str not in assignable_roles:
        await ctx.reply(f"The role {role.name} is not assignable.")
        return

    role_priority = assignable_roles[role_id_str].lower()

    if role_priority == "low":
        if ctx.author.id not in trusted_moderator_ids + owner_ids + staff_manager_ids:
            await ctx.reply("You are not allowed to assign role.")
            return
    elif role_priority == "high":
        if ctx.author.id not in staff_manager_ids + owner_ids:
            await ctx.reply("You are not allowed to give high priority roles")
            return
    else:
        await ctx.reply(f"Invalid priority level {role_priority} for role {role.name}.")
        return

    if role in user.roles:
        await ctx.reply(f"{user.display_name} already has the {role.name} role.")
        return

    if role.position >= ctx.author.top_role.position and ctx.author.id not in owner_ids:
        await ctx.reply("You cannot assign a role that is higher than or equal to your highest role.")
        return

    try:
        await user.add_roles(role, reason=f"Assigned by {ctx.author}")
        await ctx.reply(f"Assigned {role.name} to {user.display_name}.")
        await bot.WriteLog(ctx.author.id, f"Assigned <@&{role.id}> to {user.display_name}.")
    except discord.Forbidden:
        await ctx.reply("I don't have permission to assign that role.")
    except Exception as e:
        await ctx.reply(f"An error occurred: {e}")

@bot.hybrid_command(name="unassign_role", description="Remove a role from a user if it's allowed")
async def unassign_role(ctx: commands.Context, user: discord.Member, role: discord.Role):
    assignable_roles = load_roles()
    role_id_str = str(role.id)

    if role_id_str not in assignable_roles:
        await ctx.reply(f"The role {role.name} is not assignable, so it can't be removed.")
        return

    role_priority = assignable_roles[role_id_str].lower()

    if role_priority == "low":
        if ctx.author.id not in trusted_moderator_ids + owner_ids + staff_manager_ids:
            await ctx.reply("You are not allowed to remove this role.", ephemeral=True)
            return
    elif role_priority == "high":
        if ctx.author.id not in staff_manager_ids + owner_ids:
            await ctx.reply("You are not allowed to remove this high-priority role.", ephemeral=True)
            return
    else:
        await ctx.reply(f"Invalid priority level `{role_priority}` for role {role.name}.", ephemeral=True)
        return

    if role not in user.roles:
        await ctx.reply(f"{user.display_name} does not have the {role.name} role.")
        return

    if role.position >= ctx.author.top_role.position and ctx.author.id not in owner_ids:
        await ctx.reply("You cannot remove a role that is higher than or equal to your highest role.")
        return
    try:
        await user.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.reply(f"Removed {role.name} from {user.display_name}.")
        await bot.WriteLog(ctx.author.id, f"Removed <@&{role.id}> from {user.display_name}.")
    except discord.Forbidden:
        await ctx.reply("I don't have permission to remove that role.")
    except Exception as e:
        await ctx.reply(f"An error occurred: {e}")

class Priority(str, Enum):
    low = "low"
    high = "high"
@bot.hybrid_command(name="make_role_assignable", description="Allows specific users to assign this role")
async def make_roles_assignable(ctx: commands.Context, role: discord.Role, priority: Priority):
    try:
        assignable_roles = load_roles()
    except Exception as e:
        await ctx.reply(f"Failed to load assignable roles: `{e}`")
        return

    if ctx.author.id not in owner_ids:
        await ctx.reply("You are not authorized to use this command.")
        return

    try:
        if str(role.id) not in assignable_roles:
            try:
                save_roles(role.id, priority.value)
                await ctx.reply(f"Added Role {role.name} to assignables with {priority.value} priority.")
            except Exception as e:
                await ctx.reply(f"Failed to save role with exception: `{e}`")
        else:
            await ctx.reply(f"Role {role.name} already exists in assignables.")
    except Exception as e:
        await ctx.reply(f"Unhandled Exception: `{e}`", ephemeral=True)

@bot.command()
async def fetchbanlog(ctx, user: str = None):
    if user is None:
        target = ctx.author
    else:
        try:
            user_id = int(user.replace("<@", "").replace(bot_command_prefix, "").replace(">", ""))
            target = await ctx.guild.fetch_member(user_id)
        except (ValueError, discord.NotFound):
            return await ctx.send(embed=mLily.SimpleEmbed("Could not find that user."))

    file_name = f"storage/banlogs/{target.id}-logs.csv"
    if ctx.author.id not in owner_ids + staff_manager_ids + ids:
        await ctx.send(embed=mLily.SimpleEmbed(f"Access Denied for Downloading Source CSV"))
        return
    try:
        with open(file_name, "rb") as f:
            await ctx.send(file=discord.File(f, filename=file_name))
    except FileNotFoundError:
        await ctx.send(embed=mLily.SimpleEmbed(f"No logs found for user {target.mention}."))
    except Exception as e:
        await ctx.send(embed=mLily.SimpleEmbed(f"Excepted Error : {e}."))

@bot.hybrid_command(name="embed_create", description="Creates an embed based on JSON config and sends it to a specific channel")
async def create_embed(ctx: commands.Context, channel_to_send: discord.TextChannel, embed_json_config: str = "{}"):
    try:
        if ctx.author.id not in ids:
            role = ctx.guild.get_role(giveaway_hoster_role)
            if role not in ctx.author.roles:
                await ctx.send("You are restricted", ephemeral=True)
                return

        try:
            json_data = json.loads(embed_json_config)
        except json.JSONDecodeError:
            await ctx.send("Invalid JSON Format")
            return

        try:
            sEmbed = LilyEmbed.ParseEmbedFromJSON(json_data)
            await channel_to_send.send(embed=sEmbed)
            await ctx.send("Embed sent successfully.")
        except Exception as embed_error:
            await ctx.send(f"Parser Failure: {str(embed_error)}")

    except Exception as e:
        await ctx.send(f"Unhandled Exception {str(e)}")

@bot.hybrid_command(name="create_formatted_embed", description="Creates a formatted embed with custom buttons using a set of instructions")
async def create_formatted_embed(ctx, channel_to_send: discord.TextChannel, link: str = ""):
    if ctx.author.id not in owner_ids + staff_manager_ids + trusted_moderator_ids:
        await ctx.send("You are restricted from using this command.", ephemeral=True)
        return

    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(link) as response:
                    if response.status != 200:
                        await ctx.send(f"HTTP Exception: {response.status}")
                        return
                    config = await response.text()
            except aiohttp.ClientError as e:
                await ctx.send(f"Error Fetching Config{str(e)}")
                return

        try:
            embeds, buttons = LilyEmbed.EmbedParser(config, ctx)
        except Exception as e:
            await ctx.send(f"Parser Error: {str(e)}")
            return

        view = discord.ui.View(timeout=None)
        persistent_buttons = []

        for idx, (button, embed) in enumerate(buttons):
            button.custom_id = f"guide_button_{ctx.message.id}_{idx}"

            async def callback(interaction, embed=embed):
                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Displaying Embed Failure {str(e)}", ephemeral=True)

            button.callback = callback
            view.add_item(button)

            persistent_buttons.append({
                "label": button.label,
                "style": button.style.value,
                "custom_id": button.custom_id,
                "embed": embed.to_dict()
            })

        try:
            if embeds:
                message = await channel_to_send.send(embeds=embeds, view=view)
                await ctx.send("Embeds sent successfully.")
            elif buttons:
                message = await channel_to_send.send(content="Use the buttons to explore the guide:", view=view)
                await ctx.send("Buttons sent successfully.")
            else:
                await ctx.send("No embeds or buttons were found in the config. Please check your format.")
                return
        except Exception as e:
            await ctx.send(f"Failed to send message to the specified channel: {str(e)}")
            return

        persistent_data = {
            "message_id": message.id,
            "channel_id": channel_to_send.id,
            "buttons": persistent_buttons
        }

        try:
            if os.path.exists(ButtonSessionMemory):
                with open(ButtonSessionMemory, "r") as f:
                    content = f.read().strip()
                    all_views = json.loads(content) if content else []
            else:
                all_views = []
        except (json.JSONDecodeError, OSError) as e:
            all_views = []

        all_views.append(persistent_data)

        try:
            with open(ButtonSessionMemory, "w") as f:
                json.dump(all_views, f, indent=4)
        except Exception as e:
            await ctx.send(f"Failed to save Button Session.  You may have to post this embed again if program got restarted{str(e)}")
            return

    except Exception as e:
        await ctx.send(f"Unhandled Exception: {str(e)}")

@bot.hybrid_command(name="update_formatted_embed", description="Update an existing formatted embed with a new config rule data")
async def update_formatted_embed(ctx, link: str):
    if ctx.author.id not in owner_ids + staff_manager_ids + trusted_moderator_ids:
        await ctx.send("You are restricted to use this command", ephemeral=True)
        return

    if not os.path.exists(ButtonSessionMemory):
        await ctx.send("No previous sessions found.", ephemeral=True)
        return

    try:
        with open(ButtonSessionMemory, "r") as f:
            all_views = json.load(f)
    except json.JSONDecodeError:
        await ctx.send("Session memory file is corrupted.", ephemeral=True)
        return

    if not all_views:
        await ctx.send("No saved embed sessions to update.", ephemeral=True)
        return

    class SessionSelector(ui.View):
        def __init__(self, ctx, sessions, link):
            super().__init__(timeout=60)
            self.ctx = ctx
            self.sessions = sessions
            self.link = link

            options = [
                SelectOption(
                    label=f"Message ID: {s['message_id']}",
                    description=f"Channel ID: {s['channel_id']}",
                    value=str(i)
                ) for i, s in enumerate(sessions)
            ]
            self.select = ui.Select(placeholder="Choose Embed Session: ", options=options)
            self.select.callback = self.select_callback
            self.add_item(self.select)

        async def select_callback(self, interaction: Interaction):
            index = int(self.select.values[0])
            session = self.sessions[index]

            user = getattr(interaction, "user", None)
            author = getattr(self.ctx, "author", None)

            channel = bot.get_channel(session["channel_id"]) or await bot.fetch_channel(session["channel_id"])
            try:
                message = await channel.fetch_message(session["message_id"])
            except discord.NotFound:
                await interaction.response.send_message("Seems like the message got deleted", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            async with aiohttp.ClientSession() as session_obj:
                async with session_obj.get(self.link) as response:
                    if response.status != 200:
                        await interaction.followup.send(f"Failed to load new config (status {response.status})", ephemeral=True)
                        return
                    new_config = await response.text()

            new_embeds, new_buttons = LilyEmbed.EmbedParser(new_config, self.ctx)

            new_view = ui.View(timeout=None)
            updated_buttons = []

            for idx, (button, embed) in enumerate(new_buttons):
                button.custom_id = f"guide_button_{message.id}_{idx}"

                async def callback(interaction, embed=embed):
                    await interaction.response.send_message(embed=embed, ephemeral=True)

                button.callback = callback
                new_view.add_item(button)

                updated_buttons.append({
                    "label": button.label,
                    "style": button.style.value,
                    "custom_id": button.custom_id,
                    "embed": embed.to_dict()
                })

            if new_embeds:
                await message.edit(embeds=new_embeds, view=new_view)
            elif new_buttons:
                await message.edit(content="Use the buttons to explore the updated guide:", embeds=[], view=new_view)
            else:
                await interaction.response.send_message("Invalid Content in New Config", ephemeral=True)
                return

            self.sessions[index]["buttons"] = updated_buttons

            with open(ButtonSessionMemory, "w") as f:
                json.dump(self.sessions, f, indent=4)

            await interaction.followup.send("Embed updated successfully.", ephemeral=True)

    view = SessionSelector(ctx, all_views, link)
    await ctx.send("Select the session you'd like to update:", view=view, ephemeral=True)
bot.run(bot_token)