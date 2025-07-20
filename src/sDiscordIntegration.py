import discord
from discord.ext import commands
import Config.sBotDetails as Config
from LilyRulesets.sLilyRulesets import PermissionEvaluator

import LilyModeration.sLilyModeration as mLily
import Misc.sLilyEmbed as LilyEmbed
import LilyBloxFruits.sLilyBloxFruitsCore as LBFC
import LilyResponse.sLilyResponse as aiLily
import LilyGAG.sLilyGAGCore as LGAG
import LilyLeveling.sLilyLevelingCore as LilyLeveling
import LilyLogging.sLilyLogging as LilyLogging
import LilyTicketTool.LilyTicketToolCore as LilyTTCore
from LilyGAG.sLilyGAGStockListeners import StockWebSocket
import ui.sWantedPoster as WP
import logging


import os
import asyncio
from urllib.parse import quote
import json
    
import re
from dotenv import load_dotenv

logging.basicConfig(filename='storage/LilyLogs.txt', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.message_content = True
        intents.members = True
        intents.presences = True 
        intents.guilds = True
        super().__init__(command_prefix=Config.bot_command_prefix,intents=discord.Intents.all())

    async def setup_hook(self):
        await bot.load_extension("LilyModeration.sLilyModerationCommands")
        await bot.load_extension("LilyVouch.sLilyVouchCommands")
        await bot.load_extension("LilyUtility.sLilyUtilityCommands")
        await bot.load_extension("LilyManagement.sLilyStaffManagementCommands")
        await bot.load_extension("LilyLogging.sLilyLoggingCommands")
        await bot.load_extension("LilyBloxFruits.sLilyBloxFruitsCommands")
        await bot.load_extension("Misc.sLilyEmbedCommands")
        await bot.load_extension("LilyResponse.sLilyResponseCommands")
        await bot.load_extension("LilyGAG.sLilyGAGCommands")
        await bot.load_extension("LilyTicketTool.LilyTicketToolCommands")
        await bot.load_extension("LilyLeveling.sLilyLevelingCommands")
        await bot.tree.sync()

    async def BotStorageInitialization(self, guild):
        base_path = f"storage/{guild.id}"
        directories = [
            f"storage/common/Comboes",
            base_path,
            f"{base_path}/modlogs",
            f"{base_path}/botlogs",
            f"{base_path}/configs",
            f"{base_path}/sessions",
            f"{base_path}/stafflogs",
            f"{base_path}/vouches",
            f"{base_path}/vcmutelogs",
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        config_files = {
            f"{base_path}/configs/assignable_roles.json": {},
            f"{base_path}/configs/configs.json" : {},
            f"{base_path}/configs/blacklisted_mods.json": {},
            f"{base_path}/sessions/ButtonSessionMemory.json": {},
            f"{base_path}/configs/configs.json" : {}
        }

        for file_path, default_data in config_files.items():
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    json.dump(default_data, f)
                pass
                #print(f"Created file: {file_path}")
            else:
                pass
                #print(f"File exists: {file_path} — Skipped")
        print(f"Initialized {guild.name}")

    async def BotInitialize(self):
        for guild in self.guilds:
                await self.BotStorageInitialization(guild)
                await self.MemoryButtonSetup(guild)

    async def MemoryButtonSetup(self, Guild: discord.Guild):
        ButtonSessionMemory = f"storage/{Guild.id}/sessions/ButtonSessionMemory.json"
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

    async def ConnectDatabase(self):
        await LilyLogging.initialize()
        await LilyLeveling.initialize()

    async def on_ready(self):
        print('Logged on as', self.user)   
        await self.BotInitialize()
        await LilyTTCore.InitializeView(self)
        game = discord.Streaming(name="Gate to Oblivion", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        await bot.change_presence(status=discord.Status.idle, activity=game)
        await self.ConnectDatabase()
        handler = StockWebSocket(f"wss://websocket.joshlei.com/growagarden?user_id={quote("834771588157517581")}", bot)
        asyncio.create_task(handler.run())    
        await self.tree.sync()

    async def on_guild_join(self, guild):
        asyncio.create_task(self.BotInitialize())

    async def on_guild_channel_create(self, channel):
        feature_cache = open("src/Config/BotFeatures.txt", "r")
        feature_int = feature_cache.read()
        if int(feature_int) == 0:
            return
        if isinstance(channel, discord.TextChannel):
            if LilyEmbed.TicketParseRegex.match(channel.name):
                print(f"Ticket channel created: {channel.name}")
                try:
                    await asyncio.sleep(1.5)
                    async for message in channel.history(oldest_first=False):
                        if message.author.bot and message.embeds and message.content:
                            ticket_opener_id, reason, scammer_match = LilyEmbed.ParseTicketEmbed(message)
                            response_text, channel_id, delete_message, emoji_to_react, medias = aiLily.get_response(reason)
                            if response_text:
                                await channel.send(f"<@{ticket_opener_id}> {response_text}")

                except Exception as e:
                    print(f"Exception here: {e}")

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        try:
            await mLily.VerifyVMute(self, bot, member, before, after)
        except Exception as e:
            return
    
    async def has_role(self, user, role_id):
        role = discord.utils.get(user.roles, id=int(role_id))
        return role is not None

    async def is_user(self, user, user_id):
        return user.id == int(user_id)  

    async def PostStock(self, stock_type, stock_msg: str, channel_id, pings):
        embed = discord.Embed(title=stock_type,
                      description=stock_msg, colour=0x2b00ff)
        embed.set_author("BloxTrade | Grow a garden Stocks")
        file = discord.File("src/ui/Border.png", filename="border.png")
        embed.set_image(url="attachment://border.png")
        channel = self.get_channel(channel_id)
        try:
            await channel.send(embed=embed, content=" ".join(pings), file=file)
        except:
            return
        
    async def PostStockAdvanced(self, seed_stock_msg:str, gear_stock_msg:str, channel_id, pings):
        embed = discord.Embed(title="STOCK",colour=0x2b00ff)
        embed.set_author("BloxTrade | Grow a garden Stocks")
        embed.add_field(name="🌱SEED STOCK",
                value=seed_stock_msg,
                inline=True)
        embed.add_field(name="⚙️ GEAR STOCK",
                        value=gear_stock_msg,
                        inline=True)
        file = discord.File("src/ui/Border.png", filename="border.png")
        embed.set_image(url="attachment://border.png")
        channel = self.get_channel(channel_id)
        try:
            await channel.send(embed=embed, content=" ".join(pings), file=file)
        except:
            return

    async def ConditionEvaluator(self, user, condition):
        match = re.match(r'<(hasrole|isuser) (\d+)> \? (.+) : (.+)', condition)
        if match:
            check_type, check_value, true_value, false_value = match.groups()

            if check_type == 'hasrole':
                if await bot.has_role(user, check_value):
                    return true_value
                else:
                    return false_value
            elif check_type == 'isuser':
                if await bot.is_user(user, check_value):
                    return true_value
                else:
                    return false_value
        return condition

    async def RespondProcessor(self, message):
        try:
            feature_cache = open("src/Config/BotFeatures.txt", "r")
            feature_int = feature_cache.read()
            print(feature_int)
        except Exception as e:
            feature_int = 0
        if int(feature_int) == 0:
                return
        response_text, channel_id, delete_message, emoji_to_react, medias,whitelist_roles = aiLily.get_response(message.content)
        if response_text and (message.channel.id in channel_id or re.match(r"^ticket-\d{4}$", message.channel.name)):
            if any(role.id in whitelist_roles for role in message.author.roles):
                return
            response_text = re.sub(r'\{user\.name}', message.author.name, response_text)

            conditions = re.findall(r'\{(<(hasrole|isuser) \d+> \? .*? : .*?)\}', response_text)
            for condition_tuple in conditions:
                condition = condition_tuple[0]
                evaluated_value = await bot.ConditionEvaluator(message.author, condition)
                response_text = response_text.replace(f'{{{condition}}}', evaluated_value)

            for media in medias:
                    m_parser = media.split("=")
                    if "img" in m_parser:
                        try:
                            imglink = m_parser[1]
                        except Exception as e:
                            imglink = ""
                    if "gif" in m_parser:
                        try:
                            giflink = m_parser[1]
                        except Exception as e:
                            giflink = ""
            if delete_message.lower() == "false":
                for emoji in emoji_to_react:
                    try:
                        await message.add_reaction(emoji)
                    except discord.HTTPException as e:
                        print(f"Failed to add reaction {emoji}: {e}")
                await message.reply(f'{response_text}')
                try:
                    await message.channel.send(giflink)
                except:
                    pass
            else:
                await message.delete()
                await message.channel.send(f"{message.author.mention} {response_text}")
                try:
                    await message.channel.send(giflink)
                except Exception as e:
                    print(e)

    async def on_message(self, message:discord.Message): 
        if message.author == self.user:
              return         

        if message.channel.id in LilyLeveling.config['AllowedChannels']:
            await LilyLeveling.LevelProcessor(message)

        await bot.RespondProcessor(message) 
          
        await LBFC.MessageEvaluate(self, bot, message)

        await LGAG.MessageEvaluate(self, bot, message)
        
        response_text_parsing = ["{user.name}", "{server}"]
        response_conditions = ["{<hasroll > ? hii : you dont have the role yet}", "{<isuser> ? hii : you dont have the role yet}"]
       
        await self.process_commands(message)

bot = MyBot()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=mLily.SimpleEmbed(f"Exception {error}"))
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=mLily.SimpleEmbed(f"So fast Try after {error.retry_after:.1f} seconds."))
    else:
        await ctx.send(embed=mLily.SimpleEmbed(f"Exception {error}"))

@PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
@bot.command()
async def configure(ctx: commands.Context):
    text = await Config.update_config_data()
    await ctx.send(embed=mLily.SimpleEmbed(f'Updated bot config with code : {text}'))

load_dotenv("token.env")
bot.run(os.getenv("token"))