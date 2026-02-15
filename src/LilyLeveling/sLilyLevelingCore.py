import aiosqlite
import asyncio
import json
import re
import LilyModeration.sLilyModeration as mLily
import ui.sProfileCardGenerator as PCG
import discord
import Config.sBotDetails as BotConfig
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import Misc.sLilyEmbed as LE

ldb = None
config = {}
exp_queue = asyncio.Queue()
exp_worker_running = False

message_count_queue = asyncio.Queue()
message_worker_running = False

async def initialize():
    global ldb
    ldb = await aiosqlite.connect("storage/levels/Levels.db")

def InitializeConfig():
    global config
    try:
        with open("src/LilyLeveling/LevelingConfig.json", "r") as Config:
            config = json.load(Config)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        config = {}

InitializeConfig()

def ShortNumber(val):
    value = int(val)
    if value >= 1_000_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000_000:.1f}DX"
    elif value >= 1_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000:.1f}NX"
    elif value >= 1_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000:.1f}OX"
    elif value >= 1_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000:.1f}SPX"
    elif value >= 1_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000:.1f}SX"
    elif value >= 1_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000:.1f}QI"
    elif value >= 1_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000:.1f}QT"
    elif value >= 1_000_000_000_000: 
        return f"{value / 1_000_000_000_000:.1f}T"
    elif value >= 1_000_000_000:  
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:  
        return f"{value / 1_000:.1f}k"
    else:
        return str(value)


UTC = timezone.utc

def utcnow():
    return datetime.now(UTC)

def parse(ts: str | None):
    if not ts:
        return None
    return datetime.fromisoformat(ts)

def iso(dt: datetime):
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()

async def LevelProcessor(message: discord.Message):
    if message.author.bot:
        return
    if message.content.startswith(BotConfig.bot_command_prefix):
        return

    await exp_queue.put((message, 10))
    global exp_worker_running
    if not exp_worker_running:
        asyncio.create_task(_exp_background_worker())
        exp_worker_running = True

    await message_count_queue.put((message, int(message.created_at.timestamp())))
    global message_worker_running
    if not message_worker_running:
        asyncio.create_task(_message_count_worker())
        message_worker_running = True

async def SetLevel(ctx:commands.Context, member: discord.Member, new_level: int):
        global ldb
        try:
            guild_id = str(member.guild.id)
            user_id = str(member.id)

            cursor = await ldb.execute("""
                SELECT Current_Level, Level_Exp, Max_Level_Exp, Coins
                FROM levels
                WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()

            if row:
                _, _, _, coins = row
            else:
                coins = 0
                await ldb.execute("""
                    INSERT INTO levels (Guild_ID, User_ID, Current_Level, Level_Exp, Max_Level_Exp, Coins)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, user_id, 0, 0, 100, coins))

            max_exp = 100
            for _ in range(new_level):
                max_exp = int(max_exp * config['Exp_Multiplier'])
                if max_exp > 9223372036854775807:
                    max_exp = 9223372036854775807
                    break

            await ldb.execute("""
                UPDATE levels
                SET Current_Level = ?, Level_Exp = ?, Max_Level_Exp = ?
                WHERE Guild_ID = ? AND User_ID = ?
            """, (new_level, 0, max_exp, guild_id, user_id))

            await ldb.commit()
            await ctx.send(f"Level set to {new_level}")
        except Exception as e:
            await ctx.send(f"Exception {e}")

async def AddCoins(ctx:commands.Context, member: discord.Member, amount: int):
    global ldb
    try:
            guild_id = str(member.guild.id)
            user_id = str(member.id)

            cursor = await ldb.execute("""
                SELECT Coins
                FROM levels
                WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()
            if row:
                coins = row[0]
                coins += amount

                await ldb.execute("""
                UPDATE levels
                SET Coins = ?
                WHERE Guild_ID = ? AND User_ID = ?
            """, (coins, guild_id, user_id))
                
                await ldb.commit()
                await ctx.send(f"{coins} Bounty has been added successfully")
            else:
                await ctx.send("Row not found on database")
                return
    except Exception as e:
            await ctx.send(f"Exception {e}")

async def FetchLevelDetails(ctx: commands.Context, member: discord.Member = None):
    try:
        if member is None:
            member = ctx.author

        cursor = await ldb.execute(
            "SELECT Current_Level, Level_Exp, Max_Level_Exp FROM levels WHERE User_ID = ? AND Guild_ID = ?",
            (str(member.id), str(ctx.guild.id))
        )
        row = await cursor.fetchone()

        if not row:
            return await ctx.reply("No leveling data found for this user.")

        CurrentLevel, LevelEXP, MaxLevelEXP = row

        rank_cursor = await ldb.execute(
            """
            SELECT rank FROM (
                SELECT User_ID,
                       ROW_NUMBER() OVER (ORDER BY Current_Level DESC) AS rank
                FROM levels
                WHERE Guild_ID = ?
            ) WHERE User_ID = ?
            """,
            (str(ctx.guild.id), str(member.id))
        )

        rank_row = await rank_cursor.fetchone()
        rank = rank_row[0] if rank_row else 0

        rank_display = ShortNumber(rank)

        final_buffer = await PCG.CreateLevelCard(
            member,
            member.name,
            rank_display,
            ShortNumber(LevelEXP),
            ShortNumber(MaxLevelEXP),
            str(CurrentLevel)
        )

        file = discord.File(final_buffer, filename="levelcard.png")
        await ctx.reply(file=file)

    except Exception as e:
        await ctx.reply(embed=mLily.SimpleEmbed('Cannot Fetch your Level, Please Chat Atleast Once!', 'cross'))    
        print(e)       

async def FetchProfileDetails(ctx: commands.Context, member: discord.Member = None):
    try:
        if member is None:
            member = ctx.author

        cursor = await ldb.execute(
            "SELECT Daily, Weekly, Total FROM message_counts WHERE Guild_ID = ? AND User_ID = ?",
            (ctx.guild.id, member.id)
        )
        row = await cursor.fetchone()
        daily, weekly, total = row if row else (0, 0, 0)

        cursor1 = await ldb.execute(
            "SELECT Coins FROM levels WHERE Guild_ID = ? AND User_ID = ?",
            (ctx.guild.id, member.id)
        )
        row1 = await cursor1.fetchone()
        coins = row1[0] if row1 else 0

        mode: int = 1 # To DO : Move this to a database.
        if mode == 1:
            final_buffer = await PCG.CreateProfileCard(
                member,
                str(daily),
                str(weekly),
                str(total),
                ShortNumber(int(coins))
            )

            file = discord.File(final_buffer, filename="profile_card.png")
            await ctx.reply(file=file)
        # Lightweight embed pass
        else:
            pass

    except Exception as e:
        await ctx.reply(
            embed=mLily.SimpleEmbed(
                'Cannot Fetch your Profile, Please Chat Atleast Once!',
                'cross'
            )
        )
        print(e)

async def FetchLeaderBoard(ctx: commands.Context, type: str):
    try:
        val = type.lower()

        if val == 'levels':
            cursor = await ldb.execute(
            "SELECT user_id FROM levels WHERE guild_id = ? ORDER BY current_level DESC LIMIT 10",
            (str(ctx.guild.id),)
        )
        elif val == 'total':
            cursor = await ldb.execute(
            "SELECT User_ID FROM message_counts WHERE guild_id = ? ORDER BY total DESC LIMIT 10",
            (str(ctx.guild.id),)
        )
        elif val == 'daily':
            cursor = await ldb.execute(
            "SELECT User_ID FROM message_counts WHERE guild_id = ? ORDER BY daily DESC LIMIT 10",
            (str(ctx.guild.id),)
        )
        elif val == 'weekly':
            cursor = await ldb.execute(
            "SELECT User_ID FROM message_counts WHERE guild_id = ? ORDER BY weekly DESC LIMIT 10",
            (str(ctx.guild.id),)
        )
        rows = await cursor.fetchall()
        await cursor.close()

        if not rows:
            await ctx.reply(embed=mLily.SimpleEmbed('Error Fetching Leaderboard!', 'cross'))
            return

        rank_list = []
        for row in rows:
            user_id = row[0]
            user_member = ctx.guild.get_member(user_id)

            if not user_member:
                try:
                    user_member = await ctx.guild.fetch_member(user_id)
                    await asyncio.sleep(0.5)
                except discord.NotFound:
                    continue

            name = getattr(user_member, "name", None) or str(user_id)
            clean_name = re.sub(r'[^A-Za-z ]+', '', name)
            rank_list.append({'name': clean_name, 'member': user_member})

        if not rank_list:
            await ctx.reply(embed=mLily.SimpleEmbed('No valid members found!', 'cross'))
            return

        final_buffer = await PCG.CreateLeaderBoardCard(rank_list)
        file = discord.File(final_buffer, filename="profile_card.png")
        await ctx.reply(file=file)

    except Exception as e:
        print(f"Exception [LEADERBOARD FETCH] {e}")

async def _exp_background_worker():
    global exp_worker_running
    exp_worker_running = True

    MAX_LEVEL = config.get("Max_Level", 1000)
    MAX_SQLITE_INT = 9223372036854775807
    BASE_MAX_EXP = 100
    EXP_INCREMENT = 50 
    EXP_MULTIPLIER = 1.05
    COINS_BASE = config.get("coins_minimum", 10)

    while not exp_queue.empty():
        queue_msg, exp_gain = await exp_queue.get()
        updates = {(queue_msg.guild.id, queue_msg.author.id): exp_gain}

        await asyncio.sleep(0.05)

        while not exp_queue.empty():
            q_msg, q_exp = await exp_queue.get()
            key = (q_msg.guild.id, q_msg.author.id)
            updates[key] = updates.get(key, 0) + q_exp

        for (guild_id, user_id), exp_total in updates.items():
            cursor = await ldb.execute("""
                SELECT Current_Level, Level_Exp, Max_Level_Exp, Coins
                FROM levels
                WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()

            if row:
                level, exp_now, max_exp, coins = row
            else:
                level, exp_now, max_exp, coins = 0, 0, BASE_MAX_EXP, 1000
                await ldb.execute("""
                    INSERT INTO levels (Guild_ID, User_ID, Current_Level, Level_Exp, Max_Level_Exp, Coins)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, user_id, level, exp_now, max_exp, coins))

            exp_now += exp_total + (0.1 * level)

            while exp_now >= max_exp and level < MAX_LEVEL:
                exp_now -= max_exp
                level += 1

                max_exp = int(max_exp * EXP_MULTIPLIER + EXP_INCREMENT)

                if max_exp > MAX_SQLITE_INT:
                    max_exp = MAX_SQLITE_INT

                coins += int(COINS_BASE * (1 + (level * 0.1)))

            if level >= MAX_LEVEL:
                exp_now = min(exp_now, max_exp)

            await ldb.execute("""
                UPDATE levels
                SET Current_Level = ?, Level_Exp = ?, Max_Level_Exp = ?, Coins = ?
                WHERE Guild_ID = ? AND User_ID = ?
            """, (level, exp_now, max_exp, coins, guild_id, user_id))

        await ldb.commit()

    exp_worker_running = False

async def _message_count_worker():
    global message_worker_running
    message_worker_running = True

    updates = {}

    while True:
        queue_msg, timestamp = await message_count_queue.get()
        key = (queue_msg.guild.id, queue_msg.author.id)
        updates[key] = max(updates.get(key, 0), timestamp)

        while True:
            try:
                q_msg, q_ts = message_count_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            key = (q_msg.guild.id, q_msg.author.id)
            updates[key] = max(updates.get(key, 0), q_ts)

        for (guild_id, user_id), ts in updates.items():
            now_ts = int(ts)
            await ldb.execute("""
                INSERT INTO message_counts (Guild_ID, User_ID, Total, Last_Update, daily, weekly)
                VALUES (?, ?, 1, ?, 1, 1)
                ON CONFLICT(Guild_ID, User_ID) DO UPDATE SET
                    Total = Total + 1,
                    Last_Update = excluded.Last_Update,
                    daily = daily + 1,
                    weekly = weekly + 1
            """, (guild_id, user_id, now_ts))

        await ldb.commit()
        updates.clear()

        if message_count_queue.empty():
            message_worker_running = False
            break