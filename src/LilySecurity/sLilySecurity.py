import discord
from discord.ext import commands
from collections import deque

security_info = {
    'channel_deletion_limit' : 3,
    'channel_deletion_cooldown' : 8,
    'role_deletion_limit' : 3,
    'role_deletion_cooldown' : 8
}


async def SecurityEvaluate(self, bot, message):
    pass