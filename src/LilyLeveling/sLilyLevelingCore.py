import aiosqlite
import asyncio
import json
import re
import LilyModeration.sLilyModeration as mLily
import ui.sProfileCardGenerator as PCG
import discord
import Config.sBotDetails as BotConfig
from discord.ext import commands
from datetime import datetime, timedelta
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

        final_buffer = await PCG.CreateProfileCard(
            member,
            str(daily),
            str(weekly),
            str(total),
            ShortNumber(int(coins))
        )

        file = discord.File(final_buffer, filename="profile_card.png")
        await ctx.reply(file=file)

    except Exception as e:
        await ctx.reply(
            embed=mLily.SimpleEmbed(
                'Cannot Fetch your Profile, Please Chat Atleast Once!',
                'cross'
            )
        )
        print(e)

async def FetchLeaderBoard(ctx: commands.Context):
    cursor = await ldb.execute(
        "SELECT User_ID FROM levels WHERE Guild_ID = ? ORDER BY Current_Level DESC LIMIT 10",
        (ctx.guild.id,)
    )
    rows = await cursor.fetchall()

    if not rows:
        await ctx.reply(
            embed=mLily.SimpleEmbed(
                'Error Fetching Leaderboard!',
                'cross'
            )
        )
        return

    rank_list = []
    for row in rows:
        user_id = row[0]
        user_member = ctx.guild.get_member(user_id)
        if not user_member:
            try:
                user_member = await ctx.guild.fetch_member(user_id)
            except discord.NotFound:
                continue
        name = re.sub(r'[^A-Za-z ]+', '', user_member.name)
        rank_list.append({'name': user_member.name, 'member': user_member})

    final_buffer = await PCG.CreateLeaderBoardCard(rank_list)
    file = discord.File(final_buffer, filename="profile_card.png")
    await ctx.reply(file=file)

async def _exp_background_worker():
    global exp_worker_running
    exp_worker_running = True

    MAX_LEVEL = config.get("Max_Level", 1000)
    MAX_SQLITE_INT = 9223372036854775807

    while not exp_queue.empty():
        queue_msg, exp = await exp_queue.get()
        updates = {(queue_msg.guild.id, queue_msg.author.id): exp}

        await asyncio.sleep(0.05)

        while not exp_queue.empty():
            q_msg, q_exp = await exp_queue.get()
            key = (q_msg.guild.id, q_msg.author.id)
            updates[key] = updates.get(key, 0) + q_exp

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
                member = queue_msg.guild.get_member(user_id)
                if member:
                    for role_id, required_level in guild_config.items():
                        if int(required_level) == level:
                            role = queue_msg.guild.get_role(int(role_id))
                            if role and role not in member.roles:
                                try:
                                    await member.add_roles(role, reason="Level-up reward")
                                except Exception as e:
                                    print("Role assign failed:", e)

        await ldb.commit()

    exp_worker_running = False

async def daily(ctx: commands.Context):
    try:
        async with ldb.execute("SELECT daily_claim FROM profile WHERE user_id = ?", (ctx.author.id,)) as cursor:
            row = await cursor.fetchone()
            now = datetime.utcnow()

            if row and row[0]:
                last_claim_str = row[0]
                last_claim = datetime.fromisoformat(last_claim_str)
                delta = now - last_claim
                if delta.total_seconds() < 86400:
                    remaining = 86400 - delta.total_seconds()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    embed = discord.Embed(
                        color=16777215,
                        description=f"You already claimed today! Try again in {hours}h {minutes}m.",
                    )
                    await ctx.send(embed=embed)
                    return

            async with ldb.execute("SELECT current_level, coins FROM levels WHERE user_id = ? AND guild_id = ?", 
                                (ctx.author.id, str(ctx.guild.id))) as cursor:
                level_row = await cursor.fetchone()

            level = level_row[0] if level_row else 0
            coins_current = level_row[1] if level_row else 0

            coins_reward = int(config['coins_minimum'] * (1 + level * 0.1))

            if level_row:
                await ldb.execute("UPDATE levels SET coins = coins + ? WHERE user_id = ? AND guild_id = ?",
                                (coins_reward, ctx.author.id, str(ctx.guild.id)))
            else:
                await ldb.execute("INSERT INTO levels (user_id, guild_id, coins) VALUES (?, ?, ?)",
                                (ctx.author.id, str(ctx.guild.id), coins_reward))

            if row:
                await ldb.execute("UPDATE profile SET daily_claim = ? WHERE user_id = ?", (now.isoformat(), ctx.author.id))
            else:
                await ldb.execute("INSERT INTO profile (user_id, daily_claim) VALUES (?, ?)", (ctx.author.id, now.isoformat()))

            await ldb.commit()
            embed = discord.Embed(
                color=16777215,
                description=f"{BotConfig.emoji['coin']} Here is your daily **{coins_reward} coins** today!",
            )
            await ctx.send(embed=embed)
    except Exception as e:
        print(e)
    
async def _message_count_worker():
    global message_worker_running
    message_worker_running = True

    updates = {}

    while True:
        queue_msg, timestamp = await message_count_queue.get()
        key = (queue_msg.guild.id, queue_msg.author.id)
        updates[key] = max(updates.get(key, 0), timestamp)

        while not message_count_queue.empty():
            q_msg, q_ts = await message_count_queue.get()
            key = (q_msg.guild.id, q_msg.author.id)
            updates[key] = max(updates.get(key, 0), q_ts)

        for (guild_id, user_id), ts in updates.items():
            now = datetime.utcfromtimestamp(ts)
            today_start = datetime(now.year, now.month, now.day)
            week_start = today_start - timedelta(days=now.weekday())
            now_ts = int(now.timestamp())

            cursor = await ldb.execute("""
                SELECT Total, Weekly, Daily, Last_Update
                FROM message_counts
                WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()

            if row:
                total, weekly, daily, last_update = row
                last_dt = datetime.utcfromtimestamp(last_update)

                if last_dt.date() != now.date():
                    daily = 0
                if last_dt.isocalendar()[1] != now.isocalendar()[1]:
                    weekly = 0

                total += 1
                weekly += 1
                daily += 1

                await ldb.execute("""
                    UPDATE message_counts
                    SET Total = ?, Weekly = ?, Daily = ?, Last_Update = ?
                    WHERE Guild_ID = ? AND User_ID = ?
                """, (total, weekly, daily, now_ts, guild_id, user_id))
            else:
                await ldb.execute("""
                    INSERT INTO message_counts
                        (Guild_ID, User_ID, Total, Weekly, Daily, Last_Update)
                    VALUES (?, ?, 1, 1, 1, ?)
                """, (guild_id, user_id, now_ts))

        await ldb.commit()
        updates.clear()

        # Stop the worker if no more messages
        if message_count_queue.empty():
            message_worker_running = False
            break