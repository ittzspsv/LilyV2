import discord
import os
import pytz
import pandas as pd

from Config.sBotDetails import *
from discord.ext import commands
from datetime import datetime, timedelta


def evaluate_log_file(filename):
    if not os.path.exists(filename):
        df = pd.DataFrame(columns=["banned_user_id", "reason", "ban_time"])
        df.to_csv(filename, index=False)


def exceeded_ban_limit(moderator_id, moderator_role_ids):
    filename = f"{moderator_id}-logs.csv"

    if not os.path.exists(filename):
        return False

    now = datetime.now(pytz.utc)

    try:
        df = pd.read_csv(filename)
        if df.empty:
            return False

        df["ban_time"] = pd.to_datetime(df["ban_time"], errors="coerce", utc=True)
        df = df[df["ban_time"] >= (now - timedelta(hours=24))]

        max_limit = 0
        for role_id in moderator_role_ids:
            limit = limit_Ban_details.get(role_id)
            if limit and limit > max_limit:
                max_limit = limit

        return len(df) >= max_limit if max_limit > 0 else False

    except Exception as e:
        return False


def remaining_Ban_time(moderator_id, moderator_role_ids):
    filename = f"{moderator_id}-logs.csv"

    if not os.path.exists(filename):
        return None

    now = datetime.now(pytz.utc)

    try:
        df = pd.read_csv(filename)
        if df.empty:
            return None

        df["ban_time"] = pd.to_datetime(df["ban_time"], errors="coerce", utc=True)
        df = df[df["ban_time"] >= (now - timedelta(hours=24))]

        max_limit = 0
        for role_id in moderator_role_ids:
            limit = limit_Ban_details.get(role_id)
            if limit and limit > max_limit:
                max_limit = limit

        if max_limit == 0 or len(df) < max_limit:
            return None

        oldest_ban = df["ban_time"].min()
        cooldown_end = oldest_ban + timedelta(hours=24)

        if cooldown_end > now:
            time_left = cooldown_end - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes = remainder // 60
            return f"You can ban again in {hours}h {minutes}m"

        return None

    except Exception as e:
        return None


def log_ban(moderator_id, banned_user_id, reason="No reason provided"):
    filename = f"{moderator_id}-logs.csv"
    now = datetime.now(pytz.utc).isoformat()
    new_ban = pd.DataFrame([[banned_user_id, reason, now]], columns=["banned_user_id", "reason", "ban_time"])

    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    new_ban.to_csv(filename, mode="a", header=not file_exists, index=False)


def display_logs(user_id, user, slice_expr=None):
    file_path = f"{user_id}-logs.csv"
    if not os.path.exists(file_path):
        return SimpleEmbed("No Logs Found For the given user id")
    df = pd.read_csv(file_path)
    df = df[::-1]

    if slice_expr is not None:
        df = df.iloc[slice_expr]

    log_dict = df.to_dict(orient='records')

    embed = discord.Embed(
        title="🚫 Ban Logs",
        description=f"🔨 Moderator: <@{user_id}>",
        colour=0xe74c3c,
        timestamp=datetime.now()
    )

    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)
    embed.set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")

    embed.add_field(name="🧰 Total Logs", value=f"{len(log_dict)}", inline=True)
    embed.add_field(name="🗓️ Date", value=f"{datetime.now().strftime('%Y-%m-%d')}", inline=True)
    embed.add_field(name="🕵️‍♂️ Moderator ID", value=f"`{user_id}`", inline=True)

    embed.add_field(name="\\u200b", value="━━━━━━━━━━━━━━━━━━━", inline=False)

    for index, log_entry in enumerate(log_dict, start=1):
        ban_timestamp = log_entry['ban_time']
        dt = datetime.fromisoformat(ban_timestamp)

        formatted_time = dt.strftime("%Y-%m-%d %I:%M:%S %p")
        timezone = dt.tzinfo if dt.tzinfo else "UTC"

        embed.add_field(
            name=f"🚷 Ban Log #{index}",
            value=(
                f"> **👤 User:** <@{log_entry['banned_user_id']}>\n"
                f"> **📄 Reason:** {log_entry['reason']}\n"
                f"> **⏲️ Time:** {formatted_time} ({timezone})"
            ),
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


async def ban_user(ctx, user_input, reason="No reason provided"):
    except_limit_ban_ids = load_exceptional_ban_ids()
    author_role_ids = [role.id for role in ctx.author.roles]
    valid_limit_roles = [rid for rid in author_role_ids if rid in limit_Ban_details]

    if ctx.author.id in except_limit_ban_ids:
        await ctx.send(embed=SimpleEmbed("You Have the role to ban.  But you can't ban.  Maybe you are restricted from using this command"))
        return

    if not valid_limit_roles:
        await ctx.send(embed=SimpleEmbed("You don't have permission to perform a limited ban."))
        return

    try:
        target_user = None

        if isinstance(user_input, (discord.Member, discord.User)):
            target_user = user_input
        else:
            try:
                target_user = await commands.MemberConverter().convert(ctx, str(user_input))
            except commands.MemberNotFound:
                try:
                    user_id = int(user_input)
                    target_user = await ctx.bot.fetch_user(user_id)
                except ValueError:
                    await ctx.send(embed=SimpleEmbed("User ID is Not Valid"))
                    return
                except discord.NotFound:
                    await ctx.send(embed=SimpleEmbed("User not found. Recheck"))
                    return
                except discord.HTTPException as e:
                    await ctx.send(embed=SimpleEmbed(f"Exception : HTTPException  {e}"))
                    return

        if isinstance(target_user, discord.Member):
            if target_user.top_role >= ctx.guild.me.top_role:
                await ctx.send(embed=SimpleEmbed("I cannot ban this user because their role is higher than mine!"))
                return

            if target_user.top_role >= ctx.author.top_role:
                await ctx.send(embed=SimpleEmbed("I cannot ban a user with a role equal to or higher than yours."))
                return
            if target_user.id == ctx.guild.owner_id:
                await ctx.send(embed=SimpleEmbed("I cannot ban the server owner!"))
                return
            if target_user.id == ctx.bot.user.id:
                await ctx.send(embed=SimpleEmbed("You cannot ban me!"))
                return
            if target_user.id == ctx.author.id:
                await ctx.send(embed=SimpleEmbed("You cannot ban yourself!"))
                return

        if exceeded_ban_limit(ctx.author.id, valid_limit_roles):
            await ctx.send(embed=SimpleEmbed("Cannot ban the user! I'm Sorry But you have exceeded your daily limit"))
            return
        try:
            await ctx.guild.ban(discord.Object(id=target_user.id), reason=reason)
            await ctx.send(embed=SimpleEmbed(f"Banned: <@{target_user.id}> \n**Reason:** {reason}"))

            log_ban(ctx.author.id, target_user.id, reason)
            log_channel = ctx.guild.get_channel(logs_channel_id)
            if log_channel:
                await log_channel.send(embed=LogEmbed(target_user, ctx.author, reason))

        except discord.Forbidden:
            await ctx.send(embed=SimpleEmbed("I do not have permission to ban this user."))
        except discord.HTTPException as e:
            await ctx.send(embed=SimpleEmbed(f"Failed to ban the user. {e}"))
        except Exception as e:
            await ctx.send(embed=SimpleEmbed(f"Unhandled Exception: {e}"))

    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Unhandled Exception: {e}"))

