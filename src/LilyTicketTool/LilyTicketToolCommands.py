from discord.ext import commands

import json
import LilyTicketTool.LilyTicketToolThread as LTTT
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator

class LilyTicketTool(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        LTTT.LTTC.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await LTTT.InitializeTicketView(self.bot)
        print("[Ticket Tool Cog] Initialized")


    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='spawn_ticket', description='spawn in ticket processor')
    async def spawnticket(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("Please attach a .json Config")
            return

        for attachment in ctx.message.attachments:
            if attachment.filename.endswith('.json'):
                    content = await attachment.read()
                    json_data = json.loads(content.decode('utf-8'))
                    await LTTT.spawn_ticket(ctx, json_data)
                    return
            
    
    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff', 'Engagement Staff Team')))
    @commands.hybrid_command(name='close', description='close a ticket thread')
    async def CloseTicket(self, ctx: commands.Context):
         await LTTT.CloseTicketThread(ctx)
         
    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff', 'Engagement Staff Team')))
    @commands.hybrid_command(name='ticket_rename', description='renames a ticket channel')
    async def rename_ticket(self, ctx: commands.Context, * ,name: str):
         await LTTT.RenameTicket(ctx, name)

async def setup(bot):
    await bot.add_cog(LilyTicketTool(bot))