from discord.ext import commands

import json
import LilyTicketTool.LilyTicketToolThread as LTTT
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator

class LilyTicketTool(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
                    await LTTT.SpawnTicket(ctx, json_data)
                    return
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.hybrid_command(name='close', description='close a ticket thread')
    async def CloseTicket(self, ctx: commands.Context):
         await LTTT.CloseTicketThread(ctx)
async def setup(bot):
    await bot.add_cog(LilyTicketTool(bot))