import discord
import LilyLogging.sLilyLogging as LilyLogging
from discord.ext import commands
from pathlib import Path
import json
import Config.sBotDetails as Configs
import os
import Misc.sLilyEmbed as LilyEmbed
import LilyModeration.sLilyModeration as mLily
import asyncio

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

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except (json.JSONDecodeError, OSError):
        return {}

class TicketModal(discord.ui.Modal):
    def __init__(self, title: str, modal_data: dict, json_data):
        super().__init__(title=title)

        self.images = None

        if not isinstance(modal_data, dict):
            raise TypeError(f"modal_data must be a dict, got {type(modal_data)}")

        fields = modal_data.get("fields")
        file_upload_bool = modal_data.get("file_upload", False)
        if not isinstance(fields, dict):
            raise TypeError(f"fields must be a dict, got {type(fields)}")

        self.inputs = {}
        self.modal_data = modal_data
        self.json_data = json_data
        self.images = None

        for label, max_length in fields.items():
            style = discord.TextStyle.paragraph if max_length > 100 else discord.TextStyle.short

            text_input = discord.ui.TextInput(
                label=label[:45],
                placeholder=f"Max {max_length} characters",
                max_length=max_length,
                required=True,
                style=style
            )

            self.inputs[label] = text_input
            self.add_item(text_input)

        if file_upload_bool:
            self.images = discord.ui.Label(
                text='Images',
                description='Please provide a valid proof.',
                component=discord.ui.FileUpload(
                    max_values=10,
                    custom_id='report_images',
                    required=False,
                ),
            )

            self.add_item(self.images)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.images:
            self.images = [attachment.url for attachment in self.images.component.values]
        else:
            self.images = []

        cursor = await LilyLogging.mdb.execute(
            """
            SELECT ticket_id
            FROM tickets
            WHERE opened_user_id = ?
            AND guild_id = ?
            """,
            (interaction.user.id, interaction.guild.id)
        )

        rows = await cursor.fetchall()

        if len(rows) >= 3:
            references = ", ".join(f"<#{r[0]}>" for r in rows)
            await interaction.followup.send(
                embed=mLily.SimpleEmbed(
                    "Your ticket cannot be created.\n"
                    "Please close your previous tickets first.\n"
                    f"**References:** {references}"
                ),
                ephemeral=True
            )
            return

        values = {label: input.value for label, input in self.inputs.items()}
        channel_id = self.modal_data.get("channel_id")
        ticket_name_base = self.modal_data.get("ticket_base_name", "ticket")
        ticket_panel_spawn_id = self.modal_data.get("view_pannel_spawn_id", 0)
        logs_channel_id  = self.json_data["BasicConfigurations"]["TicketLoggingHandler"]

        submission = {
            "channel_id": channel_id,
            "ticket_panel_thread_id" : ticket_panel_spawn_id,
            "inputs": values,
            "ticket_name_base": ticket_name_base,
            "logs_channel_id" : logs_channel_id,
            "proof_images" : self.images
        }
        thread_channel = await TicketThreadConstructor(
            interaction,
            self.json_data,
            submission
        )
        await interaction.followup.send(
            embed=mLily.SimpleEmbed(
                f"Your ticket has been created: {thread_channel.mention}"
            ),
            ephemeral=True
        )

class TicketSelector(discord.ui.View):
    def __init__(self, json_data: dict):
        super().__init__(timeout=None)

        self.ticket_options = json_data.get("TicketType", [])[1:]
        self.modal_fields = json_data.get("Modal", [])
        self.labels = []
        self.json_data = json_data

        select_options = []
        for i, opt in enumerate(self.ticket_options):
            parts = opt.split(":", 1)
            label = parts[0].strip()
            emoji = parts[1].strip() if len(parts) > 1 else None
            self.labels.append(label)

            select_options.append(
                discord.SelectOption(label=label, value=str(i), emoji=emoji) if emoji else
                discord.SelectOption(label=label, value=str(i))
            )
        self.add_item(self.ModalSelect(select_options, self.modal_fields, self.labels, self.json_data))

    class ModalSelect(discord.ui.Select):
        def __init__(self, options, modal_fields, labels, json_data):
            super().__init__(placeholder="Choose a ticket type...", options=options, custom_id=f'ticket_selector_main')
            self.modal_fields = modal_fields
            self.labels = labels
            self.json_data = json_data

        async def callback(self, interaction: discord.Interaction):
            index = int(self.values[0])
            label = self.labels[index]

            if index < len(self.modal_fields):
                modal_entry = self.modal_fields[index]
            else:
                modal_entry = {"fields": {"Details": 300}}

            modal = TicketModal(title=label, modal_data=modal_entry, json_data=self.json_data)
            await interaction.response.send_modal(modal)

async def TicketEmbed(ticket_opener: discord.Member, submission_data):
    ticket_name = submission_data.get("ticket_name_base", "General Ticket").replace("_", " ").title()
    ticket_values = submission_data.get("inputs", {})
    embed = discord.Embed(
        color=16777215,
        title=f"<:arrow:1438045578721493062> {ticket_name} Ticket",
        description=f"<:member:1438045591098753104> Ticket Opened By {ticket_opener.mention}",
    )
    embed.set_author(
        name=ticket_opener.name,
        icon_url=ticket_opener.display_avatar.url,
    )
    embed.set_thumbnail(url=ticket_opener.avatar.url)
    embed.set_image(url=Configs.img['border'])
    embed.set_footer(
        text="Lily Ticketing",
    )

    for k, v in ticket_values.items():
        embed.add_field(
            name=k,
            value=f" >  - ```{v}```",
            inline=False,
        )
    return embed

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

            except Exception as panel_error:
                print(f"[TicketPanel Restore ERROR] {panel_error}")

        if updated:
            with open(
                "src/LilyTicketTool/LilyTicketSelector.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(json_data, f, indent=4)

    except Exception as e:
        print(f"[InitializeTicketView ERROR] {e}")

class TicketPanelView(discord.ui.View):
    def __init__(self, thread_object: discord.Thread, logs_channel_id):
        super().__init__(timeout=None)
        self.thread = thread_object
        self.thread_id = thread_object.id
        self.logs_channel_id = logs_channel_id

        view_btn = discord.ui.Button(
            label="View Ticket",
            style=discord.ButtonStyle.primary,
            custom_id=f"ticket_view:{self.thread_id}"
        )
        view_btn.callback = self.view_ticket
        self.add_item(view_btn)

        close_btn = discord.ui.Button(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            custom_id=f"ticket_close:{self.thread_id}"
        )
        close_btn.callback = self.close_ticket
        self.add_item(close_btn)

    async def view_ticket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.thread.add_user(interaction.user)
            await LilyLogging.mdb.execute(
                """
                INSERT OR IGNORE INTO ticket_handlers (accessed_staff, ticket_id)
                VALUES (?, ?)
                """,
                (interaction.user.id, self.thread.id)
            )
            await LilyLogging.mdb.commit()

            await interaction.followup.send(
                embed=mLily.SimpleEmbed(
                    f"Successfully added. Please visit {self.thread.mention}"
                ),
                ephemeral=True
            )

        except Exception as e:
            print(f"[TICKET VIEW ERROR] {e}")
            await interaction.followup.send(
                embed=mLily.SimpleEmbed("An unknown error occurred.", "cross"),
                ephemeral=True
            )

    async def close_ticket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            cursor = await LilyLogging.mdb.execute(
                """
                SELECT
                    t.opened_user_id,
                    t.ticket_type,
                    tae.tickets_access_panel_id,
                    tae.access_panel_message_id,    
                    th.accessed_staff
                FROM tickets AS t
                LEFT JOIN ticket_access_panels AS tae
                    ON tae.access_id = t.tickets_access_panel_id
                LEFT JOIN ticket_handlers AS th
                    ON th.ticket_id = t.ticket_id
                WHERE t.ticket_id = ?;
                """,
                (self.thread.id,)
            )

            rows = await cursor.fetchall()
            if not rows:
                raise RuntimeError("Ticket data not found")

            opened_user_id = rows[0][0]
            ticket_type = rows[0][1]            
            panel_channel_id = rows[0][2]
            panel_message_id = rows[0][3]

            accessed_staff_ids = {row[4] for row in rows if row[4] is not None}

            opener = interaction.guild.get_member(opened_user_id)
            if not opener:
                try:
                    opener = await interaction.guild.fetch_member(opened_user_id)
                except:
                    opener = None
            if opener:
                await self.thread.remove_user(opener)

            accessed_staff_ids.discard(opened_user_id)
            accessed_staff_ids.discard(interaction.user.id)
            for staff_id in accessed_staff_ids:
                member = interaction.guild.get_member(staff_id)
                if not member:
                    try:
                        member = await interaction.guild.fetch_member(staff_id)
                    except:
                        continue
                try:
                   await self.thread.remove_user(member) 
                except:
                    continue

            await self.thread.remove_user(interaction.user)

            await interaction.followup.send(
                embed=mLily.SimpleEmbed("Ticket closed successfully."),
                ephemeral=True
            )

            if panel_channel_id and panel_message_id:
                channel = interaction.guild.get_channel(panel_channel_id)
                if not channel:
                    try:
                        channel = await interaction.guild.fetch_channel(panel_channel_id)
                    except discord.NotFound:
                        channel = None

                if channel:
                    try:
                        msg = await channel.fetch_message(panel_message_id)
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass

            await self.thread.edit(archived=True, locked=True)
            logs_channel = interaction.guild.get_channel(self.logs_channel_id)
            if not logs_channel:
                logs_channel = await interaction.guild.fetch_channel(self.logs_channel_id)
            await TicketLogAction(
                interaction=interaction,
                thread=self.thread,
                opened_user_id=opened_user_id,
                ticket_type=ticket_type,
                accessed_staff_ids=accessed_staff_ids,
                logs_channel=logs_channel
            )

            await self.cleanup_ticket_data(panel_message_id)

        except Exception as e:
            print(f"[TICKET CLOSE ERROR] {e}")
            await interaction.followup.send(
                embed=mLily.SimpleEmbed("An unknown error occurred.", "cross"),
                ephemeral=True
            )

    async def cleanup_ticket_data(self, message_id):
        ticket_id = self.thread.id
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

async def SpawnTicket(ctx: commands.Context, json_data):
    try:
        content, embeds = LilyEmbed.ParseAdvancedEmbed(json_data["EmbedConfigs"]["TicketPanelEmbed"])
        channel_id = json_data["BasicConfigurations"]["TicketPanelSpawnChannel"]

        channel_obj = ctx.guild.get_channel(channel_id) or await ctx.guild.fetch_channel(channel_id)
        selector_view = TicketSelector(json_data)

        message_obj = await channel_obj.send(embeds=embeds, view=selector_view)
        save_ticket_view(channel_obj.id, message_obj.id, json_data, ctx.guild.id)
    except Exception as e:
        print(e)

async def SendTicketPanel(interaction: discord.Interaction, submission_json, thread_object, logs_channel):
    thread_channel = submission_json.get("ticket_panel_thread_id", 0)

    thread_channel_obj = interaction.guild.get_channel(thread_channel)
    if not thread_channel_obj:
        try:
            thread_channel_obj = await interaction.guild.fetch_channel(thread_channel)
        except discord.NotFound:
            return

    embed = await TicketEmbed(interaction.user, submission_json)
    view = TicketPanelView(thread_object, logs_channel)
    try:
        message = await thread_channel_obj.send(embed=embed, view=view)
        cursor = await LilyLogging.mdb.execute(
            """
            INSERT INTO ticket_access_panels (tickets_access_panel_id, access_panel_message_id)
            VALUES (?, ?)
            """,
            (thread_channel, message.id)
        )
        await LilyLogging.mdb.commit()

        panel_access_id = cursor.lastrowid

    except Exception as e:
        print(f"Exception [SendTicketPanel - panel insert] {e}")
        return
    try:
        await LilyLogging.mdb.execute(
            """
            INSERT INTO tickets (ticket_id, opened_user_id, tickets_access_panel_id, ticket_values, ticket_type, guild_id, log_channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_object.id,
                interaction.user.id,
                panel_access_id,
                str(submission_json.get("inputs")),
                submission_json.get("ticket_name_base", "default"),
                interaction.guild.id,
                logs_channel
            )
        )
        await LilyLogging.mdb.commit()

    except Exception as e:
        print(f"Exception [SendTicketPanel - ticket insert] {e}")

async def TicketThreadConstructor(interaction: discord.Interaction, core_json, submission_json):
    channel_id = int(submission_json.get("channel_id"))
    thread_channel: discord.TextChannel = interaction.guild.get_channel(channel_id)
    if not thread_channel:
        thread_channel = await interaction.guild.fetch_channel(channel_id)

    proof_attachments = submission_json.get("proof_images")
    if proof_attachments:
        proof_url = '\n'.join(proof_attachments)
    else:
        proof_url = "No Proofs Attached!"

    opener = interaction.user

    support_staff_ids = core_json["RoleInformation"]["SupportStaffRole"]
    if isinstance(support_staff_ids, int):
        support_staff_ids = [support_staff_ids]

    ticket_name_base = submission_json.get("ticket_name_base")
    thread = await thread_channel.create_thread(
        name=f"{ticket_name_base}-{opener.name}",
        type=discord.ChannelType.private_thread,
        auto_archive_duration=4320,
        invitable=False
    )

    thread.jump_url

    await thread.add_user(opener)

    content, embeds = LilyEmbed.ParseAdvancedEmbed(core_json['EmbedConfigs']['TicketChannelSpawnEmbed'])
    field_details = submission_json.get("inputs", {})
    embed = discord.Embed(
        title=ticket_name_base.replace("_", " "),
        description="\n".join(f"**{k}**: ```{v}```" for k, v in field_details.items()),
        color=16777215
    )
    embed.set_image(url=Configs.img['border'])
    embed.set_thumbnail(url = Configs.img['logs'])

    embeds.append(embed)

    
    await thread.send(embeds=embeds)
    await thread.send(content=f"{proof_url}")

    await SendTicketPanel(interaction, submission_json, thread, submission_json.get("logs_channel_id"))

    return thread

async def TicketLogAction(interaction: discord.Interaction,thread: discord.Thread,opened_user_id: int,ticket_type: str,accessed_staff_ids: set, logs_channel: discord.TextChannel):
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

    if accessed_staff_ids:
        accessed_str = "\n".join(f"> - <@{uid}>" for uid in accessed_staff_ids)
    else:
        accessed_str = "> - None"
    embed.add_field(
        name="Staff Accessed Ticket.",
        value=accessed_str,
        inline=False
    )

    embed.add_field(
        name="Staff Closed Ticket",
        value=f"> - <@{interaction.user.id}>",
        inline=False
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

    embed.set_footer(text=ticket_type)
    try:
        await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed)
    except Exception as e:
        print(f"Exception [TicketLogAction] {e}")

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

    if accessed_staff_ids:
        accessed_str = "\n".join(f"> - <@{uid}>" for uid in accessed_staff_ids)
    else:
        accessed_str = "> - None"
    embed.add_field(
        name="Staff Accessed Ticket.",
        value=accessed_str,
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
                embed=mLily.SimpleEmbed("Ticket closed successfully."),
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
                await ctx.reply(embed=mLily.SimpleEmbed("Attempted to Close an invalid Instigator Thread", 'cross')),
                ephemeral=True
            )
    else:
        await ctx.reply(embed=mLily.SimpleEmbed("Attempted to Close an invalid Instigator Thread", 'cross'))

async def OpenThreadByID(ctx: commands.Context, id: str):
    try:
        thread = await ctx.guild.fetch_channel(id)
        thread.add_user(ctx.author)
        await thread.send(embed=mLily.SimpleEmbed("Thread Opened, please use `close_thread`"))
    except Exception as e:
        print(f"Exception [OpenThreadByID] {e}")
    pass