import discord

from discord.ext import commands
from ..core.database.integrations.logging import LoggingDatabase
from typing import Optional
from ..core.logging.lily_logging import LilyLoggingController


import core.configs.sBotDetails as Config

class LilyLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: Optional[LoggingDatabase] = None
        self.controller: Optional[LilyLoggingController] = None

    async def on_load(self):
        self.db = await LoggingDatabase.connect("storage/logs/Logs.db")
        self.controller = LilyLoggingController(self.bot.db, self.db)


async def setup(bot):
    cog = LilyLogging(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()