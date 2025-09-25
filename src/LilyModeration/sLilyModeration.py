import discord
import os
import pytz
import polars as pl
import re
import LilyManagement.sLilyStaffManagement as LSM

import Config.sBotDetails as Config
from collections import Counter
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from discord.utils import utcnow


async def VerifyVMute(self, bot, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if after.channel and before.channel != after.channel:
            channel = bot.get_channel(1324581275276935283)
            await CheckVoiceMuted(member, channel)

def evaluate_log_file(filename):
    if not os.path.exists(filename):
        df = pl.DataFrame({
            "banned_user_id": pl.Series([], dtype=pl.Int64),
            "reason": pl.Series([], dtype=pl.Utf8),
            "ban_time": pl.Series([], dtype=pl.Datetime)
        })
        df.write_csv(filename)

async def exceeded_ban_limit(ctx: commands.Context, moderator_id: int, moderator_role_ids: list[int]):
    if not moderator_role_ids:
        return False

    placeholders = ",".join("?" * len(moderator_role_ids))
    query = f"""
        SELECT role_id, ban_limit
        FROM roles
        WHERE ban_limit > 0 AND role_id IN ({placeholders})
    """
    cursor = await LSM.sdb.execute(query, [str(rid) for rid in moderator_role_ids])
    rows = await cursor.fetchall()

    if not rows:
        return False

    max_limit = max(row[1] for row in rows)

    past_24h = (datetime.now(pytz.utc) - timedelta(hours=24)).isoformat()

    try:
        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*)
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
              AND timestamp >= ?
        """, (ctx.guild.id, moderator_id, past_24h)) as c2:
            result = await c2.fetchone()
            recent_ban_count = result[0] if result else 0

        return recent_ban_count >= max_limit

    except Exception as e:
        print("Error checking ban limit:", e)
        return False

async def remaining_Ban_time(ctx: commands.Context, moderator_id: int, moderator_role_ids: list[int]):
    if not moderator_role_ids:
        return None

    now = datetime.now(pytz.utc)
    past_24h = (now - timedelta(hours=24)).isoformat()

    try:
        placeholders = ",".join("?" * len(moderator_role_ids))
        query = f"""
            SELECT ban_limit
            FROM roles
            WHERE ban_limit > 0 AND role_id IN ({placeholders})
        """
        cursor = await LSM.sdb.execute(query, moderator_role_ids)
        rows = await cursor.fetchall()

        if not rows:
            return None

        max_limit = max(row[0] for row in rows)
        if max_limit == 0:
            return None

        async with LilyLogging.mdb.execute("""
            SELECT timestamp
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
              AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (ctx.guild.id, moderator_id, past_24h)) as cursor:
            bans = await cursor.fetchall()

        recent_ban_count = len(bans)
        if recent_ban_count < max_limit:
            return None

        oldest_trigger_ban = datetime.fromisoformat(bans[0][0])
        cooldown_end = oldest_trigger_ban + timedelta(hours=24)

        if cooldown_end > now:
            remaining = cooldown_end - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            return f"You can ban again in {hours}h {minutes}m"

        return None

    except Exception as e:
        print("Error calculating remaining ban time:", e)
        return None

async def remaining_ban_count(ctx: commands.Context, moderator_id: int, moderator_role_ids: list[int]):
    if not moderator_role_ids:
        return 0

    now = datetime.now(pytz.utc)
    past_24h = (now - timedelta(hours=24)).isoformat()

    try:
        placeholders = ",".join("?" * len(moderator_role_ids))
        query = f"""
            SELECT ban_limit
            FROM roles
            WHERE role_id IN ({placeholders}) AND ban_limit > 0
        """
        cursor = await LSM.sdb.execute(query, moderator_role_ids)
        rows = await cursor.fetchall()
        max_limit = max(row[0] for row in rows) if rows else 0

        if max_limit == 0:
            return 0

        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*)
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
              AND timestamp >= ?
        """, (ctx.guild.id, moderator_id, past_24h)) as cursor:
            row = await cursor.fetchone()
            recent_ban_count = row[0] if row else 0

        return max(0, max_limit - recent_ban_count)

    except Exception as e:
        print("Error calculating remaining ban count:", e)
        return 0

async def ms(ctx: commands.Context, moderator_id: int, user: discord.User, slice_expr=None):
    try:
        async with LilyLogging.mdb.execute("""
            SELECT target_user_id, mod_type, reason, timestamp
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ?
            ORDER BY timestamp DESC
        """, (ctx.guild.id, moderator_id)) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return SimpleEmbed("No Logs Found For the given user ID")

        all_logs = [
            {
                "target_user_id": row[0],
                "mod_type": row[1].lower(),
                "reason": row[2],
                "timestamp": datetime.fromisoformat(row[3])
            }
            for row in rows
        ]

        now = datetime.now(timezone.utc)
        period_7d = now - timedelta(days=7)
        period_30d = now - timedelta(days=30)

        stats = defaultdict(lambda: {"7d": 0, "30d": 0, "total": 0})
        for log in all_logs:
            action = log["mod_type"]
            ts = log["timestamp"]

            stats[action]["total"] += 1
            if ts >= period_7d:
                stats[action]["7d"] += 1
            if ts >= period_30d:
                stats[action]["30d"] += 1

        total_logs = len(all_logs)
        shown_logs = all_logs[slice_expr] if slice_expr else all_logs

        embed = discord.Embed(
            title="📘 Moderator Logs",
            description=f"🛡️ Moderator: <@{moderator_id}>",
            colour=discord.Colour.blurple(),
            timestamp=now
        )

        embed.set_author(name=Config.bot_name, icon_url=Config.bot_icon_link_url)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")

        embed.add_field(name="📖 Total Logs", value=str(total_logs), inline=True)
        embed.add_field(name="🕵️ Moderator ID", value=str(moderator_id), inline=True)
        embed.add_field(name="🗓️ Date", value=now.strftime("%Y-%m-%d"), inline=True)

        embed.add_field(name="", value="**━━━━━━━━━━━━━━━━━━━**", inline=False)

        for action in ("mute", "warn", "ban"):
            s = stats[action]
            embed.add_field(
                name=f"{action.title()}s",
                value=f"7d: `{s['7d']}`\n30d: `{s['30d']}`\nTotal: `{s['total']}`",
                inline=True
            )

        embed.add_field(name="", value="**━━━━━━━━━━━━━━━━━━━**", inline=False)

        # individual logs
        for index, log in enumerate(shown_logs, start=1):
            formatted_time = log["timestamp"].strftime("%Y-%m-%d %I:%M:%S %p")
            tz = log["timestamp"].tzinfo or "UTC"

            embed.add_field(
                name=f"📌 Log #{index} - {log['mod_type'].title()}",
                value=(f"> 👤 **User:** <@{log['target_user_id']}>\n"
                       f"> 📝 **Reason:** {log['reason']}\n"
                       f"> ⏰ **Time:** {formatted_time} ({tz})"),
                inline=False
            )

        return embed

    except Exception as e:
        print("Error in display_logs:", e)
        return SimpleEmbed("Something went wrong while retrieving logs.")
    
async def mod_logs(ctx: commands.Context, target_user_id: int, user: discord.User, moderator: discord.User = None, mod_type: str = 'all', slice_expr=None):
    try:
        DEFAULT_FETCH_LIMIT = 5 

        count_query = "SELECT COUNT(*) FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
        count_params = [ctx.guild.id, target_user_id]
        if moderator:
            count_query += " AND moderator_id = ?"
            count_params.append(moderator.id)
        if mod_type.lower() != "all":
            count_query += " AND lower(mod_type) = ?"
            count_params.append(mod_type.lower())

        async with LilyLogging.mdb.execute(count_query, tuple(count_params)) as cursor:
            total_count_row = await cursor.fetchone()
        total_count = total_count_row[0] if total_count_row else 0
        if total_count == 0:
            return SimpleEmbed("No Logs Found For the given filters")

        type_query = "SELECT lower(mod_type), COUNT(*) FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
        type_params = [ctx.guild.id, target_user_id]
        if moderator:
            type_query += " AND moderator_id = ?"
            type_params.append(moderator.id)
        type_query += " GROUP BY lower(mod_type)"

        async with LilyLogging.mdb.execute(type_query, tuple(type_params)) as cursor:
            rows = await cursor.fetchall()
        mod_type_counts = {row[0]: row[1] for row in rows}

        select_query = "SELECT mod_type, reason, timestamp, moderator_id FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
        select_params = [ctx.guild.id, target_user_id]
        if moderator:
            select_query += " AND moderator_id = ?"
            select_params.append(moderator.id)
        if mod_type.lower() != "all":
            select_query += " AND lower(mod_type) = ?"
            select_params.append(mod_type.lower())
        select_query += " ORDER BY timestamp DESC"

        start = 0
        limit = DEFAULT_FETCH_LIMIT
        if slice_expr:
            start = slice_expr.start or 0
            if slice_expr.stop is not None:
                limit = slice_expr.stop - start
        select_query += " LIMIT ? OFFSET ?"
        select_params.extend([limit, start])

        async with LilyLogging.mdb.execute(select_query, tuple(select_params)) as cursor:
            rows = await cursor.fetchall()

        display_logs = [
            {"moderator_id": row[3], "mod_type": row[0].lower(), "reason": row[1], "timestamp": row[2]}
            for row in rows
        ]

        embed = discord.Embed(
            title=f"📘 {user.display_name} Mod Logs",
            description="📑 Showing logs for the user",
            colour=discord.Colour.blurple(),
            timestamp=datetime.now()
        )

        embed.set_author(name=Config.bot_name, icon_url=Config.bot_icon_link_url)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")

        embed.add_field(name="📖 Total Logs", value=str(total_count), inline=True)
        embed.add_field(name="🗓️ Date", value=datetime.now().strftime("%Y-%m-%d"), inline=True)

        summary = "\n".join(
            f"🔸 **{action.title()}s**: `{count}`" for action, count in mod_type_counts.items()
        )
        embed.add_field(name="📊 Logs Summary", value=summary or "No actions recorded", inline=False)
        embed.add_field(name="", value="**━━━━━━━━━━━━━━━━━━━**", inline=False)

        for index, log in enumerate(display_logs, start=1):
            try:
                dt = datetime.fromisoformat(log["timestamp"])
            except ValueError:
                dt = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")
            formatted_time = dt.strftime("%Y-%m-%d %I:%M:%S %p")
            timezone = dt.tzinfo or "UTC"

            embed.add_field(
                name=f"📌 Log #{index} - {log['mod_type'].title()}",
                value=(f"> 👤 **Moderator:** <@{log['moderator_id']}>\n"
                       f"> 📝 **Reason:** {log['reason']}\n"
                       f"> ⏰ **Time:** {formatted_time} ({timezone})"),
                inline=False
            )

        return embed

    except Exception as e:
        print("Error in mod_logs:", e)
        return SimpleEmbed(f"Something went wrong while retrieving logs: {e}")

async def checklogs(ctx: commands.Context, member: str = ""):
    if not member:
        await ctx.send("Please provide a user ID to check logs for.")
        return

    try:
        member_id = int(member)
    except ValueError as v:
        await ctx.send(v)
        return

    try:
        async with LilyLogging.mdb.execute("""
            SELECT moderator_id, reason, timestamp
            FROM modlogs
            WHERE guild_id = ? AND target_user_id = ? AND mod_type = 'ban'
            ORDER BY timestamp DESC LIMIT 1
        """, (ctx.guild.id, member_id)) as cursor:
            row = await cursor.fetchone()

        if row:
            moderator_id, reason, ban_time = row

            embed = discord.Embed(
                title=f"DISPLAYING BAN LOG FOR USER ID {member_id}",
                colour=0x0055ff
            )

            embed.add_field(
                name="",
                value=(
                    f"**Moderator ID : <@{moderator_id}>**\n"
                    f"**Reason : {reason}**\n\n"
                    f"**Time: {ban_time}**"
                ),
                inline=False
            )

            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=SimpleEmbed(f"No ban logs found for user with ID {member_id}."))

    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Exception {e}"))

def SimpleEmbed(stringformat):
    embed = discord.Embed(description=stringformat, colour=0x6600ff)
    return embed

def LogEmbed(user, moderator: discord.Member, reason: str):
    embed = discord.Embed(title="BANNED LOG", colour=0x6600ff, timestamp=datetime.now())

    user_display = f'**{user.mention}**' if isinstance(user, discord.Member) else f'<@{user.id}>'

    embed.add_field(name="**User:** ", value=user_display, inline=True)
    embed.add_field(name="**Moderator:**", value=f'**{moderator.mention}**', inline=True)
    embed.add_field(name="**Reason:**", value=f'{reason}', inline=False)
    embed.set_footer(text=f"ID : {user.id}")
    return embed

def BanEmbed(moderator: discord.Member, reason, appealLink, server_name):
    embed = discord.Embed(title=f"BANNED FROM {server_name}",
                      description="You have been banned!",
                      colour=0x00f5cc)
    embed.add_field(name="Moderator",
                    value=moderator.name,
                    inline=False)
    embed.add_field(name="Reason",
                    value=reason,
                    inline=False)
    embed.add_field(name="Appeal your Ban",
                    value=f"if you think your ban is wrongly done please make an appel here {appealLink}",
                    inline=False)

    return embed

def MuteParser(duration: str):
    match = re.match(r"(\d+)([smhd])", duration.strip().lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration}")

    value = int(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "d":
        return value * 86400
    else:
        raise ValueError(f"Unsupported unit: {unit}")

async def ban_user(ctx, user_input, reason="No reason provided", proofs: list = []):
    author_role_ids = [role.id for role in ctx.author.roles]

    role_ids = [str(rid) for rid in author_role_ids]
    if role_ids:
        placeholders = ",".join("?" * len(role_ids))
        query = f"""
            SELECT role_id
            FROM roles
            WHERE ban_limit > 0 AND role_id IN ({placeholders})
        """
        cursor = await LSM.sdb.execute(query, role_ids)
        rows = await cursor.fetchall()
        valid_limit_roles = [row[0] for row in rows]  # flatten
    else:
        valid_limit_roles = []

    if not valid_limit_roles:
        await ctx.send(embed=SimpleEmbed("You don't have permission to perform a limited ban."))
        return

    try:
        user_id = user_input.id if isinstance(user_input, (discord.User, discord.Member)) else int(user_input)
    except ValueError:
        await ctx.send(embed=SimpleEmbed("Invalid user id"))
        return

    member_obj = ctx.guild.get_member(user_id)
    if member_obj:
        target_user = member_obj
    else:
        try:
            target_user = await ctx.bot.fetch_user(user_id)
        except discord.NotFound:
            await ctx.send(embed=SimpleEmbed("User not found."))
            return
        except discord.HTTPException as e:
            await ctx.send(embed=SimpleEmbed(f"Exception: HTTPException {e}"))
            return

    if member_obj:
        if member_obj.top_role >= ctx.guild.me.top_role:
            await ctx.send(embed=SimpleEmbed("I cannot ban this user because their role is higher than mine!"))
            return
        if member_obj.top_role >= ctx.author.top_role:
            await ctx.send(embed=SimpleEmbed("You cannot ban a user with a role equal to or higher than yours."))
            return
        if member_obj.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}:
            await ctx.send(embed=SimpleEmbed("You cannot ban the owner, yourself, or me!"))
            return

    if await exceeded_ban_limit(ctx, ctx.author.id, valid_limit_roles):
        await ctx.send(embed=SimpleEmbed("Cannot ban the user! You have exceeded your daily limit."))
        return

    try:
        if member_obj:
            try:
                await member_obj.send(embed=BanEmbed(ctx.author, reason, Config.appeal_server_link, ctx.guild.name))
            except Exception as e:
                print("DM failed:", e)
            await ctx.guild.ban(member_obj, reason=reason)
        else:
            await ctx.guild.ban(discord.Object(id=user_id), reason=reason)

        remaining = await remaining_ban_count(ctx, ctx.author.id, valid_limit_roles)
        await ctx.send(embed=SimpleEmbed(
            f"✅ Banned: <@{user_id}>\n**Bans Remaining:** {remaining}"
        ))

        await LilyLogging.LogModerationAction(ctx, ctx.author.id, user_id, "ban", reason)

        try:
            with open("src/LilyModeration/logchannelid.log", "r") as file:
                logs_channel_id = int(file.read().strip())
            log_channel = ctx.guild.get_channel(logs_channel_id)
            if log_channel:
                await log_channel.send(embed=LogEmbed(target_user, ctx.author, reason), files=proofs)
        except Exception as e:
            print("Error sending to log channel:", e)

    except discord.HTTPException as e:
        await ctx.send(embed=SimpleEmbed(f"Failed to ban the user. {e}"))
    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Unhandled Exception: {e}"))

async def mute_user(ctx, user: discord.Member, duration: str, reason: str = "No reason provided"):
    if user.top_role >= ctx.guild.me.top_role:
        await ctx.send(embed=SimpleEmbed("I cannot mute this user"))
        return

    if user.top_role >= ctx.author.top_role:
        await ctx.send(embed=SimpleEmbed("I cannot mute a user with a role equal to or higher than yours."))
        return

    if user.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}:
        await ctx.send(embed=SimpleEmbed("Exception!. Stupid action detected errno 77777"))
        return

    try:
        seconds = MuteParser(duration)
        until = utcnow() + timedelta(seconds=seconds)

        try:
            await user.send(embed=SimpleEmbed(
                f"You have been muted in **{ctx.guild.name}**\n**Duration:** {duration}\n**Reason:** {reason}"
            ))
        except Exception as e:
            print("DM failed:", e)

        await user.edit(timed_out_until=until, reason=reason)

        await ctx.send(embed=SimpleEmbed(
            f"✅Muted: <@{user.id}> for **Duration:** {duration}"
        ))

        await LilyLogging.LogModerationAction(ctx, ctx.author.id, user.id, "mute", reason)

        try:
            with open("src/LilyModeration/logchannelid.log", "r") as file:
                logs_channel_id = int(file.read().strip())
            log_channel = ctx.guild.get_channel(logs_channel_id)
            if log_channel:
                await log_channel.send(embed=LogEmbed(user, ctx.author, reason + f" | Duration: {duration}"))
        except Exception as e:
            print("Error sending to log channel:", e)

    except ValueError as ve:
        await ctx.send(embed=SimpleEmbed(str(ve)))
    except discord.HTTPException as e:
        await ctx.send(embed=SimpleEmbed(f"Failed to mute the user. {e}"))
    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Exception: {e}"))

async def unmute(ctx, user: discord.Member):
    if not user.timed_out_until or user.timed_out_until <= discord.utils.utcnow():
        await ctx.send(embed=SimpleEmbed("That user is not muted currently"))
        return

    try:
        await user.edit(timed_out_until=None, reason="Manual unmute by moderator")
        await ctx.send(embed=SimpleEmbed(f"✅ Unmuted: <@{user.id}>"))
        try:
            with open("src/LilyModeration/logchannelid.log", "r") as file:
                logs_channel_id = int(file.read().strip())
            log_channel = ctx.guild.get_channel(logs_channel_id)
            if log_channel:
                await log_channel.send(embed=LogEmbed(user, ctx.author, "Unmuted manually"))
        except Exception as e:
            print("Log channel error:", e)

    except discord.HTTPException as e:
        await ctx.send(embed=SimpleEmbed(f"Failed to unmute user. {e}"))
    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Exception: {e}"))

async def CheckVoiceMuted(member: discord.Member, channel: discord.TextChannel):
    folder_path = f"storage/{970643838047760384}/vcmutelogs"
    CSV_PATH = f"{folder_path}/logs.csv"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    try:
        if not os.path.exists(CSV_PATH):
            df = pl.DataFrame({
                "user_id": [],
                "unmute_time": [],
                "reason": [],
            })
            df.write_csv(CSV_PATH)

        df = pl.read_csv(CSV_PATH, try_parse_dates=True)

        user_df = df.filter(
            pl.col("user_id") == member.id
        )

        if user_df.is_empty():
            return

        unmute_time = user_df[0, "unmute_time"]
        reason = user_df[0, "reason"]
        if isinstance(unmute_time, str):
            unmute_time = datetime.fromisoformat(unmute_time)

        now = datetime.now()

        if now >= unmute_time:
            df = df.filter(~(pl.col("user_id") == member.id))
            df.write_csv(CSV_PATH)

        else:
            await member.move_to(None, reason=f"Still muted due to {reason}")
            remaining = unmute_time - now
            try:
                await channel.send(content=f"{member.mention }", embed=SimpleEmbed(f"You have been muted in voice channels until **{str(remaining).split('.')[0]}** due to: {reason}."))
            except discord.Forbidden:
                pass

    except Exception as e:
        print(f"[Voice Mute Error] {e}")

async def warn(ctx: commands.Context, member: discord.Member, reason: str):
    await LilyLogging.LogModerationAction(ctx, ctx.author.id, member.id, "warn", reason)

    embed = discord.Embed(
        title="You have been warned",
        color=discord.Color.orange()
    )
    embed.add_field(name="Server", value=ctx.guild.name, inline=False)
    embed.add_field(name="Warned By", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        await ctx.send(f"Could not DM {member.mention}")

    await ctx.send(f"{member.mention} has been warned")

async def VoiceMute(member: discord.Member, mute_duration: str, reason: str, channel: discord.TextChannel):
    folder_path = f"storage/{970643838047760384}/vcmutelogs"
    CSV_PATH = f"{folder_path}/logs.csv"

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    try:
        mute_seconds = MuteParser(mute_duration)
        unmute_time = datetime.now() + timedelta(seconds=mute_seconds)
        unmute_time_str = unmute_time.isoformat()

        if not os.path.exists(CSV_PATH):
            df = pl.DataFrame({
                "user_id": pl.Series([], dtype=pl.Utf8),
                "unmute_time": pl.Series([], dtype=pl.Utf8),
                "reason": pl.Series([], dtype=pl.Utf8),
            })
            df.write_csv(CSV_PATH)

        df = pl.read_csv(CSV_PATH, try_parse_dates=True)

        df = df.with_columns([
            pl.col("user_id").cast(pl.Utf8),
            pl.col("unmute_time").cast(pl.Utf8),
            pl.col("reason").cast(pl.Utf8),
        ])

        if df.filter(pl.col("user_id") == str(member.id)).height > 0:
            await channel.send(embed=SimpleEmbed(f"**{member.mention}** is already muted."))
            return
        
        new_row = pl.DataFrame({
            "user_id": [str(member.id)],
            "unmute_time": [unmute_time_str],
            "reason": [reason],
        })
        df = df.vstack(new_row)
        df.write_csv(CSV_PATH)

        if member.voice:
            await member.move_to(None, reason=f"Muted for {reason}")

        try:
            await channel.send(embed=SimpleEmbed(f"Muted **{member.mention}** for **{mute_duration}**. Reason: **{reason}**."))
        except discord.Forbidden:
            pass

    except Exception as e:
        if channel:
            await channel.send(embed=SimpleEmbed(f"Exception: {e}"))

async def VoiceUnmute(member: discord.Member, channel: discord.TextChannel = None):
    folder_path = f"storage/{970643838047760384}/vcmutelogs"
    CSV_PATH = f"{folder_path}/logs.csv"

    if not os.path.exists(CSV_PATH):
        if channel:
            await channel.send(embed=SimpleEmbed(f"No mute log found for {member.mention}."))
        return

    try:
        df = pl.read_csv(CSV_PATH, try_parse_dates=True)

        original_len = len(df)
        df = df.filter(pl.col("user_id") != member.id)

        df.write_csv(CSV_PATH)

        if len(df) < original_len:
            if channel:
                await channel.send(embed=SimpleEmbed(f"{member.mention} has been **Unmuted** from **Voice Channels**"))
        else:
            if channel:
                await channel.send(embed=SimpleEmbed(f"{member.mention} has not been muted from voice channels"))
    
    except Exception as e:
        print(f"Exception in VoiceUnmute: {e}")
        if channel:
            await channel.send(embed=SimpleEmbed(f"Exception {e}"))