from core.logging.lily_logging import LilyLoggingController
from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.utils.embeds.sLilyEmbed import ParseAdvancedEmbed, simple_embed
from core.configs.sBotDetails import img
from typing import Any
from ..components.LilyTicketToolComponents import TicketSelector, TicketComponentEmbed

from discord.ext import commands

import json
import discord
import asyncio
import io
import DiscordTranscript

from ..classes.ticketing_classes import DatabaseAccess


class LilyTicketingController:
    def __init__(self, bot_db: BotGlobalsDatabaseAccess, logging_controller: LilyLoggingController) -> None:
        self.bot_db = bot_db
        self.logging_controller = logging_controller

    async def initialize_ticket_view(self, bot):
        try:
            panels = await self.bot_db.get_ticket_views()

            if not panels:
                print("[InitializeTicketView] No ticket panels found.")
                return

            for panel in panels:
                try:
                    guild_id, channel_id, message_id, config_json = panel

                    config = json.loads(config_json)

                    if not config:
                        continue

                    content, embeds = ParseAdvancedEmbed(
                        config["EmbedConfigs"]["TicketPanelEmbed"]
                    )

                    if not isinstance(embeds, list):
                        embeds = [embeds]

                    channel = bot.get_channel(channel_id)

                    if not channel:
                        try:
                            channel = await bot.fetch_channel(channel_id)
                        except (discord.NotFound, discord.Forbidden):
                            print(f"[InitializeTicketView] Missing channel {channel_id}")
                            continue

                    selector_view = TicketSelector(config, DatabaseAccess(self.bot_db, self.logging_controller))
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

                            await self.bot_db.save_ticket_view(
                                guild_id=guild_id,
                                channel_id=channel_id,
                                message_id=message.id,
                                config=config
                            )

                    except (discord.NotFound, discord.Forbidden):
                        print(f"[InitializeTicketView] Panel message missing in {channel_id}")
                        continue

                    try:
                        tickets = await self.bot_db.get_guild_tickets(guild_id)

                        for ticket_id, opener_user_id, submission_json, ticket_message_id in tickets:
                            view = TicketComponentEmbed(
                                opener_user_id,
                                ticket_id,
                                json.loads(submission_json),
                                config,
                                DatabaseAccess(self.bot_db, self.logging_controller)
                            )

                            bot.add_view(
                                view,
                                message_id=ticket_message_id
                            )

                    except Exception as e:
                        print(f"[Ticket Component Restore ERROR] {e}")

                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"[TicketPanel Restore ERROR] {e}")
                    continue

        except Exception as e:
            print(f"[InitializeTicketView ERROR] {e}")

    async def spawn_ticket(self, ctx: commands.Context, json_data: dict) -> None:
        if ctx.guild is None:
            return

        try:
            content, embeds = ParseAdvancedEmbed(
                json_data["EmbedConfigs"]["TicketPanelEmbed"]
            )

            if not isinstance(embeds, list):
                embeds = [embeds]

            channel_id = json_data["BasicConfigurations"]["TicketPanelSpawnChannel"]

            channel_obj = (
                ctx.guild.get_channel(channel_id)
                or await ctx.guild.fetch_channel(channel_id)
            )

            if not isinstance(channel_obj, discord.TextChannel):
                raise RuntimeError("Invalid ticket panel channel.")


            selector_view = TicketSelector(json_data, DatabaseAccess(self.bot_db, self.logging_controller))

            ctx.bot.add_view(selector_view)


            message_obj = await channel_obj.send(
                content=content,
                embeds=embeds,
                view=selector_view
            )

            await self.bot_db.save_ticket_view(
                guild_id=ctx.guild.id,
                channel_id=channel_obj.id,
                message_id=message_obj.id,
                config=json_data
            )


        except Exception as e:
            print(f"[SPAWN TICKET ERROR] {e}")

            await ctx.reply(
                "Failed to spawn ticket panel due to an internal error."
            )

    async def c_ticket_log_action(self, ctx: commands.Context,thread: discord.Thread,opened_user_id: int,ticket_type: str,accessed_staff_ids: set, logs_channel: discord.TextChannel, reason: str="No reason provided!"):
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

        embed.add_field(
            name="Reason",
            value=f"- {reason}",
            inline=False
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

        embed.set_footer(text=ticket_type)
        try:
            await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed)
        except Exception as e:
            print(f"Exception [TicketLogAction] {e}")

    async def c_ticket_log_action_channel(self, ctx: commands.Context,opened_user_id: int,ticket_type: str, logs_channel: discord.TextChannel, transcripts_file, reason: str="No reason provided!") -> int:
        embed = discord.Embed(
            title="Ticket Logs",
            description=f"### __TICKET DETAILS__\n> - Ticket Opener : <@{opened_user_id}>\n> - Ticket Closed by: {ctx.author.mention}\n> - Reason: {reason}",
            color=0xFFFFFF
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

        embed.set_footer(text=ticket_type)
        try:
            message: discord.Message = await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed, file=transcripts_file)
            return message.id
        except Exception as e:
            print(f"Exception [TicketLogAction] {e}")
            return 0

    async def rename_ticket(self, ctx: commands.Context, name: str):
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        owner = await self.bot_db.get_ticket_owner(ctx.channel.id)
        if owner:
            await ctx.channel.edit(name=name.replace(" ", "_"), reason=f"Ticket renamed by {ctx.author}")
            await ctx.reply(embed=simple_embed("Ticket renamed successfully!"))
        else:
            await ctx.reply(embed=simple_embed("Attempted to rename an invalid Instigator Ticket"))

    async def ticket_add_user(
        self,
        ctx: commands.Context,
        user: discord.Member
    ) -> None:

        if not isinstance(ctx.channel, discord.TextChannel):
            return

        try:
            owner = await self.bot_db.get_ticket_owner(ctx.channel.id)

            if not owner:
                await ctx.reply(
                    embed=simple_embed(
                        "Attempted to add a member to an invalid instigator ticket.",
                        "cross"
                    )
                )
                return

            await ctx.channel.set_permissions(
                user,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                add_reactions=True,
                use_external_emojis=True,
                use_application_commands=True
            )

            await ctx.reply(
                embed=simple_embed(
                    f"Successfully added {user.mention} to this ticket."
                )
            )

        except discord.Forbidden:
            await ctx.reply(
                embed=simple_embed(
                    "Missing permissions to modify channel access.",
                    "cross"
                )
            )

        except discord.HTTPException as e:
            await ctx.reply(
                embed=simple_embed(
                    f"Failed to add user: {e}",
                    "cross"
                )
            )

        except Exception as e:
            print(f"[TICKET ADD USER ERROR] {e}")

            await ctx.reply(
                embed=simple_embed(
                    "An internal error occurred while adding the user.",
                    "cross"
                )
            )

    async def close_ticket_thread(self, ctx: commands.Context, reason: str="No reason provided"):
        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "This command requires guild object inorder to execute!"
                )
            )
            return

        message = await ctx.reply(
            embed=simple_embed(
                "Ticket close scheduling has been initiated. The channel will be deleted shortly."
            )
        )

        if not isinstance(ctx.channel, (discord.Thread, discord.TextChannel)):
            return await message.edit(
                embed=simple_embed(
                    "Attempted to Close an invalid Instigator Ticket",
                    "cross"
                )
            )

        channel = ctx.channel
        ticket_id: int = channel.id

        try:
            row = await self.bot_db.get_ticket_by_id(ticket_id)
            if not row:
                raise RuntimeError("Ticket data not found")

            opened_user_id, ticket_type, logs_channel_id, submission_json_raw, claimer_user_id = row

            if claimer_user_id is None:
                await message.edit(
                    embed=simple_embed(
                        f"No one has claimed this ticket! PLease claim this ticket before closing",
                        "cross"
                    )
                )

                return

            if claimer_user_id != ctx.author.id:
                await message.edit(
                    embed=simple_embed(
                        f"You cannot close this ticket.  Only <@{claimer_user_id}> can close it.  Please revoke the ticket claim if you are permitted!",
                        "cross"
                    )
                )

                return

            logs_channel = ctx.guild.get_channel(logs_channel_id)

            if not isinstance(logs_channel, discord.TextChannel):
                try:
                    fetched_channel = await ctx.guild.fetch_channel(logs_channel_id)

                    if isinstance(fetched_channel, discord.TextChannel):
                        logs_channel = fetched_channel
                    else:
                        logs_channel = None

                except discord.NotFound:
                    logs_channel = None
                except discord.Forbidden:
                    logs_channel = None

            if isinstance(channel, discord.Thread):
                if logs_channel:
                    await self.c_ticket_log_action(
                        ctx=ctx,
                        thread=channel,
                        opened_user_id=opened_user_id,
                        ticket_type=ticket_type,
                        accessed_staff_ids=set(),
                        logs_channel=logs_channel,
                        reason=reason
                    )

                await channel.edit(archived=True, locked=True)

                await self.bot_db.delete_ticket(ticket_id)
                return

            elif isinstance(channel, discord.TextChannel):
                transcript = await DiscordTranscript.export(
                    channel,
                    limit=None,
                    tz_info="America/New_York",
                    military_time=True,
                    bot=ctx.bot,
                )

                if transcript is None:
                    return await ctx.send("Failed to generate transcript.")

                transcript_bytes = transcript.encode()


                transcript_file = discord.File(
                    io.BytesIO(transcript_bytes),
                    filename=f"transcript-{channel.name}.html",
                )

                proofs_reference: int = 0

                if logs_channel:
                    proofs_reference = await self.c_ticket_log_action_channel(
                        ctx=ctx,
                        opened_user_id=opened_user_id,
                        ticket_type=ticket_type,
                        logs_channel=logs_channel,
                        transcripts_file=transcript_file,
                        reason=reason
                    )

                """ Log the ticket """
                await self.bot_db.create_ticket_log(
                    ctx.guild.id,
                    opened_user_id,
                    ctx.author.id,
                    reason,
                    ticket_type,
                    proofs_reference
                )

                """ Send DM'S to the ticket opener """
                try:
                    user: discord.Member | None = ctx.guild.get_member(opened_user_id)
                    if user is None:
                        user = await ctx.guild.fetch_member(opened_user_id)
                    
                    if user is not None:
                        embed = discord.Embed(
                            color=16777215,
                            title=f"Ticket Closed",
                            description=f"- Your support ticket was handled by {ctx.author.mention} and closed with reason {reason}\n- An copy of the transcript is attached for future reference.",
                        )

                        if ctx.guild.icon is not None:
                            embed.set_thumbnail(url=ctx.guild.icon.url)
                        
                        embed.add_field(
                            name="Server",
                            value=f"{ctx.guild.name}",
                            inline=False,
                        )

                        await user.send(
                            embed=embed, 
                            file=discord.File(
                                io.BytesIO(transcript_bytes),
                                filename=f"transcript-{channel.name}.html",
                            )
                        )

                except:
                    """ Silently ignore the DM """
                    pass


                try:
                    await channel.delete(reason=f"Ticket Closed by {ctx.author}")
                except discord.Forbidden:
                    return await ctx.send("Missing permissions to delete channel.")
                except discord.HTTPException as e:
                    return await ctx.send(f"Failed to delete channel: {e}")

                await self.bot_db.delete_ticket(ticket_id)

        except Exception as e:
            print(f"[TICKET CLOSE ERROR] {e}")

            await message.edit(
                embed=simple_embed(
                    "Attempted to Close an invalid Instigator Ticket",
                    "cross"
                )
            )

    async def ticket_stats(self, ctx: commands.Context, member: discord.Member):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("Please run this command inside an guild"))
        results = await self.bot_db.ticket_stats(ctx.guild.id, member.id)
        if not results:
            return await ctx.reply(embed=simple_embed("No ticket stats found!", 'cross'))

        embed = discord.Embed(
            color=16777215,
            title=f"{member.global_name}'s Ticket Statistics",
            description=f"### Total Tickets Handled : {sum(list(results.values()))}",
        )
        for key, values in results.items():
            embed.add_field(name=key.replace("_", " ").title(), value=values)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=img['border'])

        await ctx.reply(embed=embed)
        
    async def ticket_retrieve(self, ctx: commands.Context, id: int):
        if ctx.guild is None:
            return

        result = await self.bot_db.get_ticket_log(id, ctx.guild.id)

        if result is None:
            await ctx.reply(
                embed=simple_embed(
                    "No ticket logs found!", 'cross'
                )
            )

            return
        
        transcripts_reference = result["transcripts_reference"]
        transcripts_channel_id = self.bot_db.get_channel(ctx.guild.id, "ticket_transcripts")

        if transcripts_channel_id is None:
            await ctx.reply(
                embed=simple_embed(
                    "Ticket transcripts channel cannot be found", 'cross'
                )
            )
            return

        transcripts_channel = ctx.guild.get_channel(transcripts_channel_id)
        if not transcripts_channel:
            transcripts_channel = await ctx.guild.fetch_channel(transcripts_channel_id)

        if transcripts_channel and isinstance(transcripts_channel, discord.TextChannel):
            transcript_message: discord.Message | None = None

            try:
                transcript_message = await transcripts_channel.fetch_message(transcripts_reference)
            except Exception:
                await ctx.reply(
                    embed=simple_embed(
                        "Failed to fetch transcript message", 'cross'
                    )
            )
                
            if transcript_message is None:
                return

            """ TODO, fetch all attachments from transcript_message to prepare an file """
            files: list[discord.File] = []
            for attachment in transcript_message.attachments:
                data = await attachment.read()

                files.append(
                    discord.File(
                        io.BytesIO(data),
                        filename=attachment.filename,
                        spoiler=attachment.is_spoiler(),
                    )
                )
        
            """ Building embed """
            embed = discord.Embed(
                title=f"Ticket Log #{id}",
            )
            embed.set_thumbnail(url=img["logs"])
            embed.set_image(url=img["border"])
            embed.add_field(
                name="Opened by",
                value=f"<@{result["opened_user_id"]}>",
                inline=False,
            )
            embed.add_field(
                name="Staff Handled",
                value=f"<@{result["staff_handled"]}>",
                inline=False,
            )
            embed.add_field(
                name="Reason",
                value=result["reason"],
                inline=False,
            )
            embed.add_field(
                name="Closed At",
                value=result["timestamp"],
                inline=False,
            )
            embed.add_field(
                name="Ticket Type",
                value=result["ticket_type"],
                inline=False,
            )

            await ctx.reply(embed=embed, files=files)

        else:
            await ctx.reply(
                embed=simple_embed(
                    "Failed to fetch transcript channel", 'cross'
                )
            )
        

        
