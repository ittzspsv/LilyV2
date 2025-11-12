import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
import pytz
import re
import LilyManagement.sLilyStaffManagement as LSM

import Config.sBotDetails as Config
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from discord.utils import utcnow


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

        embed1 = (
            discord.Embed(
                title=f"{Config.emoji['arrow']} ShreeSPSV'S Moderation Stats",
                colour=16777215,
            )
            .set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")
            .set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")
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
        )

        logs_text = ""
        for index, log in enumerate(shown_logs, start=1):
            ts_unix = int(log["timestamp"].timestamp())  # Unix timestamp
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
            .set_thumbnail(url=user.avatar.url if user.avatar else "https://example.com/default_avatar.png")
            .set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")
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
            .set_thumbnail(url="https://media.discordapp.net/attachments/1366840025010012321/1438064934574493768/logs.png")
            .set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png")
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
        return SimpleEmbed(f"Something went wrong while retrieving logs: {e}")

def SimpleEmbed(message: str, s_emoji: str='checked'):
    return discord.Embed(
        color=16777215,
        description=f"{Configs.emoji[s_emoji]} **{message}**",
    )

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
    try:
        cur = await VC.cdb.execute("SELECT value FROM GlobalConfigs WHERE key = 'Jail'")
        row = await cur.fetchone()
        jail_value = int(row[0]) if row and row[0] is not None else 0
    except Exception:
        jail_value = 0

    author_role_ids = [role.id for role in ctx.author.roles]
    role_ids = [str(rid) for rid in author_role_ids]
    if role_ids:
        placeholders = ",".join("?" * len(role_ids))
        query = f"SELECT role_id FROM roles WHERE ban_limit > 0 AND role_id IN ({placeholders})"
        cursor = await LSM.sdb.execute(query, role_ids)
        rows = await cursor.fetchall()
        valid_limit_roles = [row[0] for row in rows]
    else:
        valid_limit_roles = []

    if not valid_limit_roles:
        await ctx.send(embed=SimpleEmbed("You don't have permission to perform a ban."))
        return

    try:
        user_id = user_input.id if isinstance(user_input, (discord.User, discord.Member)) else int(user_input)
    except ValueError:
        await ctx.send(embed=SimpleEmbed("Invalid user id"))
        return

    member_obj = ctx.guild.get_member(user_id)
    user_obj = None

    if not member_obj:
        try:
            member_obj = await ctx.guild.fetch_member(user_id)
        except discord.NotFound:
            try:
                user_obj = await ctx.bot.fetch_user(user_id)
            except discord.NotFound:
                await ctx.send(embed=SimpleEmbed("User not found on Discord.", 'cross'))
                return
            except discord.HTTPException as e:
                await ctx.send(embed=SimpleEmbed(f"Exception fetching user: {e}", 'cross'))
                return
        except discord.HTTPException as e:
            await ctx.send(embed=SimpleEmbed(f"Exception fetching member: {e}", 'cross'))
            return

    if member_obj:
        if member_obj.top_role >= ctx.guild.me.top_role:
            await ctx.send(embed=SimpleEmbed("I cannot moderate this user; their role is higher than mine!"))
            return
        if member_obj.top_role >= ctx.author.top_role:
            await ctx.send(embed=SimpleEmbed("You cannot moderate a user with an equal or higher role."))
            return
        if member_obj.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}:
            await ctx.send(embed=SimpleEmbed("You cannot moderate the owner, yourself, or the bot!"))
            return

    if await exceeded_ban_limit(ctx, ctx.author.id, valid_limit_roles):
        await ctx.send(embed=SimpleEmbed("You have exceeded your daily ban limit."))
        return

    try:
        target = member_obj or user_obj

        try:
            await target.send(embed=BanEmbed(ctx.author, reason, Config.appeal_server_link, ctx.guild.name))
        except Exception:
            pass

        if jail_value == 0:
            await ctx.guild.ban(discord.Object(id=user_id),
                reason=f"By {ctx.author} (ID: {ctx.author.id}) | Reason: {reason}"
            )
            await LilyLogging.LogModerationAction(ctx, ctx.author.id, user_id, "ban", reason)
            remaining = await remaining_ban_count(ctx, ctx.author.id, valid_limit_roles)
            await ctx.send(embed=SimpleEmbed(f"Banned: <@{user_id}>\n**Bans Remaining:** {remaining}"))
        else:
            if not member_obj:
                await ctx.send(embed=SimpleEmbed("Cannot quarantine; user is no longer in the guild.", 'cross'))
                return

            quarantine_role = discord.utils.get(ctx.guild.roles, name="Quarantine")
            if not quarantine_role:
                await ctx.send(embed=SimpleEmbed("Quarantine role not found. Cannot apply quarantine."))
                return
            if quarantine_role >= ctx.guild.me.top_role:
                await ctx.send(embed=SimpleEmbed("Cannot assign quarantine role; it is higher than my top role."))
                return

            await member_obj.add_roles(quarantine_role, reason=f"Quarantine applied by {ctx.author} | {reason}")
            await LilyLogging.LogModerationAction(ctx, ctx.author.id, user_id, "quarantine", reason)
            await ctx.send(embed=SimpleEmbed(f"Quarantined: <@{user_id}>"))

    except discord.HTTPException as e:
        await ctx.send(embed=SimpleEmbed(f"Failed to perform moderation action: {e}"))
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
            f"✅ Muted: <@{user.id}> for **Duration:** {duration}"
        ))

        await LilyLogging.LogModerationAction(ctx, ctx.author.id, user.id, "mute", reason)

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

    except discord.HTTPException as e:
        await ctx.send(embed=SimpleEmbed(f"Failed to unmute user. {e}"))
    except Exception as e:
        await ctx.send(embed=SimpleEmbed(f"Exception: {e}"))

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