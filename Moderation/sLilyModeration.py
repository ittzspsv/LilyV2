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


def exceeded_ban_limit(moderator_id):
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

        return len(df) >= BAN_LIMIT
    except Exception as e:
        #print(f"Error reading {filename}: {e}")
        return False

def log_ban(moderator_id, banned_user_id, reason="No reason provided"):
    filename = f"{moderator_id}-logs.csv"
    now = datetime.now(pytz.utc).isoformat()
    new_ban = pd.DataFrame([[banned_user_id, reason, now]], columns=["banned_user_id", "reason", "ban_time"])

    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    new_ban.to_csv(filename, mode="a", header=not file_exists, index=False)

    #print(f"Ban logged: {banned_user_id} banned by {moderator_id} for '{reason}' at {now}")


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
    limit_ban_role = ctx.guild.get_role(limit_ban_role_id)

    if ctx.author.id in exceptional_limited_ban_id:
        await ctx.send(embed=SimpleEmbed(f"You have the role {limit_ban_role.name}, but you cannot ban."))
        return

    if not any(role.id == limit_ban_role_id for role in ctx.author.roles):
        await ctx.send(embed=SimpleEmbed(f"You need the {limit_ban_role.name} role to perform a ban."))
        return

    try:
        target_user = None

        if isinstance(user_input, discord.Member) or isinstance(user_input, discord.User):
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
            if target_user.id == ctx.guild.owner_id:
                await ctx.send(embed=SimpleEmbed("I cannot ban the server owner!"))
                return
            if target_user.id == ctx.bot.user.id:
                await ctx.send(embed=SimpleEmbed("You cannot ban me!"))
                return
            if target_user.id == ctx.author.id:
                await ctx.send(embed=SimpleEmbed("You cannot ban yourself!"))
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
            await ctx.send(embed=SimpleEmbed(f"Failed to ban the user.{e}"))
        except Exception as e:
            await ctx.send(embed=SimpleEmbed(f"Exception Not handled: {e}"))

    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Exception Not handled: {e}"))

