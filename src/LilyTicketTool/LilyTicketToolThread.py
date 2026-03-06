import discord
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from pathlib import Path
import json
import Config.sBotDetails as Configs
import os
import Misc.sLilyEmbed as LilyEmbed
from LilyTicketTool.components.LilyTicketToolComponents import TicketSelector, TicketPanelView, TicketEmbed, SendTicketPanel
from LilyUtility.sLilyUtility import load_json
import asyncio

from typing import Union

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
                if not config:
                    continue

                basic = config["BasicConfigurations"]

                channel_id = basic["TicketPanelSpawnChannel"]
                log_channel_id = basic["TicketLoggingHandler"]
                message_id = panel.get("message_id")
                guild_id = panel.get("guild_id")

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

                selector_view = TicketSelector(bot, config)
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

                await asyncio.sleep(1)

                try:
                    cursor = await LilyLogging.mdb.execute(
                        """
                        SELECT 
                            t.ticket_id
                        FROM tickets AS t
                        WHERE t.guild_id = ?
                        """,
                        (guild_id,)
                    )

                    rows = await cursor.fetchall()

                    for (thread_id,) in rows:
                        thread = bot.get_channel(thread_id)
                        if not thread:
                            try:
                                thread = await bot.fetch_channel(thread_id)
                            except (discord.NotFound, discord.Forbidden):
                                continue

                        if not isinstance(thread, discord.Thread):
                            continue

                        view = TicketPanelView(thread, log_channel_id)
                        bot.add_view(view)

                except Exception as e:
                    print(f"[InitializeTicketView DB ERROR] {e}")

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
    try:
        content, embeds = LilyEmbed.ParseAdvancedEmbed(json_data["EmbedConfigs"]["TicketPanelEmbed"])
        channel_id = json_data["BasicConfigurations"]["TicketPanelSpawnChannel"]

        channel_obj = ctx.guild.get_channel(channel_id) or await ctx.guild.fetch_channel(channel_id)
        selector_view = TicketSelector(ctx.bot, json_data)

        message_obj = await channel_obj.send(embeds=embeds, view=selector_view)
        save_ticket_view(channel_obj.id, message_obj.id, json_data, ctx.guild.id)
    except Exception as e:
        print(e)

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

async def cleanup_ticket_data(thread: discord.Thread, message_id):
        ticket_id = thread.id
        await LilyLogging.mdb.execute(
            "DELETE FROM ticket_handlers WHERE ticket_id = ?",
            (ticket_id,)
        )
        await LilyLogging.mdb.execute(
            "DELETE FROM tickets WHERE ticket_id = ?",
            (ticket_id,)
        )

        await LilyLogging.mdb.execute(
            "DELETE FROM ticket_access_panels WHERE access_panel_message_id = ?",
            (message_id,) 
        )
        await LilyLogging.mdb.commit()

async def CloseTicketThread(ctx: commands.Context):
    await ctx.defer()
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        try:
            cursor = await LilyLogging.mdb.execute(
                """
                SELECT
                    t.opened_user_id,
                    t.ticket_type,
                    tae.tickets_access_panel_id,
                    tae.access_panel_message_id,    
                    th.accessed_staff,
                    t.log_channel_id
                FROM tickets AS t
                LEFT JOIN ticket_access_panels AS tae
                    ON tae.access_id = t.tickets_access_panel_id
                LEFT JOIN ticket_handlers AS th
                    ON th.ticket_id = t.ticket_id
                WHERE t.ticket_id = ?;
                """,
                (thread.id,)
            )

            rows = await cursor.fetchall()
            if not rows:
                raise RuntimeError("Ticket data not found")

            opened_user_id = rows[0][0]
            ticket_type = rows[0][1]            
            panel_channel_id = rows[0][2]
            panel_message_id = rows[0][3]
            logs_channel_id = rows[0][5]

            accessed_staff_ids = {row[4] for row in rows if row[4] is not None}

            opener = ctx.guild.get_member(opened_user_id)
            if not opener:
                try:
                    opener = await ctx.guild.fetch_member(opened_user_id)
                except:
                    opener = None
            if opener:
                await thread.remove_user(opener)

            accessed_staff_ids.discard(opened_user_id)
            accessed_staff_ids.discard(ctx.author.id)
            for staff_id in accessed_staff_ids:
                member = ctx.guild.get_member(staff_id)
                if not member:
                    try:
                        member = await ctx.guild.fetch_member(staff_id)
                    except:
                        continue
                try:
                    await thread.remove_user(member)
                except:
                    continue

            await thread.remove_user(ctx.author)

            await ctx.send(
                embed=LilyEmbed.simple_embed("Ticket closed successfully."),
                ephemeral=True
            )

            if panel_channel_id and panel_message_id:
                channel = ctx.guild.get_channel(panel_channel_id)
                if not channel:
                    try:
                        channel = await ctx.guild.fetch_channel(panel_channel_id)
                    except discord.NotFound:
                        channel = None

                if channel:
                    try:
                        msg = await channel.fetch_message(panel_message_id)
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass

            await thread.edit(archived=True, locked=True)
            logs_channel = ctx.guild.get_channel(logs_channel_id)
            if not logs_channel:
                logs_channel = await ctx.guild.fetch_channel(logs_channel_id)
            await cTicketLogAction(
                ctx=ctx,
                thread=thread,
                opened_user_id=opened_user_id,
                ticket_type=ticket_type,
                accessed_staff_ids=accessed_staff_ids,
                logs_channel=logs_channel
            )

            await cleanup_ticket_data(thread, panel_message_id)

        except Exception as e:
            print(f"[TICKET CLOSE ERROR] {e}")
            await ctx.send(
                embed=LilyEmbed.simple_embed("Attempted to Close an invalid Instigator Thread", 'cross'),
                ephemeral=True
            )
    else:
        await ctx.reply(embed=LilyEmbed.simple_embed("Attempted to Close an invalid Instigator Thread", 'cross'))

async def open_thread_by_id(ctx: commands.Context, id: str):
    try:
        thread = await ctx.guild.fetch_channel(id)
        thread.add_user(ctx.author)
        await thread.send(embed=LilyEmbed.simple_embed("Thread Opened, please use `close_thread`"))
    except Exception as e:
        print(f"Exception [OpenThreadByID] {e}")
    pass