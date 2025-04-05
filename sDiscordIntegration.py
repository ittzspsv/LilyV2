import discord
from Stock.sCurrentStock import *
from Values.sStockValueJSON import *
from discord.ext import commands
from Misc.sFruitImageFetcher import *
from Config.sBotDetails import *
import Algorthims.sTradeFormatAlgorthim as TFA
from datetime import datetime, timedelta

import Algorthims.sFruitDetectionAlgorthimEmoji as FDAE
import Algorthims.sFruitDetectionAlgorthim as FDA
import Algorthims.sLinkScamDetectionAlgorthim as SLSDA
import Algorthims.sNSFWDetectionAlgorthim as NSFWDA
import Algorthims.sFruitSuggestorAlgorthim_ as FSA
import Moderation.sLilyModeration as mLily
import Vouch.sLilyVouches as vLily

from Values.sStockValueJSON import *
from collections import deque
from itertools import cycle

import pytz
import os
import random
import asyncio
    
import re

#ACCESSING DATA FORMATS

if port == 0:
    emoji_data_path = "EmojiData.json"
    with open(emoji_data_path, "r", encoding="utf-8") as json_file:
        emoji_data = json.load(json_file)

    emoji_id_to_name = {}
    for fruit_name, emoji_value in emoji_data.items():
        for emoji_values in emoji_value:
            match = re.search(r"<:(\w+):(\d+)>", emoji_values)
            if match:
                emoji_id_to_name[match.group(2)] = fruit_name.title()

else:
    emoji_data_path = "bEmojiData.json"
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

ist = pytz.timezone('Asia/Kolkata')

# Based on Indian Standard Time and 10 mins waiting for correct fetch BASED ON INTERNATIONAL TIMESCALINGS

update_times = [
    (5, 33),
    (9, 33),
    (13, 33),
    (17, 33),
    (21, 33),
    (1, 33),
]

mirage_update_times = [
    (3, 33),
    (5, 33),
    (7, 33),
    (9, 33),
    (11, 33),
    (13, 33),
    (15, 33),
    (17, 33),
    (19, 33),
    (21, 33),
    (23, 33),
]

#Previous Normal Stock
previous_normal_stock_fruits = []
previous_mirage_stock_fruits = []


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.message_content = True
        intents.members = True
        intents.presences = True 
        intents.guilds = True
        super().__init__(command_prefix=bot_command_prefix, intents=intents)

    async def on_ready(self):
        print('Logged on as', self.user)
        self.loop.create_task(self.check_time_and_post())
        await self.tree.sync()

    async def send_discord_message(message):
        await bot.wait_until_ready()
        channel = bot.get_channel(stock_update_channel_id)
        
        if channel:
            await channel.send(message)
        else:
            pass

    async def WriteLog(self, user_id, log_txt):
        log_file_path = "logs.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{user_id} [{timestamp}] made a change :  {log_txt}\n" 

        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)

    async def load_flagged_users(self):
        log_file_path = "flag.log"
        if not os.path.exists(log_file_path):
            return set()
        
        with open(log_file_path, "r", encoding="utf-8") as file:
            return {int(line.strip()) for line in file if line.strip().isdigit()}

    async def log_flagged_user(self, user_id):
        log_file_path = "flag.log"
        with open(log_file_path, "a", encoding="utf-8") as file:
            file.write(f"{user_id}\n")

    async def FindActiveModeratorRandom(self, guild, role_name):
        mod_role = discord.utils.get(guild.roles, name=role_name)
        if not mod_role:
            return None

        active_mods = [member for member in mod_role.members if member.status in (discord.Status.online, discord.Status.idle)]

        return random.choice(active_mods) if active_mods else None

    async def normal_stock(self, Channel, type=0): 
            #Normal Stock Display
            printable_string = ""
            current_good_fruits_n = []
            normal_stock_data = await fetch_stock_until_update("Normal Stock") if type==0 else get_stock("https://fruityblox.com/stock", "Normal Stock")
            temp_stock = []
            if isinstance(normal_stock_data, dict) and normal_stock_data:
                #await message.channel.send("# NORMAL STOCK")
                for fruit, details in normal_stock_data.items():
                    temp_stock.append(fruit)
                    stock_display = ", ".join(details['Stock Type'])
                    printable_string += f"\n- {emoji_data[fruit][0]} **{fruit}**  {emoji_data['beli'][0]}{details['Value'].replace('$', '')}"
                    #await message.channel.send(f"**{fruit}**- **Value** = {details['Value']}, **Stock Type** - {stock_display}")

                for fruit, details in normal_stock_data.items():
                    if fruit in good_fruits:
                        current_good_fruits_n.append(fruit)
                
                else:
                    #Normal Stock Embed
                    embed = discord.Embed(title="NORMAL STOCK",
                            description=f"{printable_string}",
                                    colour=embed_color_code)
                    
                    embed.set_author(name=bot_name,
                            icon_url=bot_icon_link_url)

                    embed.set_thumbnail(url="https://static.wikia.nocookie.net/roblox-blox-piece/images/b/b6/BloxFruitDealer.png")

                    embed.add_field(name="",
                    value=f"[{server_name}]({server_invite_link})",
                    inline=False)

                    normal_stock_message = await Channel.send(embed=embed)
                    await normal_stock_message.add_reaction("🇼")
                    await normal_stock_message.add_reaction("🇱")

                    if current_good_fruits_n != []:
                        pass #disabled pinging system temporarily
                        await Channel.send(f"<@&{stock_ping_role_id}>{', '.join(current_good_fruits_n)} is in Normal Stock :blush:.  Make sure to buy them")

    async def mirage_stock(self, Channel, type=0):
            #Mirage stock
            mirage_stock_data = await fetch_stock_until_update("Mirage Stock") if type == 0 else get_stock("https://fruityblox.com/stock", "Mirage Stock")
            current_good_fruits_m = []
            temp_m_stock = []
            printable_string2 = ""
            if isinstance(mirage_stock_data, dict) and mirage_stock_data:
                #await message.channel.send("# MIRAGE STOCK")
                for fruit, details in mirage_stock_data.items():
                    temp_m_stock.append(fruit)
                    stock_display = ", ".join(details['Stock Type'])
                    printable_string2 += f"\n- {emoji_data[fruit][0]} **{fruit}**  {emoji_data['beli'][0]}{details['Value'].replace('$', '')}" 
                    #await message.channel.send(f"**{fruit}** **Value** = {details['Value']}, **Stock Type** - {stock_display}")

                for fruit, details in mirage_stock_data.items():
                    if fruit in m_good_fruits:
                        current_good_fruits_m.append(fruit)

                #Mirage Stock Embed
                embed = discord.Embed(title="MIRAGE STOCK",
                            description=f"{printable_string2}",
                                    colour=embed_color_code)
                
                embed.set_author(name=bot_name,
                        icon_url=bot_icon_link_url)

                embed.set_thumbnail(url="https://static.wikia.nocookie.net/roblox-blox-piece/images/0/0d/Advanced_Blox_Fruit_Dealer%282%29.png")

                embed.add_field(name="",
                value=f"[{server_name}]({server_invite_link})",
                inline=False)

                mirage_stock_message = await Channel.send(embed=embed)
                await mirage_stock_message.add_reaction("🇼")
                await mirage_stock_message.add_reaction("🇱")


                #await message.channel.send(f"> ### Normal Stock: \n> {printable_string} \n> ### Mirage Stock: \n> {printable_string2}")
                if current_good_fruits_m != []:
                    pass #disabled pinging system temporarily
                    await Channel.send(f"<@&{stock_ping_role_id}>{', '.join(current_good_fruits_m)} is in Mirage Stock:blush:.  Make sure to buy them")

    async def check_time_and_post(self):
        await bot.wait_until_ready()
        channel = bot.get_channel(stock_update_channel_id)
        
        while not self.is_closed():
            now = datetime.now(ist)
            current_time = (now.hour, now.minute)

            tasks = []

            if current_time in update_times:
                tasks.append(asyncio.create_task(self.safe_post_stock(self.normal_stock, channel)))

            if current_time in mirage_update_times:
                tasks.append(asyncio.create_task(self.safe_post_stock(self.mirage_stock, channel)))

            if tasks:
                await asyncio.gather(*tasks)

            future_times = sorted(
                [(h, m) for h, m in (update_times + mirage_update_times) if (h, m) > current_time]
            )

            if future_times:
                next_h, next_m = future_times[0]
                next_check_time = now.replace(hour=next_h, minute=next_m, second=0, microsecond=0)
                sleep_time = (next_check_time - now).total_seconds()    
            else:
                sleep_time = 60

            await asyncio.sleep(max(sleep_time, 1))

    async def safe_post_stock(self, stock_function, channel):
        try:
            await stock_function(channel)
        except Exception as e:
            print(f"Error posting stock: {e}")
                
    async def on_message(self, message):

        if message.author == self.user:
              return      

        elif re.search(r"\b(fruit value of|value of)\b", message.content.lower()):
            match = re.search(r"\b(?:fruit value of|value of)\s+(.+)", message.content.lower())
            if match:
                    item_name = match.group(1).strip()
                    item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()
                    item_name = MatchFruitSet(item_name, fruit_names)
                    item_name_capital = item_name.title()
                    jsonfruitdata = fetch_fruit_details(item_name)
                    if isinstance(jsonfruitdata, dict):
                        fruit_img_link = FetchFruitImage(item_name_capital, 100)
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

                        fChannel = self.get_channel(fruit_values_channel_id)
                        if message.channel == fChannel:
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
                output_dict = j_LorW(your_fruits, your_fruit_types, their_fruits, their_fruits_types)
                #await message.channel.send(resultant)
                if isinstance(output_dict, dict):

                    percentage_calculation = calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                
                    embed = discord.Embed(title=output_dict["TradeConclusion"],description=output_dict["TradeDescription"],color=output_dict["ColorKey"],)
                    embed.set_author(
                        name=bot_name,
                        icon_url=bot_icon_link_url
                    )

                    your_fruit_values = [
                        f"{emoji_data[your_fruit_types[i].title()][0]} {emoji_data[your_fruits[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_IndividualValues'][i])}**"
                        for i in range(min(len(your_fruit_types), len(your_fruits), len(output_dict["Your_IndividualValues"])))
                    ]

                    their_fruit_values = [
                        f"{emoji_data[their_fruits_types[i].title()][0]} {emoji_data[their_fruits[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_IndividualValues'][i])}**"
                        for i in range(min(len(their_fruits_types), len(their_fruits), len(output_dict["Their_IndividualValues"])))
                    ]

                    embed.add_field(
                        name="🔹 **Your Offered Fruits**",
                        value="\n".join(your_fruit_values) if your_fruit_values else "*No fruits offered*",
                        inline=True
                    )

                    embed.add_field(
                        name="🔹 **Their Offered Fruits**",
                        value="\n".join(their_fruit_values) if their_fruit_values else "*No fruits offered*",
                        inline=True
                    )

                    embed.add_field(
                        name="💰 **Your Total Value:**",
                        value=f"{emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_TotalValue'])}**" if output_dict['Your_TotalValue'] else "*No values available*",
                        inline=False
                    )

                    embed.add_field(
                        name="💰 **Their Total Value:**",
                        value=f"{emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_TotalValue'])}**" if output_dict['Their_TotalValue'] else "*No values available*",
                        inline=False
                    )

                    if percentage_calculation != "Invalid input. Please enter numerical values.":
                        embed.add_field(
                            name=f"📊 {percentage_calculation}",
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
                            
        elif FDAE.is_valid_trade_sequence(message.content, emoji_id_to_name):   
            your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess = FDAE.extract_fruit_trade(message.content, emoji_id_to_name)
            print(message.content)
            print(your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess)

            output_dict = j_LorW(your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess)
            if(isinstance(output_dict, dict)):
                percentage_calculation = calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                
                embed = discord.Embed(title=output_dict["TradeConclusion"],description=output_dict["TradeDescription"],color=output_dict["ColorKey"])

                embed.set_author(name=bot_name, icon_url=bot_icon_link_url)

                your_fruit_values = [
                    f"{emoji_data[your_fruit_typess[i].title()][0]} {emoji_data[your_fruitss[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_IndividualValues'][i])}**"
                    for i in range(min(len(your_fruit_typess), len(your_fruitss), len(output_dict["Your_IndividualValues"])))
                ]

                their_fruit_values = [
                    f"{emoji_data[their_fruits_typess[i].title()][0]} {emoji_data[their_fruitss[i]][0]}  {emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_IndividualValues'][i])}**"
                    for i in range(min(len(their_fruits_typess), len(their_fruitss), len(output_dict["Their_IndividualValues"])))
                ]

                embed.add_field(
                    name="🔹 **Your Fruits & Values**",
                    value="\n".join(your_fruit_values) if your_fruit_values else "*No fruits offered*",
                    inline=True
                )

                embed.add_field(
                    name="🔹 **Their Fruits & Values**",
                    value="\n".join(their_fruit_values) if their_fruit_values else "*No fruits offered*",
                    inline=True
                )

                embed.add_field(
                    name="💰 **Your Total Value:**",
                    value=f"{emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Your_TotalValue'])}**" if output_dict['Your_TotalValue'] else "*No values available*",
                    inline=False
                )

                embed.add_field(
                    name="💰 **Their Total Value:**",
                    value=f"{emoji_data['beli'][0]} **{'{:,}'.format(output_dict['Their_TotalValue'])}**" if output_dict['Their_TotalValue'] else "*No values available*",
                    inline=False
                )

                if percentage_calculation != "Invalid input. Please enter numerical values.":
                    embed.add_field(
                        name=f"📊 **Trade Balance:** {percentage_calculation}",
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

        elif TFA.is_valid_trade_suggestor_format(message.content.lower(), fruit_names): 
            pass
            '''
            s_my_fruits, s_my_fruit_types, s_your_fruits, s_your_fruit_typess = FDA.extract_trade_details(message.content.lower())
            suggested_fruits, total_value = FSA.get_trade_suggestions(s_my_fruits, 4, 5)

            my_fruits_emoji = ""
            for individuals in s_my_fruits:
                my_fruits_emoji += f'{emoji_data[individuals][0]}'

            embed = discord.Embed(
                title="TRADE SUGGESTOR",
                description="Here are some of my suggestions for your fruits",
                colour=0x00b0f4
            )
            embed.set_author(name=bot_name, icon_url=bot_icon_link_url)
            
            count = 1
            for trade_value, fruit_lists in suggested_fruits.items():
                fruit_suggested_emoji = ""
                for inner_tuple in fruit_lists[0]:
                    fruit_suggested_emoji += emoji_data[inner_tuple][0]
                embed.add_field(
                            name=f"SUGGESTION {count}",
                            value=f"{my_fruits_emoji}{emoji_data['TradePointer'][0]}{fruit_suggested_emoji} {emoji_data['beli'][0]}{trade_value}",
                            inline=False
                )

                count = count + 1

            w_or_l_channel = self.get_channel(w_or_l_channel_id)
            if message.channel == w_or_l_channel:
                await message.reply(embed=embed)'''

        elif FDAE.is_valid_trade_suggestor_sequence(message.content.lower()):
            pass

        elif f"value.update" in message.content.lower():
            if message.author.id in ids:
                user_message = message.content.lower()
                message_parsed = user_message.split()
                
                #name, physical_value, permanent_value, physical_demand, permanent_demand, demand_type, permanent_demand_type

                prompt = "value.update name gravity physical_value 35,000,000 permanent_value 1,850,000,000 physical_demand 10/10 permanent_demand 10/10 demand_type Overpaid permanent_demand_type Insane"
            
                name_index = message_parsed.index("name")
                physical_value_index = message_parsed.index("physical_value")
                permanent_value_index = message_parsed.index("permanent_value")
                physical_demand_index = message_parsed.index("physical_demand")
                permanent_demand_index = message_parsed.index("permanent_demand")
                demand_type_index = message_parsed.index("demand_type")
                permanent_demand_type_index = message_parsed.index("permanent_demand_type")

            
                name = message_parsed[name_index + 1].title()
                physical_value = message_parsed[physical_value_index + 1]
                permanent_value = message_parsed[permanent_value_index + 1]
                physical_demand = message_parsed[physical_demand_index + 1]
                permanent_demand = message_parsed[permanent_demand_index + 1]
                demand_type = message_parsed[demand_type_index + 1].title()
                permanent_demand_type = message_parsed[permanent_demand_type_index + 1].title()


                update_fruit_data(name, physical_value, permanent_value, physical_demand, permanent_demand, demand_type, permanent_demand_type)

                await message.channel.send("Value Of Fruit Updated SuccessFully!")
                await self.WriteLog(message.author.id, f" Updated {name} Value!")

            else:

                user_message = message.content.lower()
                message_parsed = user_message.split()
                name_index = message_parsed.index("name")
                name = message_parsed[name_index + 1].title()


                await message.channel.send("You don't have access to use this command!")
                await self.WriteLog(f"**{message.author.id}**", f" Attempted to update **{name}** Value!")

        elif "update logs" in message.content.lower():
            if message.author.id in ids:

                parser = message.content.lower().split()
                if "logs" in parser:
                    log_index = parser.index("logs")
                    
                    if log_index + 1 < len(parser):
                        try:
                            loglen = int(parser[log_index + 1])
                        except ValueError:
                            loglen = 10 
                    else:
                        loglen = 10
                else:
                    loglen = 10

                logs_string = ""
                log_file_path = "logs.log"
                with open(log_file_path, "r", encoding="utf-8") as log_file:
                    last_lines = deque(log_file, maxlen=loglen)     
                    
                    for line in last_lines:
                        logs_string += f"{line.strip()} \n\n"


                    embed = discord.Embed(title="LOGS",
                        description=f"{logs_string}",
                        colour=0xfe169d)

                    embed.set_author(name=f"{bot_name}")


                    await message.channel.send(embed=embed)

            else:
                await message.channel.send("You don't have access to use this command!")

        elif "clear logs keeplast" in message.content.lower():
            if message.author.id in ids:
                log_file_path = "logs.log"
                parser =  parser = message.content.lower().split()
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


                with open(log_file_path, "r", encoding="utf-8") as log_file:
                    lines = log_file.readlines()

                # Keep only the last `lines_to_keep`
                recent_logs = lines[-lines_to_keep:]

                with open(log_file_path, "w", encoding="utf-8") as log_file:
                    log_file.writelines(recent_logs)

                await message.channel.send(f"Logs Deleted Keeping Last {lines_to_keep} Logs!")

            else:
                await message.channel.send("You don't have access to use this command!")    

        elif "clear flags keeplast" in message.content.lower():
            if message.author.id in ids:
                log_file_path = "flag.log"
                parser =  parser = message.content.lower().split()
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


                with open(log_file_path, "r", encoding="utf-8") as log_file:
                    lines = log_file.readlines()

                recent_logs = lines[-lines_to_keep:]

                with open(log_file_path, "w", encoding="utf-8") as log_file:
                    log_file.writelines(recent_logs)

                await message.channel.send(f"Logs Deleted Keeping Last {lines_to_keep} Logs!")

            else:
                await message.channel.send("You don't have access to use this command!")          

        elif message.content.lower() == "normal stock":
            stock_update_channel = bot.get_channel(stock_update_channel_id)
            if message.channel == stock_update_channel:
                allowed_role_name = stock_team_roll_name
                role_check = discord.utils.get(message.author.roles, name=allowed_role_name)
                if role_check:
                    channel = bot.get_channel(stock_update_channel_id)
                    await self.normal_stock(channel, type=1)
                    await self.WriteLog(message.author.id, f" Used Normal Stock Command")

        elif message.content.lower() == "mirage stock":
            stock_update_channel = bot.get_channel(stock_update_channel_id)
            if message.channel == stock_update_channel:
                allowed_role_name = stock_team_roll_name
                role_check = discord.utils.get(message.author.roles, name=allowed_role_name)
                if role_check:
                    channel = bot.get_channel(stock_update_channel_id)
                    await self.mirage_stock(channel, type=1)
                    await self.WriteLog(message.author.id, f" Used Mirage Stock Command")

        #Scam Word Detection Algorthim

        elif SLSDA.detect_beamer_message(message.content.lower()) and not TFA.is_valid_trade_format(message.content.lower(), fruit_names):  
            ping_pattern = r"<@\d+>"
            updated_text         = re.sub(ping_pattern, "", message.content.lower())
            emoji_pattern = r"<:\w+:\d+>"
            updated_text = re.sub(emoji_pattern, "", message.content.lower())
            if scam_Detection_prompts == 1:
                boolean = SLSDA.detect_beamer_message(updated_text)
                print(boolean)
                if boolean:
                    flagged_users = await self.load_flagged_users()
                    if message.author.id not in flagged_users:
                        #await self.log_flagged_user(message.author.id)
                        active_moderator = await self.FindActiveModeratorRandom(message.guild, trial_moderator_name)
                        embed = discord.Embed(title=f"Matched Scam",
                                            description="First Encounter : Deleted the message",
                                            colour=0xf50000)

                        if active_moderator:
                            embed.add_field(name="", value=f"{active_moderator.mention}", inline=False)
                        else:
                            embed.add_field(name="", value="No Moderators", inline=False)

                        await message.reply(embed=embed)
                        await message.reply(SLSDA.debug_String)
        
        #NSFW Words deletion
        if "||" in message.content:
            #DISABLED TEMPORARILY
            textwf = 0
            if textwf == 0:
                return
            print(message.content)
            rephrased = message.content.replace("||", "")
            if NSFWDA.is_nsfw(rephrased, NSFWDA.nsfw_set):
                try:
                    await message.delete()
                    await message.channel.send("Flagged Words Deleted")
                except discord.NotFound:
                    pass

        if NSFWDA.is_nsfw(message.content.lower(), NSFWDA.nsfw_set):
            #DISABLED TEMPORARILY
            textwf = 0
            if textwf == 0:
                return
            try:
                await message.delete()
                await message.channel.send("Flagged Words Deleted")
            except discord.NotFound:
                pass

        await bot.process_commands(message)

bot = MyBot()


@bot.command()
async def ban(ctx, member: str, *, reason="No reason provided"):
    try:
        target_user = None
        try:
            target_user = await commands.MemberConverter().convert(ctx, member)
        except commands.MemberNotFound:
            try:
                if isinstance(member, discord.User):
                    user_id = member.id
                else:
                    user_id = int(member)
                target_user = await ctx.bot.fetch_user(user_id)
            except ValueError:
                await ctx.send(embed=mLily.SimpleEmbed("Invalid user ID format. Provide a valid numeric ID."))
                return
            except discord.NotFound:
                await ctx.send(embed=mLily.SimpleEmbed(f"User ID {member} not found. Please check the ID."))
                return
            except discord.HTTPException as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user data: {e}"))
                return

        if not mLily.exceeded_ban_limit(ctx.author.id):
            await mLily.ban_user(ctx, target_user, reason)
        else:
            await ctx.send(embed=mLily.SimpleEmbed(f"Cannot ban the user! I'm Sorry But you have exceeded your daily limit"))

    except Exception as e:
        await ctx.send(embed=mLily.SimpleEmbed(f"An error occurred: {e}"))

@bot.command()
async def banlogs(ctx, slice_exp: str, member: str = ""):
    try:
        start, stop = (int(x) if x else 0 for x in slice_exp.split(":"))
    except ValueError:
        await ctx.send(embed=mLily.SimpleEmbed("Slicing Error. Make sure your slicing is in the format 'start:stop'"))
        return
    if not member:
        user = await bot.fetch_user(ctx)
        embed = mLily.display_logs(ctx.author.id, user, slice_expr=slice(start, stop))
    else:
        user = await bot.fetch_user(member)
        embed = mLily.display_logs(member, user, slice_expr=slice(start, stop))

    await ctx.send(embed=embed)

@bot.hybrid_command(name='vouch', description='Vouch a service handler')
async def vouch(ctx: commands.Context,  member: discord.Member, note: str = "", received: str = ""):
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

@bot.hybrid_command(name='item_value', description='Gives you the value details of a single fruit')
async def item_value(ctx: commands.Context, item_name: str):
    fChannel = bot.get_channel(fruit_values_channel_id)

    if isinstance(ctx, discord.Interaction):
        if ctx.channel == fChannel:
            await ctx.response.reply(f"Fruit Value: {item_name}")
        else:
            await ctx.response.reply("Use Appropriate Channels", ephemeral=True)
    else:
        if ctx.channel == fChannel:
            item_name = item_name
            item_name_capital = item_name.title()
            jsonfruitdata = fetch_fruit_details(item_name)
            if isinstance(jsonfruitdata, dict):
                    fruit_img_link = FetchFruitImage(item_name_capital, 100)
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

                    await ctx.send(embed=embed)


        else:
            await ctx.send("Use Appropriate Channels")

bot.run(bot_token)  