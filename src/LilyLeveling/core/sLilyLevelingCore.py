import aiosqlite
import asyncio
import json
import re
import ui.sProfileCardGenerator as PCG
import discord
import Config.sBotDetails as BotConfig
from discord.ext import commands
import Misc.sLilyEmbed as LE

from Misc.sLilyEmbed import simple_embed
from LilyUtility.sLilyUtility import format_currency

from LilyLeveling.componnets.sLilyLevelingComponents import build_level_embed, build_profile_embed

from typing import Dict

ldb = None
config = {}
exp_queue = asyncio.Queue()
exp_worker_running = False

message_count_queue = asyncio.Queue()
message_worker_running = False

level_cache_copy: Dict[int, Dict[int, int]] = None
level_cache: Dict[int, Dict[int, int]] = None

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

# Process message counts
async def level_processor(message: discord.Message) -> None:
    if message.author.bot or message.guild is None:
        return
    if message.content.startswith(BotConfig.bot_command_prefix):
        return
    
    # Lets cache it instead
    guild_dict = level_cache.setdefault(message.guild.id, {})
    guild_dict[message.author.id] = guild_dict.get(message.author.id, 0) + 1

# Each minute lets write them in the database.
async def persistent_level_view() -> None:
    global level_cache

    if not level_cache:
        return

    MAX_LEVEL = config.get("Max_Level", 1000)
    MAX_SQLITE_INT = 9223372036854775807
    BASE_EXP_PER_MESSAGE = 15
    BASE_MAX_EXP = 100
    EXP_INCREMENT = 50
    EXP_MULTIPLIER = 1.05
    COINS_BASE = config.get("coins_minimum", 10)

    cache_copy = level_cache
    level_cache = {}

    for guild_id, users in cache_copy.items():
        for user_id, data in users.items():

            message_count = data["messages"]
            last_ts = data["last_ts"]

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
                    INSERT INTO levels
                    (Guild_ID, User_ID, Current_Level, Level_Exp, Max_Level_Exp, Coins)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, user_id, level, exp_now, max_exp, coins))


            total_exp_gain = message_count * (BASE_EXP_PER_MESSAGE + (0.1 * level))
            exp_now += total_exp_gain

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


            await ldb.execute("""
                INSERT INTO message_counts
                (Guild_ID, User_ID, Total, Last_Update, daily, weekly)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(Guild_ID, User_ID) DO UPDATE SET
                    Total = Total + excluded.Total,
                    Last_Update = excluded.Last_Update,
                    daily = daily + excluded.daily,
                    weekly = weekly + excluded.weekly
            """, (
                guild_id,
                user_id,
                message_count,
                last_ts,
                message_count,
                message_count
            ))

    await ldb.commit()

async def set_level(ctx:commands.Context, member: discord.Member, new_level: int) -> None:
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

async def add_coins(ctx:commands.Context, member: discord.Member, amount: int) -> None:
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

async def fetch_level_details(ctx: commands.Context, member: discord.Member = None) -> None:
    img_mode: int = 0
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

        rank_display = format_currency(rank)
        if img_mode == 1:
            final_buffer = await PCG.CreateLevelCard(
                member,
                member.name,
                rank_display,
                format_currency(LevelEXP),
                format_currency(MaxLevelEXP),
                str(CurrentLevel)
            )

            file = discord.File(final_buffer, filename="levelcard.png")
            await ctx.reply(file=file)
        else:
            embed = build_level_embed(member, rank_display, format_currency(LevelEXP), format_currency(MaxLevelEXP), str(CurrentLevel))
            await ctx.reply(embed=embed)

    except Exception as e:
        await ctx.reply(embed=simple_embed('Cannot Fetch your Level, Please Chat Atleast Once!', 'cross'))    
        print(e)       

async def fetch_profile_details(ctx: commands.Context, member: discord.Member = None) -> None:
    try:
        if member is None:
            member = ctx.author

        cursor = await ldb.execute(
            "SELECT Daily, Weekly, Total FROM message_counts WHERE Guild_ID = ? AND User_ID = ?",
            (ctx.guild.id, member.id)
        )
        row = await cursor.fetchone()
        daily, weekly, total = row if row else (0, 0, 0)

        cache_count: int = level_cache.get(ctx.guild.id).get(member.id) or 0
        daily += cache_count
        weekly += cache_count
        total += cache_count

        cursor1 = await ldb.execute(
            "SELECT Coins FROM levels WHERE Guild_ID = ? AND User_ID = ?",
            (ctx.guild.id, member.id)
        )
        row1 = await cursor1.fetchone()
        coins = row1[0] if row1 else 0

        img_mode: int = 1 # To DO : Move this to a database.
        if img_mode == 1:
            final_buffer = await PCG.CreateProfileCard(
                member,
                str(daily),
                str(weekly),
                str(total),
                format_currency(int(coins))
            )

            file = discord.File(final_buffer, filename="profile_card.png")
            await ctx.reply(file=file)
        # Lightweight embed pass
        else:
            embed = build_profile_embed(member, (str(daily), str(weekly), str(total)), format_currency(int(coins)))
            await ctx.reply(embed=embed)

    except Exception as e:
        await ctx.reply(
            embed=simple_embed(
                'Cannot Fetch your Profile, Please Chat Atleast Once!',
                'cross'
            )
        )
        print(e)

async def fetch_leaderboard(ctx: commands.Context, type: str) -> None:
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
            await ctx.reply(embed=simple_embed('Error Fetching Leaderboard!', 'cross'))
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
            await ctx.reply(embed=simple_embed('No valid members found!', 'cross'))
            return

        final_buffer = await PCG.CreateLeaderBoardCard(rank_list)
        file = discord.File(final_buffer, filename="profile_card.png")
        await ctx.reply(file=file)

    except Exception as e:
        print(f"Exception [LEADERBOARD FETCH] {e}")