from discord.ext import commands
from core.features.permissions.lily_permissions import permission
from core.features.ticketing.controller.lily_ticketing_controller import LilyTicketingController
from typing import Optional
from core.utils.embeds.sLilyEmbed import simple_embed
import json
import discord

class LilyTicketTool(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controller: Optional[LilyTicketingController] = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self.controller is not None:
            await self.controller.initialize_ticket_view(self.bot)
            print("[Ticket Tool Cog] Initialized")

    async def on_load(self):
         self.controller = LilyTicketingController(
              self.bot.logs_db,
              self.bot.db
         )

    @commands.hybrid_group()
    async def ticket(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Ticketing System Command Hierarchy!"))

    @ticket.command(name='spawn', description='spawn in ticket processor')
    @permission(command_name="spawn_ticket", restrict=True)
    async def spawnticket(self, ctx):
        if self.controller is None:
            return

        if not ctx.message.attachments:
            await ctx.send("Please attach a .json Config")
            return

        for attachment in ctx.message.attachments:
            if attachment.filename.endswith('.json'):
                    content = await attachment.read()
                    json_data = json.loads(content.decode('utf-8'))
                    await self.controller.spawn_ticket(ctx, json_data)
                    await ctx.reply("Ticket has been spawned successfully!")
            
    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @ticket.command(name='close', description='close a ticket thread')
    @permission(command_name="ticket_close")
    async def CloseTicket(self, ctx: commands.Context, reason: str):
         if self.controller is not None:
            await self.controller.close_ticket_thread(ctx, reason)
         
    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @ticket.command(name='rename', description='renames a ticket channel')
    @permission(command_name="ticket_rename")
    async def rename_ticket(self, ctx: commands.Context, * ,name: str):
         if self.controller is not None:
            await self.controller.rename_ticket(ctx, name)

    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @ticket.command(name='add', description='adds a member to the ticket')
    @permission(command_name="ticket_add")
    async def ticket_add(self, ctx: commands.Context, user: discord.Member):
         if self.controller is not None:
            await self.controller.ticket_add_user(ctx, user)

async def setup(bot):
    cog = LilyTicketTool(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()