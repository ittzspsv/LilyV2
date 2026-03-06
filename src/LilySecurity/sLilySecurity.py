import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import time
from typing import Dict, Deque, DefaultDict
import re

from LilyUtility.sLilyUtility import utcnow

security_info = {
    'channel_deletion_limit' : 3,
    'channel_deletion_cooldown' : 8,
    'role_deletion_limit' : 3,
    'role_deletion_cooldown' : 8,
    "ping_limit" : 1,
    "ping_cd" : 8,
    "role_ping_limit" : 1,
    "role_ping_cd" : 8
}

ping_limit = 3
time_window = 10 * 60


guild_channel_deletions = defaultdict(lambda: defaultdict(lambda: deque()))
guild_role_deletions = defaultdict(lambda: defaultdict(lambda: deque()))


role_mention_regex = re.compile(r"<@&(\d+)>")
role_ping_tracker: DefaultDict[int, DefaultDict[int, Deque[float]]] = defaultdict(lambda: defaultdict(deque))
role_ping_strikes: DefaultDict[int, DefaultDict[int, int]] = defaultdict(lambda: defaultdict(int))

async def LilySecurityJoinWindow(bot, member: discord.Member):
    if member.bot:
        try:
            if not member.public_flags.verified_bot:
                await member.kick(reason="Bot is not verified. Kicking Out!")

                cursor = await VC.cdb.execute(
                    "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
                    (member.guild.id,)
                )
                row = await cursor.fetchone()
                await cursor.close()

                if row and row[0]:
                    try:
                        log_channel = await bot.fetch_channel(row[0])
                        if log_channel:
                            target_adder = None
                            async for i in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                                if i.target.id == member.id:
                                    target_adder = i.user
                            embed = discord.Embed(
                                color=16777215,
                                title=f"{Configs.emoji['arrow']} Security Act",
                                description=f"- An Unknown Bot {member.mention} without verification has been added to the server by {target_adder.mention}.  Kicking it out!",
                            )
                            embed.set_footer(
                                text="Security Powered by Lily",
                            )

                            await log_channel.send(embed=embed)
                    except:
                        pass

        except:
            pass

async def LilyEventActionChannelDelete(channel: discord.abc.GuildChannel):
    guild_id = channel.guild.id
    actor = None

    try:
        async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                actor = entry.user
                break
    except Exception as e:
        print(f"Error fetching audit logs: {e}")
        return

    if not actor:
        return

    queue = guild_channel_deletions[guild_id][actor.id]
    queue.append(datetime.now(timezone.utc))

    cooldown = timedelta(seconds=security_info['channel_deletion_cooldown'])

    while queue and datetime.now(timezone.utc) - queue[0] > cooldown:
        queue.popleft()

    if len(queue) >= security_info['channel_deletion_limit']:
        try:
            await actor.kick(reason="Lily Security : Exceeded channel deletion limit")
        except:
            try:
                await actor.edit(roles=[])
            except:
                pass

        log_channel = None
        cursor = await VC.cdb.execute(
                    "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
                    (channel.guild.id,)
                )
        row = await cursor.fetchone()
        log_channel = channel.guild.get_channel(row[0])
        await cursor.close()

        if log_channel:
            embed = discord.Embed(
                color=0xFFFFFF,
                title=f"{Configs.emoji['arrow']} Security Act",
                description=f"- {actor.mention} has exceeded channel deletion limit. Action taken.",
            )
            await log_channel.send(embed=embed)

        queue.clear()

async def LilyEventActionRoleDelete(role: discord.Role):
    guild_id = role.guild.id
    actor = None

    try:
        async for entry in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                actor = entry.user
                break
    except Exception as e:
        return

    if not actor:
        return

    queue = guild_role_deletions[guild_id][actor.id]
    queue.append(datetime.now(timezone.utc))

    cooldown = timedelta(seconds=security_info['role_deletion_cooldown'])

    while queue and datetime.now(timezone.utc) - queue[0] > cooldown:
        queue.popleft()

    if len(queue) >= security_info['role_deletion_limit']:
        try:
            await actor.kick(reason="Lily Security : Exceeded role deletion limit")
        except:
            try:
                await actor.edit(roles=[])
            except:
                pass

        log_channel = None
        cursor = await VC.cdb.execute(
                    "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
                    (role.guild.id,)
                )
        row = await cursor.fetchone()
        log_channel = role.guild.get_channel(row[0])
        await cursor.close()

        if log_channel:
            embed = discord.Embed(
                color=0xFFFFFF,
                title=f"{Configs.emoji['arrow']} Security Act",
                description=f"- {actor.mention} has exceeded role deletion limit. Action taken.",
            )
            await log_channel.send(embed=embed)

        queue.clear()

async def elevated_ping_evaluation(message: discord.Message):
    guild = message.guild
    member: discord.Member = message.author
    bot_member: discord.Member = guild.me

    if not message.mention_everyone:
        return

    if member.top_role >= bot_member.top_role:
        return

    try:
        await message.delete()
    except discord.Forbidden:
        return

    try:
        await guild.ban(
            member,
            reason="Security violation: Unauthorized @everyone/@here mention",
            delete_message_days=0
        )
    except discord.Forbidden:
        return 

    log_channel = None
    cursor = await VC.cdb.execute(
        """
            SELECT cc.logs_channel
            FROM ConfigData cd
            JOIN ConfigChannels cc
                ON cd.channel_config_id = cc.channel_config_id
            WHERE cd.guild_id = ?
            AND cc.logs_channel IS NOT NULL
        """,
        (guild.id,)
    )
    row = await cursor.fetchone()
    await cursor.close()

    if row:
        log_channel = guild.get_channel(row[0])
        if not log_channel:
            try:
                log_channel = await guild.fetch_channel(row[0])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

    if log_channel:
        embed = discord.Embed(
            color=0xFFFFFF,
            title=f"{Configs.emoji['arrow']} Security Act",
            description=(
                f"**Action:** Auto-ban\n"
                f"**User:** {member.mention} (`{member.id}`)\n"
                f"**Reason:** Unauthorized @everyone/@here mention"
            ),
        )
        embed.set_footer(text=f"Lily Security • {guild.name}")

        await log_channel.send(embed=embed)

async def role_ping_rate_limiter(message: discord.Message):
    if not message.guild or not isinstance(message.author, discord.Member):
        return

    guild = message.guild
    member = message.author
    bot_member = guild.me

    if member.id == guild.owner_id or member.top_role.position >= bot_member.top_role.position:
        return

    if not role_mention_regex.search(message.content):
        return

    now = utcnow().timestamp()
    dq = role_ping_tracker[guild.id][member.id]

    while dq and now - dq[0] > time_window:
        dq.popleft()

    dq.append(now)
    print(len(dq))

    if len(dq) <= ping_limit:
        return

    role_ping_strikes[guild.id][member.id] += 1
    strikes = role_ping_strikes[guild.id][member.id]

    

    if strikes == 1:
        remaining = time_window
        if dq:
            remaining = max(0, time_window - (now - dq[0]))

        minutes = int(remaining) // 60
        seconds = int(remaining) % 60
        cooldown_text = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

        try:
            await member.send(
                "Hello! You reached your **Role Mention Limit**.\n"
                f"Limit: {ping_limit} per 10 minutes.\n"
                f"Cooldown resets in: {cooldown_text}\n"
                "Pinging again may result in role removal. 😊"
            )
        except discord.Forbidden:
            pass
        return


    if strikes >= 2:
        roles_to_remove = [
            role for role in member.roles
            if role != guild.default_role and role < bot_member.top_role
        ]

        if roles_to_remove:
            try:
                await member.remove_roles(
                    *roles_to_remove,
                    reason="Excessive Role Pings"
                )

                dq.clear()
            except (discord.Forbidden, discord.HTTPException):
                return

        role_ping_strikes[guild.id].pop(member.id, None)

        cursor = await VC.cdb.execute(
            """
            SELECT cc.logs_channel
            FROM ConfigData cd
            JOIN ConfigChannels cc
                ON cd.channel_config_id = cc.channel_config_id
            WHERE cd.guild_id = ?
            AND cc.logs_channel IS NOT NULL
            """,
            (guild.id,)
        )
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return

        log_channel = guild.get_channel(row[0])
        if not log_channel:
            try:
                log_channel = await guild.fetch_channel(row[0])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        embed = discord.Embed(
            title="Security Act",
            description=(
                f"**Action:** Auto-Role-Strip\n"
                f"**User:** {member.mention} (`{member.id}`)\n"
                "**Reason:** Reached Role Rate Limits."
            ),
            color=0xFFFFFF
        )
        embed.set_footer(text=f"Lily Security • {guild.name}")

        await log_channel.send(embed=embed)
    
async def LilySecurityEvaluate(message: discord.Message):
    if message.author.bot:
        return

    if message.reference is not None:
        return

    if not message.guild:
        return
    
    # Prevents @everyone/@here ping.
    await elevated_ping_evaluation(message)
    await role_ping_rate_limiter(message)