import random
import discord
from discord.ext import commands
from enum import Enum
import Config.sBotDetails as Config

class Games(Enum):
    GAG = "Grow a garden"
    BloxFruits = "Blox Fruits"


class RejectReasonModal(discord.ui.Modal):
    def __init__(self, middleman_channel: discord.TextChannel, mod: discord.Member, log_channel: discord.TextChannel):
        super().__init__(title="Reject Middleman Request")
        self.middleman_channel = middleman_channel
        self.mod = mod
        self.log_channel = log_channel
        self.reason = discord.ui.TextInput(
            label="Reason for rejection",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await self.log_channel.send(
            f"Middleman request in {self.middleman_channel.mention} was rejected by {self.mod.mention}.\n"
            f"Reason: {self.reason.value}"
        )
        await interaction.response.send_message(
            "Reason submitted. Middleman request will be deleted.", ephemeral=True
        )
        await self.middleman_channel.delete(reason=f"Rejected by {self.mod} for reason: {self.reason.value}")

class MiddlemanButtons(discord.ui.View):
    def __init__(
        self,
        buyer: discord.Member,
        seller: discord.Member,
        payment_handler: discord.Member,
        middleman_roles: list[discord.Role],
        hr_roles: list[discord.Role],
        log_channel: discord.TextChannel
    ):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.seller = seller
        self.payment_handler = payment_handler
        self.middleman_roles = middleman_roles
        self.hr_roles = hr_roles
        self.claimed = False
        self.log_channel = log_channel

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role in interaction.user.roles for role in self.middleman_roles):
            await interaction.response.send_message(
                "Only Middleman role members can claim this request.", ephemeral=True
            )
            return

        if self.claimed:
            await interaction.response.send_message(
                "This request is already claimed.", ephemeral=True
            )
            return

        self.claimed = True
        await interaction.response.send_message(
            f"{interaction.user.mention} has claimed the middleman request. Please provide your private server code."
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role in interaction.user.roles for role in self.hr_roles):
            await interaction.response.send_message(
                "Only HR role members can reject this request.", ephemeral=True
            )
            return

        modal = RejectReasonModal(interaction.channel, interaction.user, self.log_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.buyer and interaction.user != self.seller:
            await interaction.response.send_message(
                "Only the buyer or seller can cancel this request.", ephemeral=True
            )
            return

        if self.claimed:
            await interaction.response.send_message(
                "This request has already been claimed and cannot be canceled."
            )
            return

        await interaction.response.send_message("Middleman request canceled.")
        await interaction.channel.delete()


async def SetupMiddleman(
    ctx: commands.Context,
    buyer: discord.Member,
    seller: discord.Member,
    transaction: str,
    payment: str,
    payment_handler: discord.Member,
    game: Games,
):

    middleman_roles = [ctx.guild.get_role(rid) for rid in Config.MiddlemanRoles if ctx.guild.get_role(rid)]
    hr_roles = [ctx.guild.get_role(rid) for rid in Config.StaffManagerRoles if ctx.guild.get_role(rid)]

    if not middleman_roles:
        await ctx.send("No valid Middleman roles found!")
        return
    if not hr_roles:
        await ctx.send("No valid HR roles found!")
        return


    log_channel = ctx.guild.get_channel(1356223694388723792)
    if not log_channel or not isinstance(log_channel, discord.TextChannel):
        await ctx.send("Log channel not found or invalid!")
        return
    
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        buyer: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        seller: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        payment_handler: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    channel = await ctx.guild.create_text_channel(
        name=f"Middleman-{random.randrange(1000, 5000)}",
        overwrites=overwrites,
        reason=f"Created for middleman request between {buyer} and {seller}"
    )

    embed = discord.Embed(
        title="MIDDLEMAN REQUEST",
        description=f"- Game: **{game.value}**",
        colour=0xf500c8
    )
    embed.add_field(name="👤Buyer", value=buyer.mention, inline=True)
    embed.add_field(name="👤Seller", value=seller.mention, inline=True)
    embed.add_field(name="📦Transaction", value=transaction, inline=False)
    embed.add_field(name="💰Payment", value=payment, inline=True)
    embed.add_field(name="🧾Payment Handler", value=payment_handler.mention, inline=True)

    view = MiddlemanButtons(buyer, seller, payment_handler, middleman_roles, hr_roles, log_channel)
    await channel.send(embed=embed, view=view)
