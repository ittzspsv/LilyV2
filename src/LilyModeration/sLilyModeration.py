import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
import pytz
import re
import asyncio
import ui.sGIFManipulation as GIFM
import LilyManagement.sLilyStaffManagement as LSM

import Config.sBotDetails as Config
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from discord.utils import utcnow
import os
import random


async def exceeded_ban_limit(ctx: commands.Context, moderator_id: int, moderator_role_ids: list[int]):
    if not moderator_role_ids:
        return False

    placeholders = ",".join("?" * len(moderator_role_ids))
    query = f"""
        SELECT role_id, ban_limit
        FROM roles
        WHERE ban_limit > -1 AND role_id IN ({placeholders})
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
        cursor = await LSM.sdb.execute(query, moderator_role_ids)
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

        embed1 = (
            discord.Embed(
                title=f"{Config.emoji['arrow']} {user.display_name}'s Moderation Stats",
                colour=16777215,
            )
            .set_thumbnail(url=user.avatar.url if user.avatar else Config.img['member'])
            .set_image(url=Config.img['border'])
            .add_field(name=f"{Config.emoji['logs']} Total Logs", value=str(total_logs), inline=True)
            .add_field(name=f"{Config.emoji['shield']} Moderator ID", value=str(moderator_id), inline=True)
            .add_field(name=f"{Config.emoji['calender']} Date", value=now.strftime("%Y-%m-%d"), inline=True)
        )

        embed2 = (
            discord.Embed(title=f"{Config.emoji['arrow']} Moderation Statistics Overview", colour=16777215)
            .set_thumbnail(url="https://media.discordapp.net/attachments/1366840025010012321/1438061680541306880/staff.png")
            .set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")
            .add_field(
                name=f"{Config.emoji['mute']} Mutes",
                value=f"7d: `{stats['mute']['7d']}`\n30d: `{stats['mute']['30d']}`\nTotal: `{stats['mute']['total']}`",
                inline=True
            )
            .add_field(
                name=f"{Config.emoji['warn']} Warns",
                value=f"7d: `{stats['warn']['7d']}`\n30d: `{stats['warn']['30d']}`\nTotal: `{stats['warn']['total']}`",
                inline=True
            )
            .add_field(
                name=f"{Config.emoji['ban_hammer']} Bans",
                value=f"7d: `{stats['ban']['7d']}`\n30d: `{stats['ban']['30d']}`\nTotal: `{stats['ban']['total']}`",
                inline=True
            )
            .add_field(
                name=f"{Config.emoji['ban_hammer']} Quarantines",
                value=f"7d: `{stats['quarantine']['7d']}`\n30d: `{stats['quarantine']['30d']}`\nTotal: `{stats['quarantine']['total']}`",
                inline=True
            ))
        

        logs_text = ""
        for index, log in enumerate(shown_logs, start=1):
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
                description=logs_text or "No logs to display.",
                colour=16777215
            ).set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")

            return [embed1, embed2, embed_logs]
        else:
            return [embed1, embed2]

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
            {
                "moderator_id": row[3],
                "mod_type": row[0].lower(),
                "reason": row[1],
                "timestamp": row[2],
            }
            for row in rows
        ]

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
        embed_summary.add_field(name="Logs Summary", value=summary_text or "No actions recorded", inline=False)


        embed_logs = (
            discord.Embed(
                color=16777215,
                title=f"{Config.emoji['arrow']} Log's Overview",
            )
            .set_thumbnail(url=Config.img['logs'])
            .set_image(url=Config.img['border'])
        )

        for index, log in enumerate(display_logs, start=1):
            try:
                dt = datetime.fromisoformat(log["timestamp"])
            except ValueError:
                dt = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")
            ts_unix = int(dt.timestamp())

            reason_text = log["reason"] if log["reason"] else "No reason provided"
            embed_logs.add_field(
                name=f"📌 Log #{index} • {log['mod_type'].title()}",
                value=(
                    f"> {Config.emoji['shield']} Moderator : <@{log['moderator_id']}>\n"
                    f"> {Config.emoji['pencil']} Reason : **{reason_text}**\n"
                    f"> {Config.emoji['clock']} Time : <t:{ts_unix}:R>"
                ),
                inline=False,
            )

        return [embed_summary, embed_logs]

    except Exception as e:
        print("Error in mod_logs:", e)
        return SimpleEmbed(f"Exception {e}", 'cross')

def SimpleEmbed(message: str, s_emoji: str='checked'):
    return discord.Embed(
        color=16777215,
        description=f"{Configs.emoji[s_emoji.lower()]} **{message}**",
    )

def BanEmbed(moderator: discord.Member, reason, appealLink, server_name):
    embed = (
        discord.Embed(
            color=0xFFFFFF,
            title=f"{Config.emoji['arrow']} You Have Been Banned!",
        )
        .set_image(url=Config.img['border'])
        .add_field(
            name=f"{Config.emoji['bookmark']} Reason",
            value=reason,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['shield']} Moderator",
            value=moderator.name,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['bot']} Server",
            value=server_name,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['ban_hammer']} Appeal Your Ban Here",
            value=f"If you think your ban was wrongly done, please make an appeal here: {appealLink}",
            inline=False,
        )
    )
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
    try:
        cur = await VC.cdb.execute("SELECT value FROM GlobalConfigs WHERE key = 'Jail'")
        row = await cur.fetchone()
        jail_value = int(row[0] or 0)
    except Exception:
        jail_value = 0

    role_ids = [str(r.id) for r in ctx.author.roles]
    if role_ids:
        placeholders = ",".join("?" * len(role_ids))
        cursor = await LSM.sdb.execute(
            f"SELECT role_id FROM roles WHERE ban_limit > -1 AND role_id IN ({placeholders})",
            role_ids
        )
        valid_limit_roles = [row[0] for row in await cursor.fetchall()]
    else:
        valid_limit_roles = []

    if not valid_limit_roles:
        return await ctx.send(embed=SimpleEmbed("You don't have permission to perform a ban.", 'cross'))

    try:
        user_id = user_input.id
    except AttributeError:
        try:
            user_id = int(user_input)
        except ValueError:
            return await ctx.send(embed=SimpleEmbed("Invalid user id", 'cross'))

    member_obj = user_input if isinstance(user_input, discord.Member) else None
    user_obj = user_input if isinstance(user_input, discord.User) else None

    if member_obj:
        if (
            member_obj.top_role >= ctx.guild.me.top_role or
            member_obj.top_role >= ctx.author.top_role or
            member_obj.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}
        ):
            return await ctx.send(embed=SimpleEmbed("Cannot moderate this user.", 'cross'))


    if await exceeded_ban_limit(ctx, ctx.author.id, valid_limit_roles):
        return await ctx.send(embed=SimpleEmbed("You have exceeded your daily ban limit.", 'cross'))

    target = member_obj or user_obj

    try:
        await target.send(embed=BanEmbed(ctx.author, reason, Config.appeal_server_link, ctx.guild.name))
    except Exception:
        pass

    try:
        if jail_value == 0:
            await ctx.guild.ban(
                discord.Object(id=user_id),
                reason=f"By {ctx.author} (ID: {ctx.author.id}) | Reason: {reason}"
            )
            await LilyLogging.LogModerationAction(ctx, ctx.author.id, user_id, "ban", reason, proofs.copy())
            remaining = await remaining_ban_count(ctx, ctx.author.id, valid_limit_roles)

            return await ctx.send(embed=SimpleEmbed(
                f"Banned: <@{user_id}>\n**Bans Remaining:** {remaining}"
            ))

        if not member_obj:
            return await ctx.send(embed=SimpleEmbed(
                "Cannot quarantine; user is no longer in the guild.", 'cross'
            ))

        quarantine_role = (
            discord.utils.get(ctx.guild.roles, name="Quarantine")
            or discord.utils.get(ctx.guild.roles, name="Prisoner")
        )

        if not quarantine_role or quarantine_role >= ctx.guild.me.top_role:
            return await ctx.send(embed=SimpleEmbed(
                "Quarantine role issue: not found or too high.", 'cross'
            ))


        if not any(role.name == "Quarantine" for role in member_obj.roles):
            await member_obj.edit(
                roles=[ctx.guild.default_role, quarantine_role],
                reason=f"Quarantine applied by {ctx.author} | {reason}"
            )
            await LilyLogging.LogModerationAction(ctx, ctx.author.id, user_id, "quarantine", reason, proofs.copy())
            remaining = await remaining_ban_count(ctx, ctx.author.id, valid_limit_roles)

            return await ctx.send(embed=SimpleEmbed(
                f"Quarantined: <@{user_id}>\n**Quarantines Remaining:** {remaining}"
            ))
        else:
            return await ctx.send(embed=SimpleEmbed(
                f"Quarantine Cannot be applied, Member is already quarantined"
            ))

    except discord.HTTPException as e:
        return await ctx.send(embed=SimpleEmbed(f"Failed to perform moderation action: {e}", 'cross'))
    except Exception as e:
        return await ctx.send(embed=SimpleEmbed(f"Unhandled Exception: {e}", 'cross'))

async def mute_user(ctx: commands.Context, user: discord.Member, duration: str, reason: str = "No reason provided", proofs: list = []):
    if user.top_role >= ctx.guild.me.top_role:
        await ctx.send(embed=SimpleEmbed("I cannot mute this user", 'cross'))
        return

    if user.top_role >= ctx.author.top_role:
        await ctx.send(embed=SimpleEmbed("I cannot mute a user with a role equal to or higher than yours.", 'cross'))
        return

    if user.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}:
        await ctx.send(embed=SimpleEmbed("Exception!. Stupid action detected errno 77777", 'cross'))
        return

    try:
        seconds = MuteParser(duration)
        until = utcnow() + timedelta(seconds=seconds)

        try:
            embed = (
                discord.Embed(
                    color=0xFFFFFF,
                    title=f"{Config.emoji['arrow']} YOU HAVE BEEN MUTED!",
                )
                .set_image(url=Config.img['border'])
                .add_field(
                    name=f"Config.emoji['bookmark'] Reason",
                    value=reason,
                    inline=False,
                )
                .add_field(
                    name=f"{Config.emoji['shield']} Moderator",
                    value=ctx.author.mention,
                    inline=False,
                )
                .add_field(
                    name=f"{Config.emoji['bot']} Server",
                    value=ctx.guild.name,
                    inline=False,
                )
                .add_field(
                    name=f"{Config.emoji['ban_hammer']} Appeal Your Ban Here",
                    value=f"If you think your mute was wrongly done, please make an appeal here: {Config.appeal_server_link}",
                    inline=False,
                )
            )

            await user.send(embed=embed)
        except Exception as e:
            print("DM failed:", e)

        await user.edit(timed_out_until=until, reason=reason)

        await ctx.send(embed=SimpleEmbed(
            f"Muted: <@{user.id}>"
        ))

        await LilyLogging.LogModerationAction(ctx, ctx.author.id, user.id, "mute", reason, proofs)

    except ValueError as ve:
        await ctx.send(embed=SimpleEmbed(str(ve)))
    except discord.HTTPException as e:
        print(f"[MuteUser] {e}")
        await ctx.send(embed=SimpleEmbed(f"Failed to mute the user", 'cross'))
    except Exception as e:
        print(f"[MuteUser] {e}")
        await ctx.send(embed=SimpleEmbed(f"Failed to mute the user", 'cross'))

async def unmute(ctx: commands.Context, user: discord.Member):
    if not user.timed_out_until or user.timed_out_until <= discord.utils.utcnow():
        await ctx.send(embed=SimpleEmbed("That user is not muted currently", 'cross'))
        return

    try:
        await user.edit(timed_out_until=None, reason=f"Manual unmute by moderator {ctx.author.mention}")
        await ctx.send(embed=SimpleEmbed(f"Unmuted: <@{user.id}>"))

    except discord.HTTPException as e:
        await ctx.send(embed=SimpleEmbed(f"Failed to unmute user. {e}", 'cross'))
    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Exception: {e}", 'cross'))

async def warn(ctx: commands.Context, member: discord.Member, reason: str, proofs=[]):
    await LilyLogging.LogModerationAction(ctx, ctx.author.id, member.id, "warn", reason, proofs)

    embed = discord.Embed(
        color=16777215,
        title=f"{Config.emoji['arrow']} You Have Been Warned!",
    )
    embed.set_thumbnail(url=Config.img['warn'])
    embed.add_field(
        name=f"{Config.emoji['bookmark']} Reason",
        value=reason,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['shield']} Moderator",
        value=f"<@{ctx.author.id}>",
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['bot']} Server",
        value=ctx.guild.name,
        inline=False,
    )

    try:
        await member.send(embed=embed)
    except Exception as e:
        print(e)

    await ctx.send(embed=SimpleEmbed(f"{member.mention} has been warned"))

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