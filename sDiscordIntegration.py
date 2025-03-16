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

fruit_names = [fruit["name"].lower() for fruit in value_data]

ist = pytz.timezone('Asia/Kolkata')

# Based on Indian Standard Time and 10 mins waiting for correct fetch BASED ON INTERNATIONAL TIMESCALINGS
update_times = [
    (5, 40),
    (9, 40),
    (13, 40),
    (17, 40),
    (21, 40),
    (1, 40)
]

mirage_update_times = [
    (3, 40),
    (7, 40),
    (11, 40),
    (15, 40),
    (19, 40),
    (23, 40)
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
            normal_stock_data = get_normal_stock()
            temp_stock = []
            if isinstance(normal_stock_data, dict) and normal_stock_data:
                #await message.channel.send("# NORMAL STOCK")
                for fruit, details in normal_stock_data.items():
                    temp_stock.append(fruit)
                    stock_display = ", ".join(details['Stock Type'])
                    printable_string += f"\n- {emoji_data[fruit]} **{fruit}**  {emoji_data['beli']}{details['Value'].replace('$', '')}"
                    #await message.channel.send(f"**{fruit}**- **Value** = {details['Value']}, **Stock Type** - {stock_display}")

                for fruit, details in normal_stock_data.items():
                    if fruit in good_fruits:
                        current_good_fruits_n.append(fruit)
                
                if temp_stock == previous_normal_stock_fruits:
                    #await Channel.send("Repeatation Of Stock")
                    await asyncio.sleep(2)
                    await self.check_time_and_post()
                    return

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

                    previous_normal_stock_fruits.clear()
                    previous_normal_stock_fruits.extend(temp_stock)

    async def mirage_stock(self, Channel):
            #Mirage stock
            mirage_stock_data = get_mirage_stock()
            current_good_fruits_m = []
            temp_m_stock = []
            printable_string2 = ""
            if isinstance(mirage_stock_data, dict) and mirage_stock_data:
                #await message.channel.send("# MIRAGE STOCK")
                for fruit, details in mirage_stock_data.items():
                    temp_m_stock.append(fruit)
                    stock_display = ", ".join(details['Stock Type'])
                    printable_string2 += f"\n- {emoji_data[fruit]} **{fruit}**  {emoji_data['beli']}{details['Value'].replace('$', '')}" 
                    #await message.channel.send(f"**{fruit}** **Value** = {details['Value']}, **Stock Type** - {stock_display}")

                for fruit, details in mirage_stock_data.items():
                    if fruit in good_fruits:
                        current_good_fruits_m.append(fruit)

                if temp_m_stock == previous_mirage_stock_fruits:
                    await asyncio.sleep(2)
                    await self.check_time_and_post()
                    #await Channel.send("Repeatation of stock")
                    return
                
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

                previous_mirage_stock_fruits.clear()
                previous_mirage_stock_fruits.extend(temp_m_stock)

    async def check_time_and_post(self):
            await bot.wait_until_ready()
            channel = bot.get_channel(stock_update_channel_id)

            '''if channel:
                if stock_fetch_type == 0:
                    await self.normal_stock(channel)
                    await self.mirage_stock(channel)
                else:
                    await self.vNormal_stock(channel)
                    await self.vMirage_stock(channel)'''

            while not self.is_closed():
                delay = 2


                # Get the current IST time
                now = datetime.now()
                current_time = (now.hour, now.minute)

                # Check if current time matches any update time
                if current_time in update_times:
                    await self.normal_stock(channel)

                    #after posting the stock let skip the current time
                    delay = 60
                    

                else:
                    delay = 2 

                if current_time in mirage_update_times:
                    await self.mirage_stock(channel)
                        
                    #after posting the stock let skip the current time
                    delay = 60
                else:
                    delay = 2
                await asyncio.sleep(delay)
            
    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
              return

        elif re.search(r"\b(fruit value of|value of)\b", message.content.lower()):
            match = re.search(r"\b(?:fruit value of|value of)\s+(.+)", message.content.lower())
            if match:
                    item_name = match.group(1).strip()
                    item_name = re.sub(r"^(perm|permanent)\s+", "", item_name).strip()
                    item_name_capital = item_name.title()
                    print(item_name_capital)
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

                your_fruits, your_fruit_types, their_fruits, their_fruits_types = extract_trade_details(message.content)
                output_dict = j_LorW(your_fruits, your_fruit_types, their_fruits, their_fruits_types)
                #await message.channel.send(resultant)
                if isinstance(output_dict, dict):

                    percentage_calculation = calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                
                    embed = discord.Embed(title=output_dict["TradeConclusion"],
                        description= output_dict["TradeDescription"],
                        colour=0xc2004e,)

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

            output_dict = j_LorW(your_fruitss, your_fruit_typess, their_fruitss, their_fruits_typess)
            if(isinstance(output_dict, dict)):
                percentage_calculation = calculate_win_loss(output_dict["Your_TotalValue"], output_dict["Their_TotalValue"])
                
                embed = discord.Embed(title=output_dict["TradeConclusion"],
                        description= output_dict["TradeDescription"],
                        colour=0xc2004e,)

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
                        value=f"{emoji_data['beli']}{'{:,}'.format(output_dict['Your_TotalValue'])} " if output_dict['Your_TotalValue'] else "*No values available*",
                        inline=False
                    )
                
                embed.add_field(
                        name="Their Total Values: ",
                        value=f"{emoji_data['beli']}{'{:,}'.format(output_dict['Their_TotalValue'])} " if output_dict['Their_TotalValue'] else "*No values available*",
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