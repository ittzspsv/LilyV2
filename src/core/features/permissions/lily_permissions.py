from __future__ import annotations

from discord.ext import commands
from ...database.integrations.bot_globals import BotGlobalsDatabaseAccess
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import Lily

import discord

def permission(command_name: str, restrict: bool = False):
    def decorator(func):
        async def predicate(ctx: commands.Context): 
            """ Permission based commands cannot be executed throu' bot DM """
            if ctx.guild is None or isinstance(ctx.author, discord.User):
                return False

            if ctx.author.id in (1488556914605428988, 798533737943138314, 999309816914792630):
                return True
            
            """ Guild owners and administrators have access to any commands, unless restrict = False """
            if ctx.author.id == ctx.guild.owner_id:
                if restrict:
                    raise commands.CheckFailure("You are restricted from using this command")
                return True

            if ctx.author.guild_permissions.administrator:
                if restrict:
                    raise commands.CheckFailure("You are restricted from using this command")
                return True
                


            """ Normal permission checking based on commands """
            bot: "Lily" = ctx.bot
            db: Optional[BotGlobalsDatabaseAccess] = bot.db

            if db is None:
                raise commands.CheckFailure("Database Initialization error")
                        
            
            role_ids = [role.id for role in ctx.author.roles]

            has_perm = db.has_permission(
                ctx.guild.id,
                command_name,
                role_ids
            )

            if restrict:
                if has_perm:
                    raise commands.CheckFailure("You are restricted from using this command.")
                return True
            else:
                if not has_perm:
                    raise commands.CheckFailure("Required role missing.")
                return True

        return commands.check(predicate)(func)
    return decorator