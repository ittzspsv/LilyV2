from core.database.integrations.logging import LoggingDatabase
from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.utils.embeds.sLilyEmbed import ParseAdvancedEmbed, simple_embed
from ..components.LilyTicketToolComponents import TicketSelector, TicketComponentEmbed

from discord.ext import commands

import json
import discord
import asyncio
import io
import DiscordTranscript

class LilyTicketingController:
    def __init__(self, log_db: LoggingDatabase, bot_db: BotGlobalsDatabaseAccess) -> None:
        self.log_db = log_db
        self.bot_db = bot_db

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

                    selector_view = TicketSelector(config, self.log_db)
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
                        tickets = await self.log_db.get_guild_tickets(guild_id)

                        for ticket_id, opener_user_id, submission_json, ticket_message_id in tickets:
                            view = TicketComponentEmbed(
                                opener_user_id,
                                ticket_id,
                                json.loads(submission_json),
                                config
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


            selector_view = TicketSelector(json_data, self.log_db)

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

        except discord.Forbidden:
            await ctx.reply(
                "Missing permissions to send ticket panel in the configured channel."
            )

        except discord.NotFound:
            await ctx.reply(
                "Configured ticket panel channel could not be found."
            )

        except Exception as e:
            print(f"[SPAWN TICKET ERROR] {e}")

            await ctx.reply(
                "Failed to spawn ticket panel due to an internal error."
            )

    async def c_ticket_log_action(self, ctx: commands.Context,thread: discord.Thread,opened_user_id: int,ticket_type: str,accessed_staff_ids: set, logs_channel: discord.TextChannel):
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

    async def c_ticket_log_action_channel(self, ctx: commands.Context,opened_user_id: int,ticket_type: str, logs_channel: discord.TextChannel, transcripts_file):
        embed = discord.Embed(
            title="Ticket Logs",
            description=f"### __TICKET DETAILS__\n> - Ticket Opener : <@{opened_user_id}>\n> - Ticket Closed by: {ctx.author.mention}",
            color=0xFFFFFF
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

        embed.set_footer(text=ticket_type)
        try:
            await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed, file=transcripts_file)
        except Exception as e:
            print(f"Exception [TicketLogAction] {e}")

    async def rename_ticket(self, ctx: commands.Context, name: str):
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        owner = await self.log_db.get_ticket_owner(ctx.channel.id)
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
            owner = await self.log_db.get_ticket_owner(ctx.channel.id)

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

    async def close_ticket_thread(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "This command requires guild object inorder to execute!"
                )
            )
            return

        await ctx.reply(
            embed=simple_embed(
                "Ticket close scheduling has been initiated. The channel will be deleted shortly."
            )
        )

        if not isinstance(ctx.channel, (discord.Thread, discord.TextChannel)):
            return await ctx.reply(
                embed=simple_embed(
                    "Attempted to Close an invalid Instigator Ticket",
                    "cross"
                )
            )

        channel = ctx.channel
        ticket_id: int = channel.id

        try:
            row = await self.log_db.get_ticket_by_id(ticket_id)
            if not row:
                raise RuntimeError("Ticket data not found")

            opened_user_id, ticket_type, logs_channel_id, submission_json_raw = row

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
                    )

                await channel.edit(archived=True, locked=True)

                await self.log_db.delete_ticket(ticket_id)
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

                transcript_file = discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-{channel.name}.html",
                )

                if logs_channel:
                    await self.c_ticket_log_action_channel(
                        ctx=ctx,
                        opened_user_id=opened_user_id,
                        ticket_type=ticket_type,
                        logs_channel=logs_channel,
                        transcripts_file=transcript_file
                    )

                """ Send DM'S to the ticket opener """

                try:
                    await channel.delete(reason=f"Ticket Closed by {ctx.author}")
                except discord.Forbidden:
                    return await ctx.send("Missing permissions to delete channel.")
                except discord.HTTPException as e:
                    return await ctx.send(f"Failed to delete channel: {e}")

                await self.log_db.delete_ticket(ticket_id)

        except Exception as e:
            print(f"[TICKET CLOSE ERROR] {e}")

            await ctx.send(
                embed=simple_embed(
                    "Attempted to Close an invalid Instigator Ticket",
                    "cross"
                )
            )