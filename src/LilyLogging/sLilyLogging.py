from datetime import datetime

from discord.ext import commands
import discord
import aiosqlite
import pytz

bdb = None
mdb = None

async def initialize():
    global bdb, mdb
    bdb = await aiosqlite.connect("storage/logs/BotLogs.db")
    mdb = await aiosqlite.connect("storage/logs/Modlogs.db")
    await bdb.execute("""
        CREATE TABLE IF NOT EXISTS botlogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            timestamp TEXT,
            log TEXT
        )
    """)
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
    await bdb.commit()
    await mdb.commit()


async def WriteLog(ctx: commands.Context, user_id: int, log_txt: str):
    global bdb
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await bdb.execute("""
        INSERT INTO botlogs (guild_id, user_id, timestamp, log)
        VALUES (?, ?, ?, ?)
    """, (ctx.guild.id, user_id, timestamp, log_txt))

    await bdb.commit()

async def LogModerationAction(ctx: commands.Context, moderator_id: int, target_user_id: int, mod_type: str, reason: str = "No reason provided"):
    global mdb
    timestamp = datetime.now(pytz.utc).isoformat()

    await mdb.execute("""
        INSERT INTO modlogs (guild_id, moderator_id, target_user_id, mod_type, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ctx.guild.id, moderator_id, target_user_id, mod_type.lower(), reason, timestamp))

    await mdb.commit()

async def PostLog(ctx: commands.Context, embed: discord.Embed):
    channel = ctx.bot.get_channel(1325204537434312856)

    if channel is None:
        channel = await ctx.bot.fetch_channel(1325204537434312856)

    await channel.send(embed=embed)
