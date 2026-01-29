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

async def LilySecurityEvaluate(message: discord.Message):
    if message.author.bot:
        return

    if message.reference is not None:
        return

    if not message.guild:
        return

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
        SELECT logs_channel
        FROM ConfigData
        WHERE guild_id = ? AND logs_channel IS NOT NULL
        """,
        (guild.id,)
    )
    row = await cursor.fetchone()
    await cursor.close()

    if row:
        log_channel = guild.get_channel(row[0])

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