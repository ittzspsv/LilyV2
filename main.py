import os
import asyncio
import logging

from dotenv import load_dotenv
from src.lily import Lily

from discord.ext import commands
import discord

load_dotenv("token.env")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("lily")
async def lily_bot():
    bot = Lily()

    token = os.getenv("token")
    if not token:
        raise ValueError("TOKEN environment variable is missing")

    logger.info("Starting Lily")
    await bot.start(token=token)


asyncio.run(lily_bot())