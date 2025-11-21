from datetime import datetime

from discord.ext import commands
import discord
import Config.sValueConfig as VC
import Config.sBotDetails as Configs
import aiosqlite
import pytz

mdb = None

async def initialize():
    global mdb
    mdb = await aiosqlite.connect("storage/logs/Logs.db")
    await mdb.execute("""
        CREATE TABLE IF NOT EXISTS modlogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            moderator_id INTEGER,
            target_user_id INTEGER,
            mod_type TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """)
    await mdb.commit()

async def WriteLog(ctx: commands.Context, user_id: int, log_txt: str):
    global mdb
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await mdb.execute("""
        INSERT INTO botlogs (guild_id, user_id, timestamp, log)
        VALUES (?, ?, ?, ?)
    """, (ctx.guild.id, user_id, timestamp, log_txt))
    await mdb.commit()

    cursor = await VC.cdb.execute(
        "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
        (ctx.guild.id,)
    )
    row = await cursor.fetchone()
    await cursor.close()

    if not row or not row[0]:
        return

    channel = ctx.bot.get_channel(row[0])
    if not channel:
        return

    embed = (
        discord.Embed(
            color=16777215,
            title=f"{Configs.emoji['ticket']} Logging Information",
        )
        .set_footer(text=timestamp)
        .add_field(
            name=f"{Configs.emoji['member']} User",
            value=f"<@{user_id}>",
            inline=True,
        )
        .add_field(
            name=f"{Configs.emoji['pencil']} Reason",
            value=log_txt,
            inline=False,
        )
    )

    await channel.send(embed=embed)

async def LogModerationAction(ctx: commands.Context,moderator_id: int,target_user_id: int,mod_type: str,reason: str = "No reason provided",proofs=[]):
    global mdb
    timestamp = datetime.now(pytz.utc).isoformat()

    await mdb.execute("""
        INSERT INTO modlogs (guild_id, moderator_id, target_user_id, mod_type, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ctx.guild.id, moderator_id, target_user_id, mod_type.lower(), reason, timestamp))
    await mdb.commit()

    cursor = await VC.cdb.execute(
        "SELECT logs_channel FROM ConfigData WHERE guild_id = ? AND logs_channel IS NOT NULL",
        (ctx.guild.id,)
    )
    row = await cursor.fetchone()
    await cursor.close()

    if not row or not row[0]:
        return

    channel = ctx.bot.get_channel(row[0])
    if not channel:
        return

    main_embed = discord.Embed(
        color=16777215,
        url="https://discohook.app#gallery-G2oFSRb8",
        title=f"{Configs.emoji['ticket']} Logging Information",
        timestamp=datetime.utcnow()
    )
    main_embed.add_field(name=f"{Configs.emoji['bookmark']} Case Type", value=mod_type.title(), inline=True)
    main_embed.add_field(name=f"{Configs.emoji['member']} User", value=f"<@{target_user_id}>", inline=True)
    main_embed.add_field(name=f"{Configs.emoji['shield']} Moderator", value=f"<@{moderator_id}>", inline=True)
    main_embed.add_field(name=f"{Configs.emoji['pencil']} Reason", value=reason, inline=False)

    embeds_to_send = []

    if proofs:
        main_embed.add_field(name=f"{Configs.emoji['logs']} Proofs", value="", inline=False)

        first_proof = proofs[0]
        if isinstance(first_proof, discord.Attachment):
            main_embed.set_image(url=first_proof.url)
        elif isinstance(first_proof, str):
            main_embed.set_image(url=first_proof)

        embeds_to_send.append(main_embed)

        for proof in proofs[1:]:
            proof_embed = discord.Embed(url="https://discohook.app#gallery-G2oFSRb8")
            if isinstance(proof, discord.Attachment):
                proof_embed.set_image(url=proof.url)
            elif isinstance(proof, str):
                proof_embed.set_image(url=proof)
            embeds_to_send.append(proof_embed)
    else:
        main_embed.add_field(name=f"{Configs.emoji['logs']} Proofs", value="No Proofs Provided", inline=False)
        embeds_to_send.append(main_embed)

    await channel.send(embeds=embeds_to_send)
            
async def PostLog(ctx: commands.Context, embed: discord.Embed):
    channel = ctx.bot.get_channel(1325204537434312856)

    if channel is None:
        channel = await ctx.bot.fetch_channel(1325204537434312856)

    await channel.send(embed=embed)