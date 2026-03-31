from datetime import datetime

from discord.ext import commands
import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
import aiosqlite

from typing import Sequence, Optional, Union

import pytz

import LilyUtility.sLilyUtility as LilyUtility
from LilyLogging.components.sLilyLoggingComponents import write_log_embed, moderation_embed

mdb = None

async def initialize():
    global mdb
    mdb = await aiosqlite.connect("storage/logs/Logs.db")
    await mdb.execute("""
        CREATE TABLE IF NOT EXISTS modlogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            moderator_id INTEGER,
            target_user_id INTEGER,
            mod_type TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """)
    await mdb.commit()

async def WriteLog(ctx: commands.Context, user_id: int, log_txt: str):
    global mdb
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await mdb.execute("""
        INSERT INTO botlogs (guild_id, user_id, timestamp, log)
        VALUES (?, ?, ?, ?)
    """, (ctx.guild.id, user_id, timestamp, log_txt))
    await mdb.commit()

    logs_channel: int = VC.guild_configs.get(ctx.guild.id).get("channels").get("logs_channel", 0)

    channel = ctx.bot.get_channel(logs_channel)
    if not channel:
        return

    embed = write_log_embed(timestamp, user_id, log_txt)
    await channel.send(embed=embed)

async def LogModerationAction(ctx: commands.Context,moderator_id: int,target_user_id: int,mod_type: str,reason: str = "No reason provided", proofs: Optional[Sequence[Union[discord.Attachment, str]]] = None) -> None:
    global mdb
    timestamp = datetime.now(pytz.utc).isoformat()

    await mdb.execute("""
        INSERT INTO modlogs (guild_id, moderator_id, target_user_id, mod_type, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ctx.guild.id, moderator_id, target_user_id, mod_type.lower(), reason, timestamp))
    await mdb.commit()

    logs_channel: int = VC.guild_configs.get(ctx.guild.id).get("channels").get("logs_channel", 0)

    channel = ctx.bot.get_channel(logs_channel)
    if not channel:
        return

    embeds_to_send = moderation_embed(moderator_id, target_user_id, mod_type, reason, proofs, LilyUtility.utcnow())
    await channel.send(content=f'<@{target_user_id}>', embeds=embeds_to_send)

async def LogValueAction(ctx: commands.Context,triggered: discord.Member,value_dict: dict):
    try:
        logs_channel: int = VC.guild_configs.get(ctx.guild.id).get("channels").get("logs_channel", 0)

        channel = ctx.bot.get_channel(logs_channel)
        if not channel:
            return

        embed = discord.Embed(
            title="Value Update Information",
            description=f"Updated by {triggered.mention}",
            colour=0xFFFFFF
        )

        for key, value in value_dict.items():
            modified_name = key.replace("_", " ").title()

            if isinstance(value, (list, dict)):
                value = f"```\n{value}\n```"
            elif value is None:
                value = "N/A"
            else:
                value = str(value)

            embed.add_field(
                name=modified_name,
                value=value,
                inline=False
            )

        embed.set_footer(
            text=f"User ID: {triggered.id}"
        )

        await channel.send(content="Value Update Information Logging", embed=embed)

    except Exception as e:
        print(f"[LogValueAction ERROR] {e}")

async def PostLog(ctx: commands.Context, embed: discord.Embed, log_type:str="Default Log Type"):
    try:
        logs_channel: int = VC.guild_configs.get(ctx.guild.id).get("channels").get("logs_channel", 0)

        channel = ctx.bot.get_channel(logs_channel)
        if not channel:
            return

        channel = ctx.guild.get_channel(channel)
        if not channel:
            return

        await channel.send(content=log_type, embed=embed)
    except Exception as e:
        print(f"EXCEPTION [POST LOG ERROR] {e}")