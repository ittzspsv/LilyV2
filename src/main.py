import os
from typing import Optional

import aiohttp
import discord
from discord.ext import commands, tasks

import core.configs.sBotDetails as Config

from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.database.integrations.logging import LoggingDatabase
from core.logging.lily_logging import LilyLoggingController
from core.utils.embeds.sLilyEmbed import simple_embed
from core.features.agents.controller.lily_agent_controller import LilyAgentController
    
from dotenv import load_dotenv

load_dotenv("token.env")

class Lily(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.presences = False
        intents.members = False
        intents.message_content = True

        self.lily_session = None
        self.db: Optional[BotGlobalsDatabaseAccess] = None
        self.logs_db: Optional[LoggingDatabase] = None
        self.logging_controller: Optional[LilyLoggingController] = None
        self.agent_controller: LilyAgentController = LilyAgentController()

        super().__init__(command_prefix=self.prefix,intents=intents,help_command=None)

    async def setup_hook(self):
        """ Bot Globals Database """
        self.db = await BotGlobalsDatabaseAccess.connect("storage/configs/Configs.db")
        self.logs_db = await LoggingDatabase.connect("storage/logs/Logs.db")
        self.logging_controller = LilyLoggingController(self.db, self.logs_db)
        self.logs_db.bot_db = self.db

        extensions = [
            "commands.moderation",
            "commands.utility",
            "commands.blox_fruits",
            "commands.management",
            "commands.ticket_tool"
            #"LilyLeveling.sLilyLevelingCommands",
            #"LilyMusic.sLilyMusicCommands",
        ]

        for e, ext in enumerate(extensions):
            if ext not in self.extensions:
                try:
                    await self.load_extension(ext)
                except Exception as e:
                    print(e)

        self.lily_session = aiohttp.ClientSession()
        await self.tree.sync()
    
    def prefix(self, bot: commands.Bot ,message):
        if not message.guild:
            return Config.bot_command_prefix
        
        if self.db is None:
            return "."
        return self.db.get_prefix(message.guild.id)

    async def on_ready(self):
        print('Logged on as', self.user)
        
        await self.modify_status.start()

    async def on_guild_join(self, guild: discord.Guild):
        if self.db is not None:
            await self.db.guild_initialize(guild.id)

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
        
        await self.agent_controller.on_message(self, message=message)
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply(embed=simple_embed(str(error), 'cross'))

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(embed=simple_embed(f"So fast! Try again after {error.retry_after:.1f} seconds.", 'cross'))
        else:
            pass

bot = Lily()

bot.run(token=os.getenv("token") or "")