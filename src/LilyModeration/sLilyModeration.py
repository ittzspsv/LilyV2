import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
import pytz
import re
import asyncio
import ui.sGIFManipulation as GIFM
#import LilyManagement.sLilyStaffManagement as LSM

import Config.sBotDetails as Config
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from discord.utils import utcnow
import os
import random

from LilyModeration.db.sLilyModerationDatabaseAccess import fetch_mod_logs, fetch_mod_stats, edit_case
import LilyManagement.db.sLilyStaffDatabaseAccess as LSDA


from Misc.sLilyEmbed import simple_embed
from LilyModeration.components.sLilyModerationComponents import ban_embed, mute_embed, warn_embed, ModerationInsights
from LilyModeration.utils.LilyModerationUtilities import mute_parser


async def exceeded_ban_limit(ctx: commands.Context, moderator_id: int, moderator_role_ids: list[int]):
    if not moderator_role_ids:
        return False

    placeholders = ",".join("?" * len(moderator_role_ids))
    query = f"""
        SELECT role_id, ban_limit
        FROM roles
        WHERE ban_limit > -1 AND role_id IN ({placeholders})
    """
    cursor = await LSDA.sdb.execute(query, [str(rid) for rid in moderator_role_ids])
    rows = await cursor.fetchall()

    if not rows:
        return False

    max_limit = max(row[1] for row in rows)

    past_24h = (datetime.now(pytz.utc) - timedelta(hours=24)).isoformat()

    try:
        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*)
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type IN ('ban', 'quarantine')
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
            WHERE ban_limit > -1 AND role_id IN ({placeholders})
        """
        cursor = await LSDA.sdb.execute(query, moderator_role_ids)
        rows = await cursor.fetchall()

        if not rows:
            return None

        max_limit = max(row[0] for row in rows)
        if max_limit == 0:
            return None

        async with LilyLogging.mdb.execute("""
            SELECT timestamp
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type IN ('ban', 'quarantine')
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
        cursor = await LSDA.sdb.execute(query, moderator_role_ids)
        rows = await cursor.fetchall()
        max_limit = max(row[0] for row in rows) if rows else 0

        if max_limit == 0:
            return 0

        async with LilyLogging.mdb.execute("""
            SELECT COUNT(*)
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ? AND mod_type IN ('ban', 'quarantine')
              AND timestamp >= ?
        """, (ctx.guild.id, moderator_id, past_24h)) as cursor:
            row = await cursor.fetchone()
            recent_ban_count = row[0] if row else 0

        return max(0, max_limit - recent_ban_count)

    except Exception as e:
        print("Error calculating remaining ban count:", e)
        return 0

async def remaining_Ban_time_text(ctx: commands.Context,moderator_id: int,moderator_role_ids: list[int]):
    if not moderator_role_ids:
        return None

    now = datetime.now(pytz.utc)
    past_24h = (now - timedelta(hours=24)).isoformat()

    try:
        placeholders = ",".join("?" * len(moderator_role_ids))
        query = f"""
            SELECT ban_limit
            FROM roles
            WHERE ban_limit > -1 AND role_id IN ({placeholders})
        """
        cursor = await LSDA.sdb.execute(query, moderator_role_ids)
        rows = await cursor.fetchall()

        if not rows:
            return None

        max_limit = max(row[0] for row in rows)
        if max_limit == 0:
            return None

        async with LilyLogging.mdb.execute("""
            SELECT timestamp
            FROM modlogs
            WHERE guild_id = ?
              AND moderator_id = ?
              AND mod_type IN ('ban', 'quarantine')
              AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (ctx.guild.id, moderator_id, past_24h)) as cursor:
            bans = await cursor.fetchall()

        if not bans:
            return None

        cooldown_lines = []

        for index, (ts,) in enumerate(bans, start=1):
            ban_time = datetime.fromisoformat(ts)
            cooldown_end = ban_time + timedelta(hours=24)

            if cooldown_end > now:
                remaining = cooldown_end - now
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes = remainder // 60

                cooldown_lines.append(
                    f"{index}. Recovery in **{hours}h {minutes}m**"
                )

        if not cooldown_lines:
            return None

        return (
            "**Ban's Cooldown State.**\n"
            + "\n".join(cooldown_lines)
        )

    except Exception as e:
        print("Error calculating remaining ban time:", e)
        return None

async def ms(ctx: commands.Context, moderator: discord.Member, page_start: int=0, page_end: int=5):
    payload = {
        "guild_id" : ctx.guild.id,
        "moderator_id" : moderator.id,
        "page_start" : page_start,
        "page_end" : page_end
    }

    result = await fetch_mod_stats(payload)

    if not result["success"]:
        return simple_embed("No Logs Found For the given moderator ID")

    logs = result["logs"]
    stats = result["stats"]
    total_logs = result["total_logs"]
    now = result["now"]
    average_active_moderation_timestamp_range = result["average_active_moderation_timestamp_range"]

    embed1 = discord.Embed(
            title=f"{Config.emoji['arrow']} {moderator.display_name}'s Moderation Stats",
            description=f"### Average Active Moderation Time\n- <t:{average_active_moderation_timestamp_range[0]}:T> - <t:{average_active_moderation_timestamp_range[1]}:T>",
            colour=16777215
        )
    embed1.set_thumbnail(url=moderator.avatar.url if moderator.avatar else Config.img['member'])
    embed1.set_image(url=Config.img['border'])
    embed1.add_field(name=f"{Config.emoji['logs']} Total Logs", value=str(total_logs), inline=True)
    embed1.add_field(name=f"{Config.emoji['shield']} Moderator ID", value=str(moderator.id), inline=True)
    embed1.add_field(name=f"{Config.emoji['calender']} Date", value=now.strftime("%Y-%m-%d"), inline=True)

    embed2 = discord.Embed(
            title=f"{Config.emoji['arrow']} Moderation Statistics Overview",
            description=f"### Total Logs Evaluation\n-  **Mutes**: `{stats['mute']['total']}` | **Bans** : `{stats['ban']['total']}` | **Quarantines** : `{stats['quarantine']['total']}` | **Warns** : `{stats['warn']['total']}`",
            colour=16777215
        )
    embed2.set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")

    actions = ["mute", "warn", "ban", "quarantine"]

    for action in actions:
        embed2.add_field(
            name=f"{action.title()} (Today)",
            value=str(stats[action]["today"]),
            inline=True
        )
        embed2.add_field(
            name=f"{action.title()} (last 7 days)",
            value=str(stats[action]["7d"]),
            inline=True
        )
        embed2.add_field(
            name=f"{action.title()} (last 30 days)",
            value=str(stats[action]["30d"]),
            inline=True
        )

    logs_text = ""

    for index, log in enumerate(logs, start=page_start + 1):

        ts_unix = int(log["timestamp"].timestamp())

        logs_text += (
            f"📌 **Log #{index} - {log['mod_type'].title()}**\n"
            f"> {Config.emoji['member']} User: <@{log['target_user_id']}>\n"
            f"> {Config.emoji['bookmark']} Reason: {log['reason']}\n"
            f"> {Config.emoji['clock']} Time: <t:{ts_unix}:R>\n\n"
        )

    if logs_text:
        embed_logs = discord.Embed(
            title=f"{Config.emoji['arrow']} Moderator Action Logs",
            description=logs_text,
            colour=16777215
        ).set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")

        return [embed1, embed2, embed_logs]

    return [embed1, embed2]
    
async def mod_logs(ctx: commands.Context, target_user_id: int, user: discord.User, moderator: discord.User = None, mod_type: str = "all", page_start: int=0, page_end: int = 5):
    payload = {
        "guild_id" : ctx.guild.id,
        "target_user_id" : target_user_id,
        "moderator_id" : moderator.id if moderator else None,
        "mod_type" : mod_type,
        "page_start" : page_start,
        "page_end" : page_end
    }
    result = await fetch_mod_logs(payload)

    if not result["success"]:
        return simple_embed("No Logs Found For the given filters")

    total_count = result["total_logs"]
    mod_type_counts = result["counts"]
    display_logs = result["logs"]

    now = datetime.now(timezone.utc)

    embed_summary = (
        discord.Embed(
            color=16777215,
            title=f"{Config.emoji['arrow']} {user.display_name}'s Moderation Logs",
        )
        .set_thumbnail(url=user.avatar.url if user.avatar else Config.img['member'])
        .set_image(url=Config.img['border'])
        .add_field(name="Total Logs", value=str(total_count), inline=True)
        .add_field(name="Date", value=now.strftime("%Y-%m-%d"), inline=True)
    )

    summary_text = "\n".join(
        f"- {action.title()}s: `{count}`" for action, count in mod_type_counts.items()
    )

    embed_summary.add_field(
        name="Logs Summary",
        value=summary_text or "No actions recorded",
        inline=False
    )

    embed_logs = (
        discord.Embed(
            color=16777215,
            title=f"{Config.emoji['arrow']} Log's Overview",
        )
        .set_thumbnail(url=Config.img['logs'])
        .set_image(url=Config.img['border'])
    )

    for index, log in enumerate(display_logs, start=page_start + 1):

        try:
            dt = datetime.fromisoformat(log.get("timestamp"))
        except ValueError:
            dt = datetime.strptime(log.get("timestamp"), "%Y-%m-%d %H:%M:%S")

        ts_unix = int(dt.timestamp())
        reason_text = log["reason"] or "No reason provided"

        embed_logs.add_field(
            name=f"📌 Log #{log.get("case_id")} • {log['mod_type'].title()}",
            value=(
                f"> {Config.emoji['shield']} Moderator : <@{log['moderator_id']}>\n"
                f"> {Config.emoji['pencil']} Reason : **{reason_text}**\n"
                f"> {Config.emoji['clock']} Time : <t:{ts_unix}:R>"
            ),
            inline=False
        )

    return [embed_summary, embed_logs]
    
async def moderation_insights(ctx: commands.Context):
    view = ModerationInsights(ctx.me)
    view.message = await ctx.reply(view=view)
    
async def ban_user(ctx, user_input, reason="No reason provided", proofs: list = []):
    try:
        try:
            cur = await VC.cdb.execute(
                "SELECT value FROM GlobalConfigs WHERE key = 'Jail'"
            )
            row = await cur.fetchone()
            await cur.close()
            jail_value = int(row[0] or 0)
        except Exception:
            jail_value = 0

        role_ids = [str(r.id) for r in ctx.author.roles]
        if not role_ids:
            return await ctx.reply(embed=simple_embed("No permission.", 'cross'))

        placeholders = ",".join("?" * len(role_ids))
        cursor = await LSDA.sdb.execute(
            f"SELECT role_id FROM roles WHERE ban_limit > -1 AND role_id IN ({placeholders})",
            role_ids
        )
        valid_roles = [row[0] for row in await cursor.fetchall()]

        if not valid_roles:
            return await ctx.reply(embed=simple_embed("No permission.", 'cross'))

        user_id = getattr(user_input, "id", None)
        if not user_id:
            return await ctx.reply(embed=simple_embed("Invalid user.", 'cross'))

        member = user_input if isinstance(user_input, discord.Member) else None
        target = user_input

        if member and (
            member.top_role >= ctx.guild.me.top_role or
            member.top_role >= ctx.author.top_role or
            member.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}
        ):
            return await ctx.reply(embed=simple_embed("Cannot moderate this user.", 'cross'))

        if await exceeded_ban_limit(ctx, ctx.author.id, valid_roles):
            remaining_time = await remaining_Ban_time(ctx, ctx.author.id, valid_roles)
            return await ctx.reply(embed=simple_embed(
                f"Daily limit exceeded.\n{remaining_time}", 'cross'
            ))

        async def notify_and_log(action):
            try:
                await target.send(embed=ban_embed(
                    ctx.author, reason,
                    Config.appeal_server_link,
                    ctx.guild.name
                ))
            except Exception:
                pass

            await LilyLogging.LogModerationAction(
                ctx, ctx.author.id, user_id, action, reason, proofs.copy()
            )

            return await remaining_ban_count(ctx, ctx.author.id, valid_roles)

        if jail_value == 0:
            await ctx.guild.ban(
                discord.Object(id=user_id),
                reason=f"By {ctx.author} | {reason}"
            )

            remaining = await notify_and_log("ban")

            return await ctx.reply(embed=simple_embed(
                f"Banned: <@{user_id}>\n**Remaining:** {remaining}"
            ))

        if not member:
            return await ctx.reply(embed=simple_embed(
                "User not in guild.", 'cross'
            ))

        quarantine_role = (
            discord.utils.get(ctx.guild.roles, name="Quarantine")
            or discord.utils.get(ctx.guild.roles, name="Prisoner")
        )

        if not quarantine_role or quarantine_role >= ctx.guild.me.top_role:
            return await ctx.reply(embed=simple_embed(
                "Quarantine role issue.", 'cross'
            ))

        if quarantine_role in member.roles:
            return await ctx.reply(embed=simple_embed(
                "Already quarantined.", 'cross'
            ))

        await member.add_roles(
            quarantine_role,
            reason=f"Quarantine by {ctx.author} | {reason}"
        )

        remaining = await notify_and_log("quarantine")

        return await ctx.reply(embed=simple_embed(
            f"Quarantined: <@{user_id}>\n**Remaining:** {remaining}"
        ))

    except discord.HTTPException as e:
        return await ctx.reply(embed=simple_embed(f"HTTP Error: {e}", 'cross'))
    except Exception as e:
        return await ctx.reply(embed=simple_embed(f"Error: {e}", 'cross'))

async def mute_user(ctx: commands.Context, user: discord.Member, duration: str, reason: str = "No reason provided", proofs: list = []):

    if user.timed_out_until and user.timed_out_until > discord.utils.utcnow():
        await ctx.reply(embed=simple_embed("This user is already muted", 'cross'))
        return

    if user.top_role >= ctx.guild.me.top_role:
        await ctx.reply(embed=simple_embed("I cannot mute this user", 'cross'))
        return

    if user.top_role >= ctx.author.top_role:
        await ctx.reply(embed=simple_embed("I cannot mute a user with a role equal to or higher than yours.", 'cross'))
        return

    if user.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}:
        await ctx.reply(embed=simple_embed("Exception!. Stupid action detected errno 77777", 'cross'))
        return

    try:
        seconds = mute_parser(duration)
        until = utcnow() + timedelta(seconds=seconds)

        try:
            embed = mute_embed(ctx.author, reason, ctx.guild.name)
            await user.send(embed=embed)
        except Exception as e:
            print("DM failed:", e)

        await user.edit(timed_out_until=until, reason=reason)

        await ctx.reply(embed=simple_embed(
            f"Muted: <@{user.id}>"
        ))

        await LilyLogging.LogModerationAction(ctx, ctx.author.id, user.id, "mute", reason, proofs)

    except ValueError as ve:
        await ctx.reply(embed=simple_embed(str(ve)))
    except discord.HTTPException as e:
        print(f"[MuteUser] {e}")
        await ctx.reply(embed=simple_embed(f"Failed to mute the user", 'cross'))
    except Exception as e:
        print(f"[MuteUser] {e}")
        await ctx.reply(embed=simple_embed(f"Failed to mute the user", 'cross'))

async def unmute(ctx: commands.Context, user: discord.Member):
    if not user.timed_out_until or user.timed_out_until <= discord.utils.utcnow():
        await ctx.reply(embed=simple_embed("That user is not muted currently", 'cross'))
        return

    try:
        await user.edit(timed_out_until=None, reason=f"Manual unmute by moderator {ctx.author.mention}")
        await ctx.reply(embed=simple_embed(f"Unmuted: <@{user.id}>"))

    except discord.HTTPException as e:
        await ctx.reply(embed=simple_embed(f"Failed to unmute user. {e}", 'cross'))
    except Exception as e:
        await ctx.reply(embed=simple_embed(f"Exception: {e}", 'cross'))

async def warn(ctx: commands.Context, member: discord.Member, reason: str, proofs=[]):
    await LilyLogging.LogModerationAction(ctx, ctx.author.id, member.id, "warn", reason, proofs)

    embed = warn_embed(ctx.author, reason, ctx.guild.name)
    try:
        await member.send(embed=embed)
    except Exception as e:
        print(e)

    await ctx.reply(embed=simple_embed(f"{member.mention} has been warned"))

async def execute(ctx: commands.Context, member: discord.Member):
    await ctx.defer()

    gif_dir = "src/ui/gifs"
    gifs = [f for f in os.listdir(gif_dir) if f.lower().endswith(".gif")]

    if not gifs:
        await ctx.reply("No GIFs found.")
        return

    path = os.path.join(gif_dir, random.choice(gifs))

    message = await ctx.reply(
        file=discord.File(path, filename="execute.gif")
    )

    frame_buffer, seconds = await GIFM.ExtractLastFrame(path)

    await asyncio.sleep(seconds - 0.07)

    await message.delete()

    await ctx.reply(
        content=f"**{ctx.author.display_name} executed {member.display_name}**",
        file=discord.File(frame_buffer, filename="last_frame.png")
    )

async def CaseEdit(ctx: commands.Context, case_id: int, case_statement: str, absolute: bool=False):
    response = await edit_case({"staff_id": ctx.author.id, "case_id": case_id, "case_statement": case_statement, "absolute": absolute})

    if response.get("success"):
        await ctx.reply(embed=simple_embed(response.get("message")))
    else:
        await ctx.reply(embed=simple_embed(response.get("message"), 'cross'))
