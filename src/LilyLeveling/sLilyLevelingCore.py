import aiosqlite
import asyncio
import json
import LilyModeration.sLilyModeration as mLily
import ui.sProfileCardGenerator as PCG
import discord
import Config.sBotDetails as BotConfig
from discord.ext import commands
from datetime import datetime, timedelta

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

async def LevelProcessor(message: discord.Message):
    if message.author.bot:
        return
    if message.content.startswith(BotConfig.bot_command_prefix):
        return

    await exp_queue.put((str(message.guild.id), str(message.author.id), 10))
    global exp_worker_running
    if not exp_worker_running:
        asyncio.create_task(_exp_background_worker(message))
        exp_worker_running = True

    await message_count_queue.put((str(message.guild.id), str(message.author.id), int(message.created_at.timestamp())))
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
        await ctx.reply(embed=mLily.SimpleEmbed('Cannot Fetch your Level, Please Speak Atleast Once!', 'cross'))    
        print(e)       

async def _exp_background_worker(message: discord.Message):
    global exp_worker_running

    MAX_LEVEL = config.get("Max_Level", 1000)
    MAX_SQLITE_INT = 9223372036854775807

    while exp_queue.qsize() > 0:
        updates = {}

        while not exp_queue.empty():
            guild_id, user_id, exp = await exp_queue.get()
            key = (guild_id, user_id)
            updates[key] = updates.get(key, 0) + exp

        for (guild_id, user_id), exp_gain in updates.items():
            cursor = await ldb.execute("""
                SELECT Current_Level, Level_Exp, Max_Level_Exp, Coins
                FROM levels
                WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()

            if row:
                level, exp_now, max_exp, coins = row
            else:
                level, exp_now, max_exp, coins = 0, 0, 100, 1000
                await ldb.execute("""
                    INSERT INTO levels (Guild_ID, User_ID, Current_Level, Level_Exp, Max_Level_Exp, Coins)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, user_id, level, exp_now, max_exp, coins))

            exp_now += exp_gain

            while exp_now >= max_exp and level < MAX_LEVEL:
                exp_now -= max_exp
                level += 1
                max_exp = int(max_exp * config['Exp_Multiplier'])

                if max_exp > MAX_SQLITE_INT:
                    max_exp = MAX_SQLITE_INT
                    break

                coins += int(config['coins_minimum'] * (1 + (level * 0.1)))

            if level >= MAX_LEVEL:
                exp_now = min(exp_now, max_exp)

            await ldb.execute("""
                UPDATE levels
                SET Current_Level = ?, Level_Exp = ?, Max_Level_Exp = ?, Coins = ?
                WHERE Guild_ID = ? AND User_ID = ?
            """, (level, exp_now, max_exp, coins, guild_id, user_id))

            guild_config = config.get("Guilds", {}).get(str(guild_id))
            if guild_config:
                guild = message.client.get_guild(int(guild_id))
                member = guild.get_member(int(user_id)) if guild else None

                if member:
                    for role_id, required_level in guild_config.items():
                        if int(required_level) == level:
                            role = guild.get_role(int(role_id))
                            if role and role not in member.roles:
                                try:
                                    await member.add_roles(role, reason="Level-up reward")
                                except discord.Forbidden:
                                    print(f"Missing permissions to assign role {role.name} to {member}.")
                                except discord.HTTPException as e:
                                    print(f"Failed to assign role {role.name}: {e}")

        await ldb.commit()
        await asyncio.sleep(5)

    exp_worker_running = False

async def _message_count_worker():
    global message_worker_running

    while message_count_queue.qsize() > 0:
        updates = {}

        while not message_count_queue.empty():
            guild_id, user_id, timestamp = await message_count_queue.get()
            key = (guild_id, user_id)
            updates[key] = max(updates.get(key, 0), timestamp)

        for (guild_id, user_id), ts in updates.items():
            now = datetime.utcfromtimestamp(ts)
            today_start = datetime(now.year, now.month, now.day)
            week_start = today_start - timedelta(days=now.weekday())
            now_ts = int(now.timestamp())
            today_ts = int(today_start.timestamp())
            week_ts = int(week_start.timestamp())

            cursor = await ldb.execute("""
                SELECT Total, Weekly, Daily, Last_Update FROM message_counts
                WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()

            if row:
                total, weekly, daily, last_update = row
                last_update_dt = datetime.utcfromtimestamp(last_update)

                if last_update_dt.date() != now.date():
                    daily = 0
                if last_update_dt.isocalendar()[1] != now.isocalendar()[1]:
                    weekly = 0

                daily += 1
                weekly += 1
                total += 1

                await ldb.execute("""
                    UPDATE message_counts
                    SET Total = ?, Weekly = ?, Daily = ?, Last_Update = ?
                    WHERE Guild_ID = ? AND User_ID = ?
                """, (total, weekly, daily, now_ts, guild_id, user_id))
            else:
                await ldb.execute("""
                    INSERT INTO message_counts (Guild_ID, User_ID, Total, Weekly, Daily, Last_Update)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, user_id, 1, 1, 1, now_ts))

        await ldb.commit()
        await asyncio.sleep(5)

    message_worker_running = False