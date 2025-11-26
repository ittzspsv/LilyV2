import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import time
import re

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


guild_channel_deletions = defaultdict(lambda: defaultdict(lambda: deque()))
guild_role_deletions = defaultdict(lambda: defaultdict(lambda: deque()))
spam_ping = defaultdict(lambda: defaultdict(lambda: deque()))
USER_MENTION_REGEX = re.compile(r"<@!?(\d+)>")
ROLE_MENTION_REGEX = re.compile(r"<@&(\d+)>")

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

async def LilySecurityEvaluate(bot, message: discord.Message):
    if message.author.bot:
        return

    if message.reference is not None:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    content = message.content
    now = time.time()

    user_pings = USER_MENTION_REGEX.findall(content)
    here_ping = "@here" in content
    everyone_ping = "@everyone" in content

    total_user_pings = len(user_pings) + (1 if here_ping else 0) + (1 if everyone_ping else 0)

    role_pings = ROLE_MENTION_REGEX.findall(content)
    total_role_pings = len(role_pings)

    if total_user_pings == 0 and total_role_pings == 0:
        return

    if guild_id not in spam_ping:
        spam_ping[guild_id] = {}
    if user_id not in spam_ping[guild_id]:
        spam_ping[guild_id][user_id] = {
            "user": deque(),
            "role": deque()
        }

    if total_user_pings > 0:
        uq = spam_ping[guild_id][user_id]["user"]

        for _ in range(total_user_pings):
            uq.append(now)

        while uq and now - uq[0] > security_info["ping_cd"]:
            uq.popleft()

        if len(uq) > security_info["ping_limit"]:
            
            member = message.author

            roles_to_remove = [r for r in member.roles if r != message.guild.default_role]
            try:
                await member.remove_roles(
                    *roles_to_remove,
                    reason="Lily Security: Excessive USER ping usage"
                )
            except Exception as e:
                print("Role removal failed:", e)

            timeout_seconds = security_info.get("timeout_seconds", 3600)
            try:
                await member.timeout(
                    discord.utils.utcnow() + timedelta(seconds=timeout_seconds),
                    reason="Excessive user ping usage"
                )
            except Exception as e:
                print("Timeout failed:", e)

            uq.clear()


            try:
                cursor = await VC.cdb.execute(
                    "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
                    (guild_id,)
                )
                row = await cursor.fetchone()
                await cursor.close()

                if row:
                    log_channel = message.guild.get_channel(row[0])
                    if log_channel:
                        embed = discord.Embed(
                            color=0xFFFFFF,
                            title=f"{Configs.emoji['arrow']} Security Act",
                            description=f"- {member.mention} exceeded **user ping limit**! Action Taken."
                        )
                        await log_channel.send(embed=embed)

            except Exception as e:
                print("Logging failed:", e)

    if total_role_pings > 0:
        rq = spam_ping[guild_id][user_id]["role"]

        # Add pings
        for _ in range(total_role_pings):
            rq.append(now)

        while rq and now - rq[0] > security_info["role_ping_cd"]:
            rq.popleft()

        if len(rq) > security_info["role_ping_limit"]:

            member = message.author

            roles_to_remove = [r for r in member.roles if r != message.guild.default_role]
            try:
                await member.remove_roles(
                    *roles_to_remove,
                    reason="Lily Security: Excessive ROLE ping usage"
                )
            except Exception as e:
                print("Role removal failed:", e)

            timeout_seconds = security_info.get("timeout_seconds", 3600)
            try:
                await member.timeout(
                    discord.utils.utcnow() + timedelta(seconds=timeout_seconds),
                    reason="Excessive role ping usage"
                )
            except Exception as e:
                print("Timeout failed:", e)

            rq.clear()

            try:
                cursor = await VC.cdb.execute(
                    "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
                    (guild_id,)
                )
                row = await cursor.fetchone()
                await cursor.close()

                if row:
                    log_channel = message.guild.get_channel(row[0])
                    if log_channel:
                        embed = discord.Embed(
                            color=0xFFFFFF,
                            title=f"{Configs.emoji['arrow']} Security Act",
                            description=f"- {member.mention} exceeded **role ping limit**! Action Taken."
                        )
                        await log_channel.send(embed=embed)

            except Exception as e:
                print("Logging failed:", e)