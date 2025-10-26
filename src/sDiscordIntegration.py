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
import Config.sValueConfig as ValueConfig
import LilyTicketTool.LilyTicketToolCore as LilyTTCore
import LilyManagement.sLilyStaffManagement as LSM
import LilyPVB.LilyPVBCore as LPVBC
from LilyGAG.sLilyGAGStockListeners import StockWebSocket
import LilySubstring.sLilySubstring as LS
import LilyGAG.sLilyGAGCore as GAG
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
        extensions = [
            "LilyModeration.sLilyModerationCommands",
            "LilyVouch.sLilyVouchCommands",
            "LilyUtility.sLilyUtilityCommands",
            "LilyManagement.sLilyStaffManagementCommands",
            "LilyLogging.sLilyLoggingCommands",
            "LilyBloxFruits.sLilyBloxFruitsCommands",
            "Misc.sLilyEmbedCommands",
            "LilyResponse.sLilyResponseCommands",
            "LilyGAG.sLilyGAGCommands",
            "LilyTicketTool.LilyTicketToolCommands",
            "LilyLeveling.sLilyLevelingCommands",
            # "LilyMiddleman.sLilyMiddlemanCommands"
        ]

        for ext in extensions:
            if ext not in self.extensions:
                await self.load_extension(ext)
        await self.tree.sync()

    async def BotInitialize(self):
        for guild in self.guilds:
                await self.MemoryButtonSetup(guild)
        guild_ids = [(guild.id,) for guild in self.guilds]
        await ValueConfig.cdb.executemany(
            "INSERT OR IGNORE INTO ConfigData (guild_id) VALUES (?)",
            guild_ids
        )
        await ValueConfig.cdb.commit()

    async def MemoryButtonSetup(self, Guild: discord.Guild):
        try:
            cursor = await ValueConfig.cdb.execute(
                "SELECT MemoryButton FROM ConfigData WHERE guild_id = ?",
                (Guild.id,)
            )
            row = await cursor.fetchone()
        except Exception as e:
            print(f"Database error during MemoryButtonSetup: {e}")
            return

        if not row or not row[0]:
            return

        try:
            all_views = json.loads(row[0])
        except json.JSONDecodeError:
            await ValueConfig.cdb.execute(
                """
                INSERT INTO ConfigData (guild_id, MemoryButton)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET MemoryButton = excluded.MemoryButton
                """,
                (Guild.id, "[]")
            )
            await ValueConfig.cdb.commit()
            return

        if not all_views:
            return

        valid_views = []
        bot = self

        for view_data in all_views:
            channel_id = view_data.get("channel_id")
            message_id = view_data.get("message_id")
            buttons_data = view_data.get("buttons", [])

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            try:
                message = await channel.fetch_message(message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
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

        try:
            await ValueConfig.cdb.execute(
                """
                INSERT INTO ConfigData (guild_id, MemoryButton)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET MemoryButton = excluded.MemoryButton
                """,
                (Guild.id, json.dumps(valid_views, indent=4))
            )
            await ValueConfig.cdb.commit()
        except Exception as e:
            print(f"Failed to update valid views in DB: {e}")

    async def ConnectDatabase(self):
        await LilyLogging.initialize()
        await LilyLeveling.initialize()
        await LSM.initialize()
        await ValueConfig.initialize()

    async def on_ready(self):
        print('Logged on as', self.user)   
        await self.ConnectDatabase()
        await self.BotInitialize()
        await LilyTTCore.InitializeView(self)
        await bot.change_presence(
        activity=discord.Streaming(
            name="Gate to Oblivion",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1"
        )
    )
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
        
    async def PostCV2View(self, View, channel_id):
        channel = self.get_channel(channel_id)
        try:
            await channel.send(view=View, file=discord.File("src/ui/Border.png", filename="border.png"))
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

        await LPVBC.MessageEvaluate(self, bot, message)
        
        response_text_parsing = ["{user.name}", "{server}"]
        response_conditions = ["{<hasroll > ? hii : you dont have the role yet}", "{<isuser> ? hii : you dont have the role yet}"]
       
        await self.process_commands(message)

bot = MyBot()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(f"Exception {error}")
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"So fast Try after {error.retry_after:.1f} seconds.")
    else:
        pass

@bot.event
async def on_presence_update(before, after):
    try:
        await LS.on_presence_update(before, after)
    except:
        pass

@PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
@bot.command()
async def configure(ctx: commands.Context):
    text = await Config.update_config_data()
    await ctx.send(embed=mLily.SimpleEmbed(f'Updated bot config with code : {text}'))

load_dotenv("token.env")

bot.run(os.getenv("token"))

'''
async def main():
    await asyncio.gather(
        
    )

asyncio.run(main())'''
