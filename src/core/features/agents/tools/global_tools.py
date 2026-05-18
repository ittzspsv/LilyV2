from lily_agent import tool
from pydantic import BaseModel, Field
from typing import Optional

from ..data.overload_data import OverloadData
from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess

import discord


class SetPrefix(BaseModel):
    prefix: str = Field(..., description="Bot command prefix (e.g., ?, !)")

class GetPrefix(BaseModel):
    name: str = Field(..., description="Default that to Lily!")


@tool(description="Set the bot's prefix", parameters=SetPrefix, overload=True)
async def set_prefix(prefix: str, data: OverloadData):
    bot_db: Optional[BotGlobalsDatabaseAccess] = data.bot.db
    message: discord.Message = data.message

    if bot_db is None or message.guild is None:
        return "An unknown error occured! Database cannot be accessed!"

    await bot_db.set_prefix(message.guild.id, prefix)
    return f"Successfully Updated prefix to {prefix}"

@tool(description="Get the bot prefix", parameters=GetPrefix, overload=True)
async def get_prefix(name: str, data: OverloadData):
    bot_db: Optional[BotGlobalsDatabaseAccess] = data.bot.db
    message: discord.Message = data.message

    if bot_db is None or message.guild is None:
        return "An unknown error occured!"
    
    prefix = bot_db.get_prefix(message.guild.id)
    return f"The prefix for using the bot is `{prefix}`"