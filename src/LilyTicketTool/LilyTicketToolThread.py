import discord
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from pathlib import Path
import json
import Config.sBotDetails as Configs
import os
import Misc.sLilyEmbed as LilyEmbed
from LilyTicketTool.components.LilyTicketToolComponents import TicketSelector, TicketEmbed, TicketComponentEmbed
import LilyTicketTool.components.LilyTicketToolComponents as LTTC
from LilyUtility.sLilyUtility import load_json
import asyncio
import json

import DiscordTranscript
import io




TICKET_VIEWS_PATH = Path("storage/view/TicketViews.json")

def save_ticket_view(channel_id: int, message_id: int, config: dict, guild_id: int):
    all_data = []
    if TICKET_VIEWS_PATH.exists():
        with open(TICKET_VIEWS_PATH, "r") as f:
            try:
                content = f.read().strip()
                if content:
                    all_data = json.loads(content)
            except json.JSONDecodeError:
                all_data = []

    all_data.append({
        "channel_id": channel_id,
        "message_id": message_id,
        "config": config,
        "guild_id" : guild_id
    })

    with open(TICKET_VIEWS_PATH, "w") as f:
        json.dump(all_data, f, indent=4)

async def InitializeTicketView(bot):
    try:
        json_data = load_json(TICKET_VIEWS_PATH)
        if not isinstance(json_data, list) or not json_data:
            print("[InitializeTicketView] No ticket panels found.")
            return

        updated = False

        for panel in json_data:
            try:
                config = panel.get("config")
                guild_id: int = panel.get("guild_id")
                if not config:
                    continue

                basic = config["BasicConfigurations"]

                channel_id = basic["TicketPanelSpawnChannel"]
                message_id = panel.get("message_id")

                content, embeds = LilyEmbed.ParseAdvancedEmbed(
                    config["EmbedConfigs"]["TicketPanelEmbed"]
                )
                if not isinstance(embeds, list):
                    embeds = [embeds]

                channel = bot.get_channel(channel_id)
                if not channel:
                    try:
                        channel = await bot.fetch_channel(channel_id)
                    except (discord.NotFound, discord.Forbidden):
                        continue

                selector_view = TicketSelector(config)
                bot.add_view(selector_view)

                try:
                    if message_id:
                        message = await channel.fetch_message(message_id)
                        await message.edit(
                            content=content,
                            embeds=embeds,
                            view=selector_view
                        )
                    else:
                        message = await channel.send(
                            content=content,
                            embeds=embeds,
                            view=selector_view
                        )
                        panel["message_id"] = message.id
                        updated = True
                except (discord.NotFound, discord.Forbidden):
                    continue

                try:
                    cursor = await LilyLogging.mdb.execute("SELECT ticket_id, opened_user_id,submission_json, message_id FROM tickets WHERE guild_id = ?", (guild_id,))
                    rows = await cursor.fetchall()

                    for ticket_id, opener_user_id, submission_json, message_id in rows:
                        view = TicketComponentEmbed(opener_user_id, ticket_id, json.loads(submission_json), config)
                        bot.add_view(view, message_id=message_id)
                except Exception as e:
                    print(f"Exception [Ticket Componnet Embed View] {e}")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"[TicketPanel Restore ERROR] {e}")


        if updated:
            with open(
                "src/LilyTicketTool/LilyTicketSelector.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(json_data, f, indent=4)

    except Exception as e:
        print(f"[InitializeTicketView ERROR] {e}")

async def spawn_ticket(ctx: commands.Context, json_data) -> None:
        content, embeds = LilyEmbed.ParseAdvancedEmbed(json_data["EmbedConfigs"]["TicketPanelEmbed"])
        channel_id = json_data["BasicConfigurations"]["TicketPanelSpawnChannel"]

        channel_obj = ctx.guild.get_channel(channel_id) or await ctx.guild.fetch_channel(channel_id)
        selector_view = TicketSelector(json_data)

        message_obj = await channel_obj.send(embeds=embeds, view=selector_view)
        save_ticket_view(channel_obj.id, message_obj.id, json_data, ctx.guild.id)

async def cTicketLogAction(ctx: commands.Context,thread: discord.Thread,opened_user_id: int,ticket_type: str,accessed_staff_ids: set, logs_channel: discord.TextChannel):
    embed = discord.Embed(
        title="Ticket Logs",
        description=f"### __TICKET DETAILS__\n> - Ticket Opener : <@{opened_user_id}>\n> - Ticket Thread Reference :  {thread.mention}",
        color=0xFFFFFF
    )

    embed.add_field(
        name="Ticket Thread ID",
        value=f"- ```{thread.id}```",
        inline=False
    )

    embed.add_field(
        name="Staff Closed Ticket",
        value=f"> - <@{ctx.author.id}>",
        inline=False
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

    embed.set_footer(text=ticket_type)
    try:
        await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed)
    except Exception as e:
        print(f"Exception [TicketLogAction] {e}")

async def cTicketLogActionChannel(ctx: commands.Context,opened_user_id: int,ticket_type: str, logs_channel: discord.TextChannel, transcripts_file):
    embed = discord.Embed(
        title="Ticket Logs",
        description=f"### __TICKET DETAILS__\n> - Ticket Opener : <@{opened_user_id}>\n",
        color=0xFFFFFF
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

    embed.set_footer(text=ticket_type)
    try:
        await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed, file=transcripts_file)
    except Exception as e:
        print(f"Exception [TicketLogAction] {e}")

async def cleanup_ticket_data(ticket_id: int):
        await LilyLogging.mdb.execute(
            "DELETE FROM tickets WHERE ticket_id = ?",
            (ticket_id,)
        )
        await LilyLogging.mdb.commit()

async def CloseTicketThread(ctx: commands.Context):
    await ctx.defer()
    await ctx.reply(embed=LilyEmbed.simple_embed("Ticket close scheduling has been initiated. The channel will be deleted shortly."))
    if not isinstance(ctx.channel, (discord.Thread, discord.TextChannel)):
        return await ctx.reply(
            embed=LilyEmbed.simple_embed(
                "Attempted to Close an invalid Instigator Ticket",
                "cross"
            )
        )

    thread = ctx.channel
    ticket_id: int = thread.id
    try:
        cursor = await LilyLogging.mdb.execute(
            """
            SELECT opened_user_id, ticket_type, log_channel_id, submission_json
            FROM tickets
            WHERE ticket_id = ?;
            """,
            (thread.id,)
        )

        row = await cursor.fetchone()
        if not row:
            raise RuntimeError("Ticket data not found")

        opened_user_id, ticket_type, logs_channel_id, submission_json_raw = row

        logs_channel = ctx.guild.get_channel(logs_channel_id)
        if not logs_channel:
            try:
                logs_channel = await ctx.guild.fetch_channel(logs_channel_id)
            except discord.NotFound:
                logs_channel = None


        if isinstance(ctx.channel, discord.Thread):
             thread.edit(archived=True, locked=True)
        elif isinstance(ctx.channel, discord.TextChannel):
            transcript = await DiscordTranscript.export(
                ctx.channel,
                limit=None,
                tz_info="America/New_York",
                military_time=True,
                bot=ctx.bot,
            )

            if transcript is None:
                return

            transcript_file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{ctx.channel.name}.html",
            )

            await ctx.channel.delete(reason=f"Ticket Closed by {ctx.author}")
            
        if logs_channel and isinstance(thread, discord.Thread):
            await cTicketLogAction(
                ctx=ctx,
                thread=thread,
                opened_user_id=opened_user_id,
                ticket_type=ticket_type,
                accessed_staff_ids=set(),
                logs_channel=logs_channel,

            )

        elif logs_channel and isinstance(thread, discord.TextChannel):
            await cTicketLogActionChannel(
                ctx=ctx,
                opened_user_id=opened_user_id,
                ticket_type=ticket_type,
                logs_channel=logs_channel,
                transcripts_file=transcript_file
            )


        await cleanup_ticket_data(ticket_id)

    except Exception as e:
        print(f"[TICKET CLOSE ERROR] {e}")
        await ctx.send(
            embed=LilyEmbed.simple_embed(
                "Attempted to Close an invalid Instigator Ticket",
                "cross"
            ),
            ephemeral=True
        )

async def RenameTicket(ctx: commands.Context, name: str):
    await ctx.defer()

    cursor = await LilyLogging.mdb.execute(
            """
            SELECT opened_user_id
            FROM tickets
            WHERE ticket_id = ?;
            """,
            (ctx.channel.id,)
        )
    row = await cursor.fetchone()
    if row and row[0]:
        await ctx.channel.edit(name=name.replace(" ", "_"), reason=f"Ticket renamed by {ctx.author}")
    else:
        await ctx.reply(embed=LilyEmbed.simple_embed("Attempted to rename an invalid Instigator Ticket"))
