import aiosqlite
import asyncio
import json
import discord
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
    await ldb.execute("""
    CREATE TABLE IF NOT EXISTS levels (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Guild_ID TEXT NOT NULL,
        User_ID TEXT NOT NULL,
        Current_Level INTEGER DEFAULT 0,
        Level_Exp INTEGER DEFAULT 0,
        Max_Level_Exp INTEGER DEFAULT 100,
        Coins INTEGER DEFAULT 0
    )
""")
    
    await ldb.execute("""
    CREATE TABLE IF NOT EXISTS message_counts (
        Guild_ID TEXT NOT NULL,
        User_ID TEXT NOT NULL,
        Total INTEGER DEFAULT 0,
        Weekly INTEGER DEFAULT 0,
        Daily INTEGER DEFAULT 0,
        Last_Update INTEGER DEFAULT 0,
        PRIMARY KEY (Guild_ID, User_ID)
    )
    """)
    await ldb.commit()

def InitializeConfig():
    global config
    try:
        with open("src/LilyLeveling/LevelingConfig.json", "r") as Config:
            config = json.load(Config)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        config = {}
InitializeConfig()

async def LevelProcessor(message: discord.Message):
    if message.author.bot:
        return

    await exp_queue.put((str(message.guild.id), str(message.author.id), 10))
    global exp_worker_running
    if not exp_worker_running:
        asyncio.create_task(_exp_background_worker())
        exp_worker_running = True

    await message_count_queue.put((str(message.guild.id), str(message.author.id), int(message.created_at.timestamp())))
    global message_worker_running
    if not message_worker_running:
        asyncio.create_task(_message_count_worker())
        message_worker_running = True

async def _exp_background_worker():
    global exp_worker_running

    while exp_queue.qsize() > 0:
        updates = {}

        while not exp_queue.empty():
            guild_id, user_id, exp = await exp_queue.get()
            key = (guild_id, user_id)
            updates[key] = updates.get(key, 0) + exp

        for (guild_id, user_id), exp_gain in updates.items():
            cursor = await ldb.execute("""
                SELECT Current_Level, Level_Exp, Max_Level_Exp, Coins
                FROM levels WHERE Guild_ID = ? AND User_ID = ?
            """, (guild_id, user_id))
            row = await cursor.fetchone()

            if row:
                level, exp_now, max_exp, coins = row
            else:
                level, exp_now, max_exp, coins = 0, 0, 100, 0
                await ldb.execute("""
                    INSERT INTO levels (Guild_ID, User_ID, Current_Level, Level_Exp, Max_Level_Exp, Coins)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, user_id, level, exp_now, max_exp, coins))

            exp_now += exp_gain
            while exp_now >= max_exp:
                exp_now -= max_exp
                level += 1
                max_exp = int(max_exp * config['Exp_Multiplier'])
                coins += int(config['coins_minimum'] * (1 + (level * 0.1)))

            await ldb.execute("""
                UPDATE levels
                SET Current_Level = ?, Level_Exp = ?, Max_Level_Exp = ?, Coins = ?
                WHERE Guild_ID = ? AND User_ID = ?
            """, (level, exp_now, max_exp, coins, guild_id, user_id))

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