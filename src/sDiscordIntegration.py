import discord
from discord.ext import commands, tasks
import Config.sBotDetails as Config

import LilyTicketTool.LilyTicketToolCore as LTTC
import LilyModeration.sLilyModeration as mLily
import LilyBloxFruits.sLilyBloxFruitsCore as LBFC
import aiohttp
import LilyLeveling.sLilyLevelingCore as LilyLeveling
import Config.sValueConfig as ValueConfig
import os
import logging
import LilySecurity.sLilySecurity as LilySecurity
import LilyUtility.sLilyGreetings as LG
import LilyTicketTool.LilyTicketToolThread as LTTT


import os
import re
import asyncio
from urllib.parse import quote
import json
    
from dotenv import load_dotenv

logging.basicConfig(filename='storage/LilyLogs.txt', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.presences = False
        intents.members = False
        super().__init__(command_prefix=Config.bot_command_prefix,intents=intents,help_command=None)

    async def setup_hook(self):
        extensions = [
            "LilyModeration.sLilyModerationCommands",
            "LilyUtility.sLilyUtilityCommands",
            "LilyManagement.sLilyStaffManagementCommands",
            "LilyLogging.sLilyLoggingCommands",
            "LilyBloxFruits.sLilyBloxFruitsCommands",
            "Misc.sLilyEmbedCommands",
            # "LilyGAG.sLilyGAGCommands",
            "LilyTicketTool.LilyTicketToolCommands",
            "LilyLeveling.sLilyLevelingCommands",
            # "LilyMiddleman.sLilyMiddlemanCommands"
            "LilyMusic.sLilyMusicCommands",
            "LilyForge.LilyForgeCommands",
            "LilyGTO.LilyGTOCommands",
            #"LilyVouching.LilyVouchingCommands"
        ]

        for ext in extensions:
            if ext not in self.extensions:
                await self.load_extension(ext)
        await self.tree.sync()

    async def BotInitialize(self):
        guild_ids = [(guild.id,) for guild in self.guilds]
        await ValueConfig.cdb.executemany(
            "INSERT OR IGNORE INTO ConfigData (guild_id) VALUES (?)",
            guild_ids
        )
        await ValueConfig.cdb.commit()
    async def ConnectDatabase(self):
        await ValueConfig.initialize()

    async def on_ready(self):
        print('Logged on as', self.user)   
        await self.ConnectDatabase()
        await self.BotInitialize()
        #await LVC.Initialize()
        await self.ModifyStatus.start()

    @tasks.loop(minutes=60)
    async def ModifyStatus(self):
        member_count = 0
        for guild in bot.guilds:
            member_count += guild.member_count
            activity = discord.Activity(type=discord.ActivityType.watching, name=f"{member_count:,} members!")
        await bot.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        asyncio.create_task(self.BotInitialize())
 
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

    async def ListenDirectMessage(self, message: discord.Message):
        webhook_url = "https://discord.com/api/webhooks/xxxxxxxxx"
        try:
            await self.lily_session.post(
                    webhook_url,
                    json={
                        "content" : f'{message.content}',
                        "username" : message.author.name,
                        "avatar_url" : message.author.display_avatar.url
                    }
                )
        except discord.errors.HTTPException as e:
            print("Exception [ListenDirectMessage] {e}")

    async def on_message(self, message:discord.Message): 
        if message.author == self.user:
              return         

        await LilySecurity.LilySecurityEvaluate(message)

        if message.channel.id in LilyLeveling.config['AllowedChannels']:
            await LilyLeveling.LevelProcessor(message)

        if isinstance(message.channel, discord.DMChannel):
            await self.ListenDirectMessage(message)

        await LBFC.MessageEvaluate(bot, message)
        await self.process_commands(message)

    async def on_member_join(self, member: discord.Member):
        await LG.PostWelcomeGreeting(self, member)
        #await LSecurity.LilySecurityJoinWindow(bot, member)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        pass
        #await LSecurity.LilyEventActionChannelDelete(channel)

    async def on_guild_role_delete(self, role: discord.Role):
        pass
        #await LSecurity.LilyEventActionRoleDelete(role)

bot = MyBot()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(f"Error [ON COMMAND ERROR] {error}")
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"So fast Try after {error.retry_after:.1f} seconds.")
    else:
        pass


load_dotenv("token.env")

bot.run(os.getenv("token"))
