from discord.ext import commands
from typing import Optional
from ..core.logging.lily_logging import LilyLoggingController


class LilyLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controller: Optional[LilyLoggingController] = None

    async def on_load(self):
        self.controller = LilyLoggingController(self.bot.db)


async def setup(bot):
    cog = LilyLogging(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()