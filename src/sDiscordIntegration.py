import discord
from discord.ext import commands, tasks
import Config.sBotDetails as Config

import LilyTicketTool.LilyTicketToolCore as LTTC
import LilyModeration.sLilyModeration as mLily
import LilyBloxFruits.sLilyBloxFruitsCore as LBFC
import aiohttp
import Config.sValueConfig as ValueConfig
import os
import logging
import LilySecurity.sLilySecurity as LilySecurity
import LilyUtility.sLilyGreetings as LG

import json
import os


from Misc.sLilyEmbed import simple_embed
    
from dotenv import load_dotenv

class Lily(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.presences = False
        intents.members = False
        intents.message_content = True
        member_cache_flags = discord.MemberCacheFlags.none()

        self.lily_session = None
        super().__init__(command_prefix=Config.bot_command_prefix,intents=intents,help_command=None)#, member_cache_flags=member_cache_flags)

    async def ConnectDatabase(self):
        await ValueConfig.initialize()
        await ValueConfig.initialize_cache()

    async def setup_hook(self):
        extensions = [
            "LilyModeration.sLilyModerationCommands",
            "LilyUtility.sLilyUtilityCommands",
            "LilyManagement.sLilyStaffManagementCommands",
            "LilyLogging.sLilyLoggingCommands",
            "LilyBloxFruits.commands.sLilyBloxFruitsCommands",
            "Misc.sLilyEmbedCommands",
            "LilyTicketTool.LilyTicketToolCommands",
            #"LilyLeveling.sLilyLevelingCommands",
            #"LilyMusic.sLilyMusicCommands",
            "LilyGTO.LilyGTOCommands",
        ]

        for e, ext in enumerate(extensions):
            if ext not in self.extensions:
                try:
                    await self.load_extension(ext)
                except Exception as e:
                    print(e)
        await self.ConnectDatabase()


        self.lily_session = aiohttp.ClientSession()
        await self.tree.sync()

    async def on_ready(self):
        print('Logged on as', self.user)   
        #await LVC.Initialize()
        await self.modify_status.start()

    @tasks.loop(minutes=60)
    async def modify_status(self):
        member_count = 0
        for guild in bot.guilds:
            member_count += guild.member_count
            activity = discord.Activity(type=discord.ActivityType.watching, name=f"{member_count:,} members!")
        await bot.change_presence(activity=activity)

    async def on_message(self, message:discord.Message): 
        if message.author == self.user:
              return         

        await LilySecurity.LilySecurityEvaluate(message)

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

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply(embed=simple_embed(str(error), 'cross'))

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"So fast! Try again after {error.retry_after:.1f} seconds.")

        else:
            pass

bot = Lily()

load_dotenv("token.env")

bot.run(os.getenv("token"))