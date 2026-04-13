import discord
import LilyLogging.sLilyLogging as LilyLogging
import Config.sBotDetails as Configs

from Misc.sLilyEmbed import simple_embed
from typing import Dict, Optional, List

import Misc.sLilyEmbed as LilyEmbed
import LilyUtility.sLilyUtility as LilyUtility

import asyncio
import json

from datetime import datetime, timedelta, timezone

bot = None

class ReportComponent(discord.ui.LayoutView):
    def __init__(self, reported_member: discord.Member, field_values: Dict, mentions):
        super().__init__()
        self.last_key, self.last_value = next(reversed(field_values.items()))
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content="## Member Report"),
            discord.ui.TextDisplay(content="## Reported Member Detail"),
            discord.ui.Section(
                discord.ui.TextDisplay(content=f"**Name** \n- ```{reported_member.name}```\n**Dev ID**\n- ```{reported_member.id}```"),
                discord.ui.TextDisplay(content=f"Created On : <t:{int(reported_member.created_at.timestamp())}:F>\nJoined On : <t:{int(reported_member.joined_at.timestamp())}:F>"),
                accessory=discord.ui.Thumbnail(
                    media=reported_member.display_avatar.url,
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"### {self.last_key}\n- ```{self.last_value}```"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=mentions),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(self.container)

class TicketComponentEmbed(discord.ui.LayoutView):
    def __init__(self, opener: discord.Member | int, ticket_channel_id: int, submission_json: dict, core_json: dict):
        super().__init__(timeout=None)

        self.opener: Optional[discord.Member] = opener if isinstance(opener, discord.Member) else None

        if isinstance(opener, discord.Member):
            self.opener_id = opener.id
        elif isinstance(opener, int):
            self.opener_id = opener
        else:
            raise ValueError("Invalid Opener Type")
        

        self.ticket_channel_id: int = ticket_channel_id

        self.submission_json = submission_json
        self.core_json = core_json

        self.current_claimer: Optional[discord.Member] = None
        self.claim_expiry: Optional[datetime] = None
        self.ticket_message: Optional[discord.Message] = None


        base_name = self.submission_json.get("ticket_name_base", "ticket")
        self.ticket_name: str = base_name.replace("_", " ").title()
        field_details = self.submission_json.get("inputs", {})
        self.ticket_description: str = "\n".join(f"**{k}**: ```{v}```" for k, v in field_details.items())

        roles = submission_json.get("ping_roles", [])
        self.ticket_mentions: str = " ".join(f"<@&{role_id}>" for role_id in roles) if roles else "No Mentions!"


        self.allowed_roles = set(submission_json.get("ping_roles", []))
        self.higher_staff_role_ids = set(self.core_json.get("BasicConfigurations").get("higher_staffs_role_id"))


        # Secondary and primary embed panels

        self.claim_ticket: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.green,
            label="Claim Ticket",
            custom_id=f"claim-ticket{self.ticket_channel_id}",
        )

        self.revoke_claim: discord.ui.Button = discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Revoke Claim",
                custom_id=f"revoke-claim{self.ticket_channel_id}",
            )
        
        self.claim_ticket.callback = self.claim_ticket_callback
        self.revoke_claim.callback = self.revoke_claim_callback

        avatar_url = (
            self.opener.display_avatar.url
            if isinstance(self.opener, discord.Member)
            else f"https://media.discordapp.net/attachments/1489584483756675083/1489584654871695522/Profile.webp?ex=69d0f350&is=69cfa1d0&hm=8c63722bd588bcbf162f252966f636497d217a587db7c7291bddd3ecd9c6c718&=&format=webp"
        )

        container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content=f"## {self.ticket_name} | <@{self.opener_id}>"),
                discord.ui.TextDisplay(content=f"{self.ticket_mentions}"),
                discord.ui.TextDisplay(content=self.ticket_description),

                accessory=discord.ui.Thumbnail(
                    media=avatar_url,
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                self.claim_ticket,
                self.revoke_claim
            ),
        )

        self.add_item(container)

    async def claim_ticket_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        is_staff = any(role.id in self.allowed_roles for role in interaction.user.roles)
        is_opener = interaction.user.id == self.opener_id

        if not is_staff or is_opener:
            await interaction.followup.send(
                embed=simple_embed("You are not allowed to claim this ticket!", 'cross'),
                ephemeral=True
            )
            return
        
        if self.current_claimer:
            await interaction.followup.send(
                embed=simple_embed(f"{self.current_claimer.mention} has already claimed the ticket!", 'cross'),
                ephemeral=True
            ) 

            return
        
        channel: discord.TextChannel = interaction.channel
        await channel.set_permissions(
            interaction.user,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            use_external_emojis=True,
            read_message_history=True
        )

        self.current_claimer = interaction.user

        self.claim_ticket.disabled = True
        self.claim_ticket.label = "Claimed"
        self.claim_ticket.style = discord.ButtonStyle.secondary

        self.ticket_message = interaction.message

        await interaction.message.edit(view=self)
        await interaction.followup.send(embed=simple_embed(f"{interaction.user.mention} has claimed the ticket!"))
        self.claim_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)

        asyncio.create_task(
            self.auto_revoke_claim(
                interaction.guild,
                interaction.channel.id,
                interaction.user.id,
                self.claim_expiry
            )
        )

    async def revoke_claim_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if self.current_claimer is None:
            await interaction.followup.send(
                embed=simple_embed("No one has claimed this ticket!", 'cross'),
                ephemeral=True
            )
            return

        if not any(role.id in self.higher_staff_role_ids for role in interaction.user.roles):
            await interaction.followup.send(
                embed=simple_embed("You are not allowed to revoke ticket claims!", 'cross'),
                ephemeral=True
            )
            return

        if not self.current_claimer:
            await interaction.followup.send(
                embed=simple_embed("This ticket is not currently claimed.", 'cross'),
                ephemeral=True
            )
            return

        channel = interaction.channel
        await channel.set_permissions(self.current_claimer, overwrite=None)  

        self.current_claimer = None
        self.claim_expiry = None


        self.claim_ticket.disabled = False
        self.claim_ticket.label = "Claim"
        self.claim_ticket.style = discord.ButtonStyle.green

        if interaction.message:
            await interaction.message.edit(view=self)

        await interaction.followup.send(
            embed=simple_embed("Ticket claim has been revoked!"),
            ephemeral=True
        )

        await channel.send(
            embed=simple_embed(f"{interaction.user.mention} revoked the ticket claim.")
        )

    async def auto_revoke_claim(self,guild: discord.Guild,channel_id: int,user_id: int,expiry: datetime):
        delay = (expiry - datetime.now(timezone.utc)).total_seconds()

        if delay > 0:
            await asyncio.sleep(delay)

        if not self.current_claimer or self.current_claimer.id != user_id:
            return

        if self.claim_expiry != expiry:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        await channel.set_permissions(self.current_claimer, overwrite=None)

        self.current_claimer = None
        self.claim_expiry = None

        self.claim_ticket.disabled = False
        self.claim_ticket.label = "Claim"
        self.claim_ticket.style = discord.ButtonStyle.green

        try:
            if self.ticket_message:
                await self.ticket_message.edit(view=self)
        except:
            pass

        await channel.send(
            embed=simple_embed(f"<@{user_id}>'s claim has been revoked automatically.")
        )

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

    async def ticket_thread_constructor(self, interaction: discord.Interaction, core_json, submission_json) -> discord.TextChannel | discord.Thread:
        channel_id: int = int(submission_json.get("channel_id"))
        ticket_type: str = core_json.get("BasicConfigurations").get("TicketType")
        if ticket_type not in ('channel', 'threads', 'thread'):
            raise ValueError
        
        proof_attachments = submission_json.get("proof_images")
        proofs_flag = False
        if proof_attachments:
            proof_url = '\n'.join(proof_attachments)
            proofs_flag = True
        else:
            proof_url = "No Proofs Attached!"
            proofs_flag = False

        roles = submission_json.get("ping_roles", [])
        if roles:
            mentions = " ".join(f"<@&{role_id}>" for role_id in roles)

        higher_staff_roles_ids = core_json.get("BasicConfigurations").get("higher_staffs_role_id")

        opener = interaction.user
        logging_channel_id = core_json.get("BasicConfigurations").get("TicketLoggingHandler")
        ticket_name_base = submission_json.get("ticket_name_base")

        # Secondary and primary embed panels
        field_details = submission_json.get("inputs", {})
        content, embeds = LilyEmbed.ParseAdvancedEmbed(core_json['EmbedConfigs']['TicketChannelSpawnEmbed'])
        
        embed = discord.Embed(
            title=ticket_name_base.replace("_", " ").title(),
            description="\n".join(f"**{k}**: ```{v}```" for k, v in field_details.items()),
            color=16777215
        )
        embed.set_image(url=Configs.img['border'])
        embed.set_thumbnail(url = Configs.img['logs'])

        embeds.append(embed)
    
        if ticket_type in ('threads', 'thread'):
            thread_channel: discord.TextChannel = interaction.guild.get_channel(channel_id)
            if not thread_channel:
                thread_channel: discord.TextChannel = await interaction.guild.fetch_channel(channel_id)

            thread = await thread_channel.create_thread(
                name=f"{ticket_name_base}-{opener.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=4320,
                invitable=False
            )

            thread.jump_url

            await thread.add_user(opener)
            
            await LilyLogging.mdb.execute(
                '''INSERT INTO tickets (ticket_id, opened_user_id, submission_json, ticket_type, guild_id, log_channel_id)
                VALUES (?, ?, ?, ?, ?, ?)'''
            ,(thread.id, opener.id, json.dumps(submission_json), ticket_name_base, interaction.guild.id, logging_channel_id))

            await LilyLogging.mdb.commit()
            await thread.send(content=mentions, embeds=embeds)
            if proofs_flag:
                await thread.send(content=f"{proof_url}")
            
            return thread

        else:
            channel_category: discord.CategoryChannel = interaction.guild.get_channel(channel_id)
            overwrites = {}

            overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(
                view_channel=False
            )
            overwrites[opener] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
                use_external_emojis=True,
                read_message_history=True
            )

            # Roles without claiming the ticket cannot send messages.
            for role_id in roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False,
                        embed_links=True,
                        attach_files=True,
                        add_reactions=True,
                        use_external_emojis=True,
                        read_message_history=True,
                        create_public_threads=False,
                        create_private_threads=False
                    )
            for role_id in higher_staff_roles_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        embed_links=True,
                        attach_files=True,
                        add_reactions=True,
                        use_external_emojis=True,
                        read_message_history=True,
                        create_public_threads=False,
                        create_private_threads=False
                    )
            if isinstance(channel_category, discord.CategoryChannel):
                text_channel: discord.TextChannel = await interaction.guild.create_text_channel(
                    name=f"{ticket_name_base}-{opener.name}",
                    category=channel_category,
                    overwrites=overwrites
                )
            else:
                text_channel: discord.TextChannel = await interaction.guild.create_text_channel(
                    name=f"{ticket_name_base}-{opener.name}",
                    overwrites=overwrites
                )

            view = TicketComponentEmbed(opener=opener, ticket_channel_id=text_channel.id, submission_json=submission_json, core_json=core_json)
            ticket_message: discord.Message = await text_channel.send(view=view)
            if proofs_flag:
                await text_channel.send(content=f"{proof_url}")

            await LilyLogging.mdb.execute(
                '''INSERT INTO tickets (ticket_id, opened_user_id, submission_json, ticket_type, guild_id, log_channel_id, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)'''
            ,(text_channel.id, opener.id, json.dumps(submission_json), ticket_name_base, interaction.guild.id, logging_channel_id, ticket_message.id))

            await LilyLogging.mdb.commit()
            return text_channel

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
                embed=simple_embed(
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
        ping_roles = self.modal_data.get("ping-roles", [])
        logs_channel_id  = self.json_data["BasicConfigurations"]["TicketLoggingHandler"]

        submission = {
            "channel_id": channel_id,
            "inputs": values,
            "ticket_name_base": ticket_name_base,
            "logs_channel_id" : logs_channel_id,
            "proof_images" : self.images,
            "ping_roles" : ping_roles
        }
        thread_channel: discord.TextChannel | discord.Thread = await self.ticket_thread_constructor(
            interaction,
            self.json_data,
            submission
        )
        await interaction.followup.send(
            embed=simple_embed(
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

def TicketEmbed(ticket_opener: discord.Member, submission_data) -> discord.Embed:
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

def TicketConstructorEmbed(ticket_name_base: str, core_json: Dict, submission_json: Dict) -> List[discord.Embed]:
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

    
    return embeds