import discord
import os
import pytz
import polars as pl
import re
import aiosqlite

import Config.sBotDetails as Config
from collections import Counter
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from datetime import datetime, timedelta, timezone
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
    now = datetime.now(pytz.utc).isoformat()
    past_24h = (datetime.now(pytz.utc) - timedelta(hours=24)).isoformat()

    try:
        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*) FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
            AND timestamp >= ?
        """, (ctx.guild.id, moderator_id, past_24h)) as cursor:
            result = await cursor.fetchone()
            recent_ban_count = result[0] if result else 0

        max_limit = max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
        return recent_ban_count >= max_limit if max_limit > 0 else False

    except Exception as e:
        return False

async def remaining_Ban_time(ctx: commands.Context, moderator_id: int, moderator_role_ids: list[int]):
    now = datetime.now(pytz.utc)
    past_24h = now - timedelta(hours=24)

    try:
        async with LilyLogging.mdb.execute("""
            SELECT timestamp FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
            AND timestamp >= ?
            ORDER BY timestamp ASC LIMIT 1
        """, (ctx.guild.id, moderator_id, past_24h.isoformat())) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        oldest_ban_time = datetime.fromisoformat(row[0])

        max_limit = max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)

        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*) FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
            AND timestamp >= ?
        """, (ctx.guild.id, moderator_id, past_24h.isoformat())) as cursor:
            count_row = await cursor.fetchone()
            recent_ban_count = count_row[0] if count_row else 0

        if max_limit == 0 or recent_ban_count < max_limit:
            return None

        cooldown_end = oldest_ban_time + timedelta(hours=24)
        if cooldown_end > now:
            remaining = cooldown_end - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            return f"You can ban again in {hours}h {minutes}m"

        return None

    except Exception as e:
        return None

async def remaining_ban_count(ctx: commands.Context, moderator_id, moderator_role_ids):
    now = datetime.now(pytz.utc)
    past_24h = now - timedelta(hours=24)

    try:
        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*) FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type = 'ban'
            AND timestamp >= ?
        """, (ctx.guild.id, moderator_id, past_24h.isoformat())) as cursor:
            row = await cursor.fetchone()
            recent_ban_count = row[0] if row else 0

        max_limit = max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)

        return max(0, max_limit - recent_ban_count) if max_limit > 0 else 0

    except Exception as e:
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
                "timestamp": row[3]
            }
            for row in rows
        ]

        mod_type_counts = Counter(log["mod_type"] for log in all_logs)
        total_logs = len(all_logs)

        shown_logs = all_logs[slice_expr] if slice_expr else all_logs

        embed = discord.Embed(
            title="📘 Moderator Logs",
            description=f"🛡️ Moderator: <@{moderator_id}>",
            colour=discord.Colour.blurple(),
            timestamp=datetime.now()
        )

        embed.set_author(name=Config.bot_name, icon_url=Config.bot_icon_link_url)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")

        embed.add_field(name="📖 Total Logs", value=str(total_logs), inline=True)
        embed.add_field(name="🕵️ Moderator ID", value=str(moderator_id), inline=True)
        embed.add_field(name="🗓️ Date", value=datetime.now().strftime("%Y-%m-%d"), inline=True)

        action_summary = "\n".join(
            f"🔸 **{action.title()}s**: `{count}`" for action, count in mod_type_counts.items()
        )
        embed.add_field(name="📊 Moderation Summary", value=action_summary or "No actions recorded", inline=False)

        embed.add_field(name="", value="**━━━━━━━━━━━━━━━━━━━**", inline=False)

        for index, log in enumerate(shown_logs, start=1):
            try:
                dt = datetime.fromisoformat(log["timestamp"])
            except ValueError:
                dt = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")

            formatted_time = dt.strftime("%Y-%m-%d %I:%M:%S %p")
            timezone = dt.tzinfo or "UTC"

            embed.add_field(
                name=f"📌 Log #{index} - {log['mod_type'].title()}",
                value=(f"> 👤 **User:** <@{log['target_user_id']}>\n"
                       f"> 📝 **Reason:** {log['reason']}\n"
                       f"> ⏰ **Time:** {formatted_time} ({timezone})"),
                inline=False
            )

        return embed

    except Exception as e:
        print("Error in display_logs:", e)
        return SimpleEmbed("Something went wrong while retrieving logs.")
    
async def mod_logs(ctx: commands.Context, moderator_id: int, user: discord.User, slice_expr=None):
    try:
        async with LilyLogging.mdb.execute("""
            SELECT mod_type, reason, timestamp, moderator_id
            FROM modlogs
            WHERE guild_id = ? AND target_user_id = ?
            ORDER BY timestamp DESC
        """, (ctx.guild.id, moderator_id)) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return SimpleEmbed("No Logs Found For the given user ID")

        all_logs = [
            {
                "moderator_id" : row[3],
                "mod_type": row[0].lower(),
                "reason": row[1],
                "timestamp": row[2]
            }
            for row in rows
        ]

        mod_type_counts = Counter(log["mod_type"] for log in all_logs)
        total_logs = len(all_logs)

        shown_logs = all_logs[slice_expr] if slice_expr else all_logs

        embed = discord.Embed(
            title=f"📘 {user.display_name} Mod Logs",
            description=f"📑 Showing Logs for the user",
            colour=discord.Colour.blurple(),
            timestamp=datetime.now()
        )

        embed.set_author(name=Config.bot_name, icon_url=Config.bot_icon_link_url)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")

        embed.add_field(name="📖 Total Logs", value=str(total_logs), inline=True)
        embed.add_field(name="🗓️ Date", value=datetime.now().strftime("%Y-%m-%d"), inline=True)

        action_summary = "\n".join(
            f"🔸 **{action.title()}s**: `{count}`" for action, count in mod_type_counts.items()
        )
        embed.add_field(name="📊 Logs Summary", value=action_summary or "No actions recorded", inline=False)

        embed.add_field(name="", value="**━━━━━━━━━━━━━━━━━━━**", inline=False)

        for index, log in enumerate(shown_logs, start=1):
            try:
                dt = datetime.fromisoformat(log["timestamp"])
            except ValueError:
                dt = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")

            formatted_time = dt.strftime("%Y-%m-%d %I:%M:%S %p")
            timezone = dt.tzinfo or "UTC"

            embed.add_field(
                name=f"📌 Log #{index} - {log['mod_type'].title()}",
                value=(f"> 👤 **Moderator ID:** <@{log['moderator_id']}>\n"
                       f"> 📝 **Reason:** {log['reason']}\n"
                       f"> ⏰ **Time:** {formatted_time} ({timezone})"),
                inline=False
            )

        return embed

    except Exception as e:
        print("Error in display_logs:", e)
        return SimpleEmbed("Something went wrong while retrieving logs.")

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
    valid_limit_roles = [role_id for role_id in author_role_ids if role_id in Config.limit_Ban_details]

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
            await ctx.send(embed=SimpleEmbed("User not found. "))
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
            f"Banned: <@{user_id}>\n**Reason:** {reason}\n**Bans Remaining:** {remaining - 1}"
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
            f"Muted: <@{user.id}>\n**Duration:** {duration}\n**Reason:** {reason}"
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
        await ctx.send(embed=SimpleEmbed(f"Unmuted: <@{user.id}>"))
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