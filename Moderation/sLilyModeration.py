import discord
import os
import pytz
import polars as pl

from Config.sBotDetails import *
from discord.ext import commands
from datetime import datetime, timedelta

def evaluate_log_file(filename):
    if not os.path.exists(filename):
        df = pl.DataFrame({
            "banned_user_id": pl.Series([], dtype=pl.Int64),
            "reason": pl.Series([], dtype=pl.Utf8),
            "ban_time": pl.Series([], dtype=pl.Datetime)
        })
        df.write_csv(filename)

def exceeded_ban_limit(moderator_id, moderator_role_ids):
    filename = f"{moderator_id}-logs.csv"
    if not os.path.exists(filename):
        return False

    now = datetime.now(pytz.utc)

    try:
        df = pl.read_csv(filename, try_parse_dates=True)
        if df.is_empty():
            return False

        df = df.filter(pl.col("ban_time") >= (now - timedelta(hours=24)))

        max_limit = max([limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
        return df.height >= max_limit if max_limit > 0 else False

    except Exception:
        return False


def remaining_Ban_time(moderator_id, moderator_role_ids):
    filename = f"{moderator_id}-logs.csv"
    if not os.path.exists(filename):
        return None

    now = datetime.now(pytz.utc)

    try:
        df = pl.read_csv(filename, try_parse_dates=True)
        if df.is_empty():
            return None

        df = df.filter(pl.col("ban_time") >= (now - timedelta(hours=24)))

        max_limit = max([limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
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

def remaining_ban_count(moderator_id, moderator_role_ids):
    filename = f"{moderator_id}-logs.csv"
    if not os.path.exists(filename):
        return max([limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)

    now = datetime.now(pytz.utc)

    try:
        df = pl.read_csv(filename, try_parse_dates=True)
        df = df.filter(pl.col("ban_time") >= (now - timedelta(hours=24)))

        max_limit = max([limit_Ban_details.get(role_id, 0) for role_id in moderator_role_ids], default=0)
        return max_limit - df.height if max_limit > 0 else 0

    except Exception:
        return 0

def log_ban(moderator_id, banned_user_id, reason="No reason provided"):
    filename = f"{moderator_id}-logs.csv"
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

def display_logs(user_id, user, slice_expr=None):
    file_path = f"{user_id}-logs.csv"
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

    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)
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

def SimpleEmbed(stringformat):
    embed = discord.Embed(description=stringformat, colour=0x6600ff, timestamp=datetime.now())
    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)
    return embed

def LogEmbed(user, moderator: discord.Member, reason: str):
    embed = discord.Embed(title="BANNED LOG", colour=0x6600ff, timestamp=datetime.now())
    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)

    user_display = f'**{user.mention}**' if isinstance(user, discord.Member) else f'<@{user.id}>'

    embed.add_field(name="**User:** ", value=user_display, inline=True)
    embed.add_field(name="**Moderator:**", value=f'**{moderator.mention}**', inline=True)
    embed.add_field(name="**Reason:**", value=f'{reason}', inline=False)
    embed.set_footer(text=f"ID : {user.id}")
    return embed

async def ban_user(ctx, user_input, reason="No reason provided", proofs:list=[]):
    except_limit_ban_ids = load_exceptional_ban_ids()
    author_role_ids = [role.id for role in ctx.author.roles]
    valid_limit_roles = [role_id for role_id in author_role_ids if role_id in limit_Ban_details]

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

        if exceeded_ban_limit(ctx.author.id, valid_limit_roles):
            await ctx.send(embed=SimpleEmbed("Cannot ban the user! I'm Sorry But you have exceeded your daily limit"))
            return

        try:
            if member_obj:
                await ctx.guild.ban(member_obj, reason=reason)
            else:
                await ctx.guild.ban(discord.Object(id=user_id), reason=reason)

            await ctx.send(embed=SimpleEmbed(f"Banned: <@{user_id}> \n**Reason:** {reason}\n **Bans Remaining: **{remaining_ban_count(ctx.author.id, valid_limit_roles) - 1}"))

            log_ban(ctx.author.id, user_id, reason)

            with open("Moderation/logchannelid.log", "r") as file:
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