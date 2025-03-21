import discord
from sCurrentStock import *
from sStockValueJSON import *
from discord.ext import commands
from sStockValuesScrapper import *
from sFruitImageFetcher import *
from sBotDetails import *
import sTradeFormatAlgorthim as TFA
from datetime import datetime, timedelta
import sFruitDetectionAlgorthimEmoji as FDAE
import sFruitDetectionAlgorthim as FDA

import pytz
import asyncio
    
import re

#ACCESSING DATA FORMATS

value_data_path = "ValueData.json"
with open(value_data_path, "r", encoding="utf-8") as json_file:
    value_data = json.load(json_file)


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
    (5, 30),
    (9, 30),
    (13, 30),
    (17, 30),
    (21, 30),
    (1, 30),
]

mirage_update_times = [
    (3, 30),
    (5, 30),
    (7, 30),
    (9, 30),
    (11, 30),
    (13, 30),
    (15, 30),
    (17, 30),
    (19, 30),
    (21, 30),
    (23, 30),
]

#Previous Normal Stock
previous_normal_stock_fruits = []
previous_mirage_stock_fruits = []

intents = discord.Intents.default()
intents.message_content = True
class MyBot(commands.Bot):
    def __init__(self):
        
        super().__init__(command_prefix="!", intents=intents)


    async def on_ready(self):
        print('Logged on as', self.user)
        self.loop.create_task(self.check_time_and_post())
        await self.tree.sync()

    async def normal_stock(self, Channel): 
            #Normal Stock Display
            printable_string = ""
            current_good_fruits_n = []
            normal_stock_data = await fetch_stock_until_update("Normal Stock")
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
                        await Channel.send(f"<@&{stock_ping_role_id}>{', '.join(current_good_fruits_n)} is in Normal Stock :blush:.  Make sure to buy them")

    async def mirage_stock(self, Channel):
            #Mirage stock
            mirage_stock_data = await fetch_stock_until_update("Mirage Stock")
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
                    if fruit in good_fruits:
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
            await asyncio.sleep(5)
            try:
                await stock_function(channel)
            except Exception as e:
                print(f"Failed to post stock again: {e}")
                
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
                
                    embed = discord.Embed(title=output_dict["TradeConclusion"],
                        description= output_dict["TradeDescription"],
                        colour=output_dict["ColorKey"],)

                    embed.set_author(name=bot_name,
                                    icon_url=bot_icon_link_url)

                    your_fruit_values = []
                    for i in range(min(len(your_fruit_types), len(your_fruits), len(output_dict["Your_IndividualValues"]))):
                        your_fruit_values.append(f"- {emoji_data[your_fruit_types[i].title()][0]} {emoji_data[your_fruits[i]][0]} {emoji_data['beli'][0]}{'{:,}'.format(output_dict['Your_IndividualValues'][i])}")

                    their_fruit_values = []
                    for i in range(min(len(their_fruits_types), len(their_fruits), len(output_dict["Their_IndividualValues"]))):
                       their_fruit_values.append(f"- {emoji_data[their_fruits_types[i].title()][0]} {emoji_data[their_fruits[i]][0]} {emoji_data['beli'][0]}{'{:,}'.format(output_dict['Their_IndividualValues'][i])}")

                    embed.add_field(
                        name="Your Fruit Values",
                        value=f"\n" + "\n".join(your_fruit_values) + "" if your_fruit_values else "*No values available*",
                        inline=True
                    )

                    embed.add_field(
                        name="Their Fruit Values",
                        value=f"\n" + "\n".join(their_fruit_values) + "" if their_fruit_values else "*No values available*",
                        inline=True
                    )

                    embed.add_field(
                        name="Your Total Values: ",
                        value=f"{emoji_data['beli'][0]}{'{:,}'.format(output_dict['Your_TotalValue'])} " if output_dict['Your_TotalValue'] else "*No values available*",
                        inline=False
                    )
                
                    embed.add_field(
                            name="Their Total Values: ",
                            value=f"{emoji_data['beli'][0]}{'{:,}'.format(output_dict['Their_TotalValue'])} " if output_dict['Their_TotalValue'] else "*No values available*",
                            inline=False
                        )

                    if(percentage_calculation != "Invalid input. Please enter numerical values."):
                        embed.add_field(name=percentage_calculation,
                        value="",
                        inline=False)

                    embed.add_field(name="",
                    value=f"[{server_name}]({server_invite_link})",
                    inline=False)

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
                
                embed = discord.Embed(title=output_dict["TradeConclusion"],
                        description= output_dict["TradeDescription"],
                        colour=output_dict["ColorKey"],)

                embed.set_author(name=bot_name,
                                    icon_url=bot_icon_link_url)
                
                your_fruit_values = []
                for i in range(min(len(your_fruit_typess), len(your_fruitss), len(output_dict["Your_IndividualValues"]))):
                    your_fruit_values.append(f"- {emoji_data[your_fruit_typess[i].title()][0]} {emoji_data[your_fruitss[i]][0]} {emoji_data['beli'][0]}{'{:,}'.format(output_dict['Your_IndividualValues'][i])}")

                their_fruit_values = []
                for i in range(min(len(their_fruits_typess), len(their_fruitss), len(output_dict["Their_IndividualValues"]))):
                    their_fruit_values.append(f"- {emoji_data[their_fruits_typess[i].title()][0]} {emoji_data[their_fruitss[i]][0]} {emoji_data['beli'][0]}{'{:,}'.format(output_dict['Their_IndividualValues'][i])}")

                embed.add_field(
                        name="Your Fruit Values",
                        value=f"\n" + "\n".join(your_fruit_values) + "" if your_fruit_values else "*No values available*",
                        inline=True
                    )

                embed.add_field(
                        name="Their Fruit Values",
                        value=f"\n" + "\n".join(their_fruit_values) + "" if their_fruit_values else "*No values available*",
                        inline=True
                    )
                
                embed.add_field(
                        name="Your Total Values: ",
                        value=f"{emoji_data['beli'][0]}{'{:,}'.format(output_dict['Your_TotalValue'])} " if output_dict['Your_TotalValue'] else "*No values available*",
                        inline=False
                    )
                
                embed.add_field(
                        name="Their Total Values: ",
                        value=f"{emoji_data['beli'][0]}{'{:,}'.format(output_dict['Their_TotalValue'])} " if output_dict['Their_TotalValue'] else "*No values available*",
                        inline=False
                    )

                if(percentage_calculation != "Invalid input. Please enter numerical values."):
                        embed.add_field(name=percentage_calculation,
                        value="",
                        inline=False)

                embed.add_field(name="",
                value=f"[{server_name}]({server_invite_link})",
                inline=False)

                _w_or_l_channel = self.get_channel(w_or_l_channel_id)
                if message.channel == _w_or_l_channel:
                    await message.reply(embed=embed)   

        
bot = MyBot()

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
                    colour=embed_color_code)

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