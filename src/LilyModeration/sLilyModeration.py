import discord
import os
import pytz
import polars as pl
import re

import Config.sBotDetails as Config
from discord.ext import commands
from datetime import datetime, timedelta, timezone


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

def exceeded_ban_limit(ctx:commands.Context, moderator_id, moderator_role_ids):
    filename = f"storage/{ctx.guild.id}/banlogs/{moderator_id}-logs.csv"
    if not os.path.exists(filename):
        return False

    now = datetime.now(pytz.utc)

    try:
        df = pl.read_csv(filename, try_parse_dates=True)
        if df.is_empty():
            return False

        df = df.filter(pl.col("ban_time") >= (now - timedelta(hours=24)))

        max_limit = max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
        return df.height >= max_limit if max_limit > 0 else False

    except Exception:
        return False

def remaining_Ban_time(ctx:commands.Context, moderator_id, moderator_role_ids):
    filename = f"storage/{ctx.guild.id}/banlogs/{moderator_id}-logs.csv"
    if not os.path.exists(filename):
        return None

    now = datetime.now(pytz.utc)

    try:
        df = pl.read_csv(filename, try_parse_dates=True)
        if df.is_empty():
            return None

        df = df.filter(pl.col("ban_time") >= (now - timedelta(hours=24)))

        max_limit = max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
        if max_limit == 0 or df.height < max_limit:
            return None

        oldest_ban = df.select(pl.col("ban_time").min()).item()
        cooldown_end = oldest_ban + timedelta(hours=24)

        if cooldown_end > now:
            time_left = cooldown_end - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes = remainder // 60
            return f"You can ban again in {hours}h {minutes}m"

        return None

    except Exception:
        return None

def remaining_ban_count(ctx:commands.Context, moderator_id, moderator_role_ids):
    filename = f"storage/{ctx.guild.id}/banlogs/{moderator_id}-logs.csv"
    if not os.path.exists(filename):
        return max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)

    now = datetime.now(pytz.utc)

    try:
        df = pl.read_csv(filename, try_parse_dates=True)
        df = df.filter(pl.col("ban_time") >= (now - timedelta(hours=24)))

        max_limit = max([Config.limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
        return max_limit - df.height if max_limit > 0 else 0

    except Exception:
        return 0

def log_ban(ctx:commands.Context, moderator_id, banned_user_id, reason="No reason provided"):
    filename = f"storage/{ctx.guild.id}/banlogs/{moderator_id}-logs.csv"
    now = datetime.now(pytz.utc).isoformat()

    new_entry = pl.DataFrame({
        "banned_user_id": [int(banned_user_id)],
        "reason": [reason],
        "ban_time": [now]
    })

    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    if file_exists:
        existing = pl.read_csv(filename)
        combined = pl.concat([existing, new_entry])
    else:
        combined = new_entry

    combined.write_csv(filename)

def display_logs(ctx: commands.Context, user_id, user, slice_expr=None):
    file_path = f"storage/{ctx.guild.id}/banlogs/{user_id}-logs.csv"
    if not os.path.exists(file_path):
        return SimpleEmbed("No Logs Found For the given user id")

    df = pl.read_csv(file_path, try_parse_dates=True).reverse()
    total_logs = len(df)
    if slice_expr is not None:
        df = df[slice_expr]

    log_dict = df.to_dicts()

    embed = discord.Embed(
        title="🚫 Ban Logs",
        description=f"🔨 Moderator: <@{user_id}>",
        colour=0xe74c3c,
        timestamp=datetime.now()
    )

    embed.set_author(name=Config.bot_name, icon_url=Config.bot_icon_link_url)
    embed.set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")

    embed.add_field(name="📖 Total Logs", value=f"{total_logs}", inline=True)
    embed.add_field(name="🗓️ Date", value=f"{datetime.now().strftime('%Y-%m-%d')}", inline=True)
    embed.add_field(name="🕵️‍♂️ Moderator ID", value=f"{user_id}", inline=True)

    embed.add_field(name="", value="**━━━━━━━━━━━━━━━━━━━**", inline=False)

    for index, log_entry in enumerate(log_dict, start=1):
        ban_timestamp = log_entry['ban_time']
        if isinstance(ban_timestamp, datetime):
            dt = ban_timestamp
        else:
            try:
                dt = datetime.fromisoformat(ban_timestamp)
            except:
                dt = datetime.strptime(ban_timestamp, "%Y-%m-%d %H:%M:%S")

        formatted_time = dt.strftime("%Y-%m-%d %I:%M:%S %p")
        timezone = dt.tzinfo if dt.tzinfo else "UTC"

        embed.add_field(
            name=f"🔹Ban Log #{index}",
            value=(f"> **👤 User:** <@{log_entry['banned_user_id']}>\n"
                   f"> **📄 Reason:** {log_entry['reason']}\n"
                   f"> **⏲️ Time:** {formatted_time} ({timezone})"),
            inline=False
        )

    return embed  

async def checklogs(ctx: commands.Context, member: str = ""):
    log_folder = f"storage/{ctx.guild.id}/banlogs"
    log_files = os.listdir(log_folder)

    if not member:
        await ctx.send("Please provide a user ID to check logs for.")
        return

    try:
        member_id = int(member)
    except ValueError:
        await ctx.send("Invalid user ID format.")
        return

    for log_file in log_files:
        if log_file.endswith('-logs.csv'):
            log_path = os.path.join(log_folder, log_file)

            try:
                df = pl.read_csv(log_path)
            except Exception as e:
                await ctx.send(f"Failed to read {log_file}: {e}")
                continue

            user_bans = df.filter(pl.col("banned_user_id") == member_id)

            if user_bans.height > 0:
                latest_ban = user_bans.sort("ban_time", descending=True).row(0)

                banned_user_id = latest_ban[0]
                reason = latest_ban[1]
                ban_time = latest_ban[2]

                moderator_id = log_file.split("-")[0]

                embed = discord.Embed(title=f"DISPLAYING BAN LOG FOR USER ID {banned_user_id}",
                      colour=0x0055ff)

                embed.add_field(name=f"",
                                value=f"**Moderator ID : <@{moderator_id}>**\n**Reason : {reason}**\n\n**Time: {ban_time}**",
                                inline=False)

                await ctx.send(embed=embed)
                return

    await ctx.send(embed=SimpleEmbed(f"No ban logs found for user with ID {member_id}."))

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

async def ban_user(ctx, user_input, reason="No reason provided", proofs:list=[]):
    except_limit_ban_ids = await Config.load_exceptional_ban_ids(ctx)
    author_role_ids = [role.id for role in ctx.author.roles]
    valid_limit_roles = [role_id for role_id in author_role_ids if role_id in Config.limit_Ban_details]

    if ctx.author.id in except_limit_ban_ids:
        await ctx.send(embed=SimpleEmbed("You Have the role to ban.  But you can't ban.  Maybe you are restricted from using this command"))
        return

    if not valid_limit_roles:
        await ctx.send(embed=SimpleEmbed("You don't have permission to perform a limited ban."))
        return

    try:
        try:
            user_id = user_input.id if isinstance(user_input, (discord.User, discord.Member)) else int(user_input)
        except ValueError:
            await ctx.send(embed=SimpleEmbed("User ID is Not Valid"))
            return
        
        member_obj = ctx.guild.get_member(user_id)

        if member_obj:
            target_user = member_obj
        else:
            try:
                target_user = await ctx.bot.fetch_user(user_id)
            except discord.NotFound:
                await ctx.send(embed=SimpleEmbed("User not found. Recheck"))
                return
            except discord.HTTPException as e:
                await ctx.send(embed=SimpleEmbed(f"Exception : HTTPException  {e}"))
                return

        if member_obj:
            if member_obj.top_role >= ctx.guild.me.top_role:
                await ctx.send(embed=SimpleEmbed("I cannot ban this user because their role is higher than mine!"))
                return
            if member_obj.top_role >= ctx.author.top_role:
                await ctx.send(embed=SimpleEmbed("I cannot ban a user with a role equal to or higher than yours."))
                return
            if member_obj.id == ctx.guild.owner_id:
                await ctx.send(embed=SimpleEmbed("I cannot ban the server owner!"))
                return
            if member_obj.id == ctx.bot.user.id:
                await ctx.send(embed=SimpleEmbed("You cannot ban me!"))
                return
            if member_obj.id == ctx.author.id:
                await ctx.send(embed=SimpleEmbed("You cannot ban yourself!"))
                return

        if exceeded_ban_limit(ctx, ctx.author.id, valid_limit_roles):
            await ctx.send(embed=SimpleEmbed("Cannot ban the user! I'm Sorry But you have exceeded your daily limit"))
            return

        try:
            if member_obj:
                try:
                    await member_obj.send(embed=BanEmbed(ctx.author, reason, Config.appeal_server_link, ctx.guild.name))
                except Exception as e:
                    print(e)
                await ctx.guild.ban(member_obj, reason=reason)
            else:
                await ctx.guild.ban(discord.Object(id=user_id), reason=reason)

            await ctx.send(embed=SimpleEmbed(f"Banned: <@{user_id}> \n**Reason:** {reason}\n **Bans Remaining: **{remaining_ban_count(ctx, ctx.author.id, valid_limit_roles) - 1}"))

            log_ban(ctx, ctx.author.id, user_id, reason)

            with open("src/LilyModeration/logchannelid.log", "r") as file:
                logs_channel_id = file.read().strip()
            log_channel = ctx.guild.get_channel(int(logs_channel_id))
            if log_channel:
                await log_channel.send(embed=LogEmbed(target_user, ctx.author, reason), files=proofs)

        except discord.HTTPException as e:
            await ctx.send(embed=SimpleEmbed(f"Failed to ban the user. {e}"))
        except Exception as e:
            await ctx.send(embed=SimpleEmbed(f"Unhandled Exception: {e}"))

    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Unhandled Exception: {e}"))

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
    elif unit == "y":
        return value * 31536000
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

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
            await channel.send(embed=SimpleEmbed(f"Exception: `{e}`"))

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