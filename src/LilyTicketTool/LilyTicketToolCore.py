import discord
import json
from pathlib import Path
from discord.ext import tasks, commands
from datetime import datetime, timedelta, timezone
import Misc.sLilyEmbed as LilyEmbed
import asyncio
import json
import Config.sBotDetails as Configs

TICKET_VIEWS_PATH = Path("storage/view/TicketViews.json")
TICKET_CHANNEL_LOG_PATH = Path("storage/view/TicketChannelViews.json")
CLAIM_TIMEOUT = timedelta(minutes=30)

claimed_tickets = {}

def save_ticket_view(channel_id: int, message_id: int, config: dict):
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
        "config": config
    })

    with open(TICKET_VIEWS_PATH, "w") as f:
        json.dump(all_data, f, indent=4)

def save_ticket_channel(channel_id: int, config: dict):
    all_data = []
    if TICKET_CHANNEL_LOG_PATH.exists():
        with open(TICKET_CHANNEL_LOG_PATH, "r") as f:
            try:
                content = f.read().strip()
                if content:
                    all_data = json.loads(content)
            except json.JSONDecodeError:
                all_data = []

    all_data.append({
        "channel_id": channel_id,
        "config": config
    })

    with open(TICKET_CHANNEL_LOG_PATH, "w") as f:
        json.dump(all_data, f, indent=4)

async def InitializeView(bot: commands.Bot):
    if TICKET_VIEWS_PATH.exists():
        try:
            with open(TICKET_VIEWS_PATH, "r") as f:
                content = f.read().strip()
                views = json.loads(content) if content else []
        except json.JSONDecodeError:
            views = []

        for entry in views:
            channel = bot.get_channel(entry["channel_id"])
            if not channel:
                continue

            try:
                await channel.fetch_message(entry["message_id"])
            except:
                continue

            config = entry["config"]
            if config.get("view_type") == "ButtonType":
                view = ButtonType(
                    name=config['Configs']['TicketType'][1],
                    type_=config['Configs']['TicketType'][2],
                    moderator_roles=config['Configs'].get('ModeratorRoles', []),
                    staff_manager_roles=config['Configs'].get('StaffManagerRoles', []),
                    modal_details=config['Modal'][0],
                    field_details=config['Configs']['TicketEmbedFields']
                )
            elif config.get("view_type") == "SelectorType":
                view = SelectorType(
                    options=config['Configs']['TicketType'][1:],
                    modal_sets=config['Modal'],
                    field_details=config['Configs']['TicketEmbedFields'],
                    moderator_roles=config['Configs'].get('ModeratorRoles', []),
                    staff_manager_roles=config['Configs'].get('StaffManagerRoles', []),
                )
            else:
                continue

            try:
                bot.add_view(view)
            except Exception:
                continue

    if TICKET_CHANNEL_LOG_PATH.exists():
        try:
            with open(TICKET_CHANNEL_LOG_PATH, "r") as f:
                content = f.read().strip()
                channels = json.loads(content) if content else []
        except json.JSONDecodeError:
            channels = []

        for entry in channels:
            channel = bot.get_channel(entry["channel_id"])
            if not channel:
                continue

            config = entry["config"]
            moderator_roles = config.get("moderator_roles", [])
            staff_manager_roles = config.get("staff_manager_roles", [])

            class BasicTicketer(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="Claim", style=discord.ButtonStyle.secondary, custom_id="claim")
                async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    user = interaction.user
                    channel = interaction.channel

                    if not any(role.id in moderator_roles for role in user.roles):
                        await interaction.response.send_message("You are not allowed to claim the ticket", ephemeral=True)
                        return

                    await channel.set_permissions(user, overwrite=discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True
                    ))

                    if channel.id in claimed_tickets and claimed_tickets[channel.id]["task"]:
                        claimed_tickets[channel.id]["task"].cancel()

                    async def claim_timer():
                        try:
                            while True:
                                await asyncio.sleep(CLAIM_TIMEOUT.total_seconds())
                                last_msg = claimed_tickets.get(channel.id, {}).get("last_message", datetime.now(timezone.utc))
                                if datetime.now(timezone.utc) - last_msg >= CLAIM_TIMEOUT:
                                    await channel.set_permissions(user, overwrite=None)
                                    await channel.send(f"Claim by {user.mention} has been reset due to inactivity.")
                                    claimed_tickets.pop(channel.id, None)
                                    break
                        except asyncio.CancelledError:
                            return

                    task = asyncio.create_task(claim_timer())
                    claimed_tickets[channel.id] = {
                        "staff_id": user.id,
                        "last_message": datetime.now(timezone.utc),
                        "task": task
                    }

                    await interaction.response.send_message(f"✅ {user.mention} has claimed this ticket!", ephemeral=False)

                @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close")
                async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    user = interaction.user
                    if not any(role.id in moderator_roles for role in user.roles):
                        await interaction.response.send_message("You are not allowed to close the ticket", ephemeral=True)
                        return

                    await interaction.response.send_message(f"Ticket has been closed by {user.mention}", ephemeral=False)
                    if channel.id in claimed_tickets:
                        task = claimed_tickets[channel.id].get("task")
                        if task:
                            task.cancel()
                        claimed_tickets.pop(channel.id, None)
                    await channel.delete()

            try:
                bot.add_view(BasicTicketer())
            except Exception:
                continue

class BaseModal(discord.ui.Modal):
    def __init__(self, title: str, fields: list[dict], moderator_roles: list, staff_manager_roles:list,field_details: dict, on_submit_callback=None):
        super().__init__(title=title)
        self.on_submit_callback = on_submit_callback
        self.inputs = {}
        self.moderator_roles = moderator_roles
        self.staff_manager_roles = staff_manager_roles
        self.field_details = field_details

        for field_dict in fields:
            for label, max_length in field_dict.items():
                parts = label.split(":", 1)

                if len(parts) > 1:
                    emoji_part = parts[1].strip()
                    clean_label = parts[0].strip()
                    
                    if emoji_part:
                        final_label = f"{emoji_part} {clean_label}"
                    else:
                        final_label = clean_label
                else:
                    final_label = label.strip()

                safe_label = final_label[:45]

                style = discord.TextStyle.paragraph if max_length > 100 else discord.TextStyle.short

                input_field = discord.ui.TextInput(
                    label=safe_label,
                    placeholder=f"Max {max_length} characters",
                    required=True,
                    max_length=max_length,
                    style=style,
                    custom_id=safe_label[:100]
                )

                self.inputs[safe_label] = input_field
                self.add_item(input_field)

    async def on_submit(self, interaction: discord.Interaction):
        values = {
            input_field.label: input_field.value
            for input_field in self.inputs.values()
        }

        if self.on_submit_callback:
            await self.on_submit_callback(interaction, values)
        else:
            await TicketConstructor(values, self.moderator_roles, self.staff_manager_roles,interaction, self.field_details)

async def SendTicketLog(guild: discord.Guild,config: dict,*,opener=None,claimer=None,closer=None,modal_data: dict = None):
    log_channel_id = config.get("LogChannel") or config.get("log_channel")
    if not log_channel_id:
        return

    log_channel = guild.get_channel(log_channel_id)
    if not log_channel:
        return

    embed = (
        discord.Embed(
            color=0xFFFFFF, 
            title=f"{Configs.emoji['ticket']}Ticket Logs",
        )
        .set_image(
            url=Configs.img['border']
        )
    )

    if opener:
        embed.add_field(
            name=f"{Configs.emoji['member']} Opened By",
            value=f"{opener.mention} ({opener.id})",
            inline=False,
        )

    if claimer:
        embed.add_field(
            name=f"{Configs.emoji['staff']} Claimed By",
            value=f"{claimer.mention} ({claimer.id})",
            inline=False,
        )

    if closer:
        embed.add_field(
            name=f"{Configs.emoji['dnd']} Closed By",
            value=f"{closer.mention} ({closer.id})",
            inline=False,
        )

    if modal_data:
        description = "\n".join(f"**{k}**: `{v}`" for k, v in modal_data.items())
        embed.add_field(
            name=f"{Configs.emoji['bookmark']} Form Responses",
            value=description or "None",
            inline=False,
        )

    embed.set_footer(text="Lily Ticket Handler")
    embed.timestamp = discord.utils.utcnow()

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass

async def TicketConstructor(values: dict, moderator_roles: list, staff_manager_roles:list,interaction: discord.Interaction, field_details: dict):
    guild = interaction.guild
    user = interaction.user
    opened_user = interaction.user

    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    for role_id in moderator_roles:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
    for role_id in staff_manager_roles:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    category = interaction.channel.category
    channel_name = f"ticket-{user.name}".lower().replace(" ", "-")

    private_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
        reason=f"Ticket created by {user.name}"
    )

    embed = discord.Embed(
        title=field_details['Title'],
        description="\n".join(f"**{k}**: ```{v}```" for k, v in values.items()),
        color=16777215
    )

    embed.set_image(url=Configs.img['border'])
    embed.set_thumbnail(url = Configs.img['logs'])

    content, embeds = LilyEmbed.ParseAdvancedEmbed(field_details['TEmbed'])
    embeds.append(embed)

    log_data = {
        "moderator_roles": moderator_roles,
        "log_channel": field_details.get("LogChannel")
    }

    class BasicTicketer(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.claimer = None

        @discord.ui.button(label="Claim", style=discord.ButtonStyle.secondary, custom_id="claim")
        async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user = interaction.user

            if not any(role.id in moderator_roles for role in user.roles):
                await interaction.response.send_message("You are not allowed to claim the ticket", ephemeral=True)
                return

            if private_channel.id in claimed_tickets:
                current = claimed_tickets[private_channel.id]
                claimed_user_id = current["staff_id"]
                if claimed_user_id != user.id:
                    await interaction.response.send_message(f"This ticket is already claimed by <@{claimed_user_id}>", ephemeral=True)
                    return

            await private_channel.set_permissions(user, send_messages=True, view_channel=True)
            self.claimer = user

            if private_channel.id in claimed_tickets and claimed_tickets[private_channel.id].get("task"):
                claimed_tickets[private_channel.id]["task"].cancel()

            async def claim_timer():
                try:
                    while True:
                        await asyncio.sleep(CLAIM_TIMEOUT.total_seconds())
                        last_msg = claimed_tickets.get(private_channel.id, {}).get("last_message", datetime.now(timezone.utc))
                        if datetime.now(timezone.utc) - last_msg >= CLAIM_TIMEOUT:
                            await private_channel.set_permissions(user, overwrite=None)
                            await private_channel.send(f"Claim by {user.mention} has been reset due to inactivity.")
                            claimed_tickets.pop(private_channel.id, None)
                            self.claimer = None
                            break
                except asyncio.CancelledError:
                    return

            task = asyncio.create_task(claim_timer())
            claimed_tickets[private_channel.id] = {"staff_id": user.id, "last_message": datetime.now(timezone.utc), "task": task}

            await interaction.response.send_message(f"{user.mention} has claimed this ticket!", ephemeral=False)

        @discord.ui.button(label="Revoke Claim", style=discord.ButtonStyle.danger, custom_id="revoke_claim")
        async def revoke_claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user = interaction.user

            if not any(role.id in staff_manager_roles for role in user.roles):
                await interaction.response.send_message("You are not allowed to revoke claims.", ephemeral=True)
                return

            if private_channel.id not in claimed_tickets:
                await interaction.response.send_message("No one has claimed this ticket yet.", ephemeral=True)
                return

            claimer_id = claimed_tickets[private_channel.id]["staff_id"]
            claimer = guild.get_member(claimer_id)

            if claimer:
                await private_channel.set_permissions(claimer, overwrite=None)

            if claimed_tickets[private_channel.id].get("task"):
                claimed_tickets[private_channel.id]["task"].cancel()

            claimed_tickets.pop(private_channel.id, None)
            self.claimer = None

            await private_channel.send(f"The claim has been revoked by {user.mention}. This ticket is now unclaimed.")
            await interaction.response.send_message("Claim successfully revoked.", ephemeral=True)

        @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close")
        async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user = interaction.user

            is_claimer = self.claimer and user.id == self.claimer.id
            is_staff_manager = any(role.id in staff_manager_roles for role in user.roles)

            if not (is_claimer or is_staff_manager):
                await interaction.response.send_message("You are not allowed to close this ticket", ephemeral=True)
                return

            await interaction.response.send_message(f"Ticket has been closed by {user.mention}", ephemeral=False)
            await SendTicketLog(
                guild,
                log_data,
                opener=opened_user,
                claimer=self.claimer,
                closer=user,
                modal_data=values
            )

            if private_channel.id in claimed_tickets and claimed_tickets[private_channel.id].get("task"):
                claimed_tickets[private_channel.id]["task"].cancel()
                claimed_tickets.pop(private_channel.id, None)

            await interaction.channel.delete()

    view = BasicTicketer()
    await private_channel.send(content=f"{user.mention} your ticket has been created.", embeds=embeds, view=view)
    await interaction.followup.send(f"Your ticket has been created: {private_channel.mention}", ephemeral=True)

    save_ticket_channel(private_channel.id, log_data)
    await SendTicketLog(guild, log_data, opener=user, modal_data=values)

class ButtonType(discord.ui.View):
    def __init__(self, name: str, type_: str, moderator_roles: list, staff_manager_roles: list, modal_details: dict, field_details: dict, *, timeout=None):
        super().__init__(timeout=None)
        self.name = name
        self.type_ = type_
        self.moderator_roles = moderator_roles
        self.staff_manager_roles = staff_manager_roles
        self.modal_details = modal_details
        self.field_details = field_details

        style: discord.ButtonStyle = discord.ButtonStyle.secondary
        if self.type_ == 'Primary':
            style = discord.ButtonStyle.primary
        elif self.type_ == 'Success':
            style = discord.ButtonStyle.success
        elif self.type_ == 'Danger':
            style = discord.ButtonStyle.danger

        self.add_item(self.TicketButton(self.name, style))

    class TicketButton(discord.ui.Button):
        def __init__(self, label, style):
            super().__init__(label=label, style=style, custom_id=f"ticket_button_{label}")

        async def callback(self, interaction: discord.Interaction):
            view: ButtonType = self.view
            fields = view.modal_details
            if isinstance(fields, dict):
                fields = [fields]

            modal = BaseModal(
                title="Please enter some informations",
                fields=fields,
                moderator_roles=view.moderator_roles,
                staff_manager_roles=view.staff_manager_roles,
                field_details=view.field_details
            )
            await interaction.response.send_modal(modal)

class SelectorType(discord.ui.View):
    def __init__(self, options: list[str], modal_sets: list, field_details: dict, moderator_roles: list[int], staff_manager_roles: list[int]):
        super().__init__(timeout=None)
        self.options = options
        self.modals = modal_sets
        self.field_details = field_details
        self.moderator_roles = moderator_roles
        self.staff_manager_roles = staff_manager_roles

        self.add_item(self.ModalSelect(
            self.options,
            self.modals,
            self.moderator_roles,
            self.staff_manager_roles,
            self.field_details
        ))

    class ModalSelect(discord.ui.Select):
        def __init__(self, options: list[str], modals: list, moderator_roles: list[int], staff_manager_roles: list[int], field_details: dict):
            select_options = []
            name_label = []
            for i, opt in enumerate(options):
                parts = opt.split(":", 1)

                label = parts[0].strip()
                emoji = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                name_label.append(label)

                if emoji:
                    select_options.append(discord.SelectOption(label=label, value=str(i), emoji=emoji))
                else:
                    select_options.append(discord.SelectOption(label=label, value=str(i)))

            super().__init__(placeholder="Choose a ticket type...", options=select_options, custom_id="ticket_selector")

            self.modals = modals
            self.moderator_roles = moderator_roles
            self.staff_manager_roles = staff_manager_roles
            self.field_details = field_details
            self.labels = name_label

        async def callback(self, interaction: discord.Interaction):
            index = int(self.values[0])
            modal_fields = self.modals[index]

            if isinstance(modal_fields, dict):
                modal_fields = [modal_fields]

            modal = BaseModal(
                title=self.labels[index],
                fields=modal_fields,
                moderator_roles=self.moderator_roles,
                staff_manager_roles=self.staff_manager_roles,
                field_details=self.field_details
            )
            await interaction.response.send_modal(modal)

async def SpawnTickets(ctx: commands.Context, json_data):
    content, embed = LilyEmbed.ParseAdvancedEmbed(json_data['Configs']['Embed'])
    channel = ctx.guild.get_channel(json_data['Configs']['Channel_To_Spawn'])

    staff_roles = [ctx.guild.get_role(r) for r in json_data['Configs'].get('StaffManagerRoles', [])]
    mod_roles = [ctx.guild.get_role(r) for r in json_data['Configs'].get('ModeratorRoles', [])]

    ticket_type = json_data['Configs']['TicketType']
    if ticket_type[0] == 'Button':
        view = ButtonType(
            name=ticket_type[1],
            type_=ticket_type[2],
            moderator_roles=json_data['Configs'].get('ModeratorRoles', []),
            staff_manager_roles=json_data['Configs'].get('StaffManagerRoles', []),
            modal_details=json_data['Modal'][0],
            field_details=json_data['Configs']['TicketEmbedFields']
        )
        message = await channel.send(embeds=embed, view=view)
        json_data["view_type"] = "ButtonType"
        save_ticket_view(channel.id, message.id, json_data)

    elif ticket_type[0] == 'Selector':
        view = SelectorType(
            options=ticket_type[1:],
            modal_sets=json_data['Modal'],
            field_details=json_data['Configs']['TicketEmbedFields'],
            moderator_roles=json_data['Configs'].get('ModeratorRoles', []),
            staff_manager_roles=json_data['Configs'].get('StaffManagerRoles', [])
        )
        message = await channel.send(embeds=embed, view=view)
        json_data["view_type"] = "SelectorType"
        save_ticket_view(channel.id, message.id, json_data)

    else:
        await channel.send("Invalid Ticket Type")