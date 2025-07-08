import discord
import json
from pathlib import Path
from discord.ext import commands
import Misc.sLilyEmbed as LilyEmbed

TICKET_VIEWS_PATH = Path("storage/view/TicketViews.json")
TICKET_CHANNEL_LOG_PATH = Path("storage/view/TicketChannelViews.json")

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
                message = await channel.fetch_message(entry["message_id"])
            except:
                continue

            config = entry["config"]

            if config.get("view_type") == "ButtonType":
                view = ButtonType(
                    name=config['Configs']['TicketType'][1],
                    type_=config['Configs']['TicketType'][2],
                    moderator_roles=config['Configs'].get('ModeratorRoles', []),
                    modal_details=config['Modal'][0],
                    field_details=config['Configs']['TicketEmbedFields']
                )
            elif config.get("view_type") == "SelectorType":
                view = SelectorType(
                    options=config['Configs']['TicketType'][1:],
                    modal_sets=config['Modal'],
                    field_details=config['Configs']['TicketEmbedFields'],
                    moderator_roles=config['Configs'].get('ModeratorRoles', [])
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

            class BasicTicketer(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="Claim", style=discord.ButtonStyle.secondary, custom_id="claim")
                async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    user = interaction.user
                    if any(role.id in moderator_roles for role in user.roles):
                        await interaction.response.send_message(f"{user.mention} has claimed this ticket!", ephemeral=False)
                    else:
                        await interaction.response.send_message("You are not allowed to claim the ticket", ephemeral=True)

                @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close")
                async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    user = interaction.user
                    if any(role.id in moderator_roles for role in user.roles):
                        await interaction.response.send_message(f"Ticket has been closed by {user.mention}", ephemeral=False)
                        await interaction.channel.delete()
                    else:
                        await interaction.response.send_message("You are not allowed to close the ticket", ephemeral=True)

            try:
                bot.add_view(BasicTicketer())
            except Exception:
                continue

class BaseModal(discord.ui.Modal):
    def __init__(self, title: str, fields: list[dict], moderator_roles: list, field_details: dict, on_submit_callback=None):
        super().__init__(title=title)
        self.on_submit_callback = on_submit_callback
        self.inputs = {}
        self.moderator_roles = moderator_roles
        self.field_details = field_details

        for field_dict in fields:
            for label, max_length in field_dict.items():
                safe_label = label[:45]
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
            await TicketConstructor(values, self.moderator_roles, interaction, self.field_details)

async def SendTicketLog(guild: discord.Guild, config: dict, *, opener=None, claimer=None, closer=None, modal_data: dict = None):
    log_channel_id = config.get("LogChannel") or config.get("log_channel")
    if not log_channel_id:
        return

    log_channel = guild.get_channel(log_channel_id)
    if not log_channel:
        return

    embed = discord.Embed(title="Ticket Log", color=discord.Color.dark_purple())

    if opener:
        embed.add_field(name="Opened By", value=f"{opener.mention} ({opener.id})", inline=False)
    if claimer:
        embed.add_field(name="Claimed By", value=f"{claimer.mention} ({claimer.id})", inline=False)
    if closer:
        embed.add_field(name="Closed By", value=f"{closer.mention} ({closer.id})", inline=False)

    if modal_data:
        description = "\n".join(f"**{k}**: `{v}`" for k, v in modal_data.items())
        embed.add_field(name="Form Responses", value=description or "None", inline=False)

    embed.set_footer(text="Lily Ticket Handler")
    embed.timestamp = discord.utils.utcnow()

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass

async def TicketConstructor(values: dict, moderator_roles: list, interaction: discord.Interaction, field_details: dict):
    guild = interaction.guild
    user = interaction.user

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
        color=discord.Color.blue()
    )

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
            if any(role.id in moderator_roles for role in user.roles):
                self.claimer = user
                await interaction.response.send_message(f"{user.mention} has claimed this ticket!", ephemeral=False)
            else:
                await interaction.response.send_message("You are not allowed to claim the ticket", ephemeral=True)

        @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close")
        async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user = interaction.user
            if any(role.id in moderator_roles for role in user.roles):
                await interaction.response.send_message(f"Ticket has been closed by {user.mention}", ephemeral=False)
                await SendTicketLog(
                    guild,
                    log_data,
                    opener=interaction.channel.topic and guild.get_member_named(interaction.channel.topic),
                    claimer=self.claimer,
                    closer=user,
                    modal_data=values
                )
                await interaction.channel.delete()
            else:
                await interaction.response.send_message("You are not allowed to close the ticket", ephemeral=True)

    view = BasicTicketer()
    await private_channel.send(content=f"{user.mention} your ticket has been created.", embeds=embeds, view=view)
    await interaction.followup.send(f"Your ticket has been created: {private_channel.mention}", ephemeral=True)

    save_ticket_channel(private_channel.id, log_data)
    await SendTicketLog(guild, log_data, opener=user, modal_data=values)


class ButtonType(discord.ui.View):
    def __init__(self, name: str, type_: str, moderator_roles: list, modal_details: dict, field_details: dict, *, timeout=None):
        super().__init__(timeout=None)
        self.name = name
        self.type_ = type_
        self.moderator_roles = moderator_roles
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
                field_details=view.field_details
            )
            await interaction.response.send_modal(modal)

class SelectorType(discord.ui.View):
    def __init__(self, options: list[str], modal_sets: list, field_details: dict, moderator_roles: list[int]):
        super().__init__(timeout=None)
        self.options = options
        self.modals = modal_sets
        self.field_details = field_details
        self.moderator_roles = moderator_roles

        self.add_item(self.ModalSelect(self.options, self.modals, self.moderator_roles, self.field_details))

    class ModalSelect(discord.ui.Select):
        def __init__(self, options: list[str], modals: list, moderator_roles: list[int], field_details: dict):
            select_options = [
                discord.SelectOption(label=opt, value=str(i)) for i, opt in enumerate(options)
            ]
            super().__init__(placeholder="Choose a ticket type...", options=select_options, custom_id="ticket_selector")

            self.modals = modals
            self.moderator_roles = moderator_roles
            self.field_details = field_details
            self.labels = options

        async def callback(self, interaction: discord.Interaction):
            index = int(self.values[0])
            modal_fields = self.modals[index]

            if isinstance(modal_fields, dict):
                modal_fields = [modal_fields]

            modal = BaseModal(
                title=self.labels[index],
                fields=modal_fields,
                moderator_roles=self.moderator_roles,
                field_details=self.field_details
            )
            await interaction.response.send_modal(modal)

async def SpawnTickets(ctx: commands.Context, json_data):
    content, embed = LilyEmbed.ParseAdvancedEmbed(json_data['Configs']['Embed'])
    channel = ctx.guild.get_channel(json_data['Configs']['Channel_To_Spawn'])

    ticket_type = json_data['Configs']['TicketType']
    if ticket_type[0] == 'Button':
        view = ButtonType(
            name=ticket_type[1],
            type_=ticket_type[2],
            moderator_roles=json_data['Configs'].get('ModeratorRoles', []),
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
            moderator_roles=json_data['Configs'].get('ModeratorRoles', [])
        )
        message = await channel.send(embeds=embed, view=view)
        json_data["view_type"] = "SelectorType"
        save_ticket_view(channel.id, message.id, json_data)

    else:
        await channel.send("Invalid Ticket Type")