from discord.ext import commands

import json
import LilyTicketTool.LilyTicketToolCore as LTTC

class LilyTicketTool(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.hybrid_command(name='spawn_ticket', description='spawn in ticket processor')
    async def spawnticket(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("Please attach a .json Config")
            return

        for attachment in ctx.message.attachments:
            if attachment.filename.endswith('.json'):
                try:
                    content = await attachment.read()
                    json_data = json.loads(content.decode('utf-8'))
                    await LTTC.SpawnTickets(ctx, json_data)
                    return

                except Exception as e:
                    await ctx.send(f"Exception {e}")
                    return

async def setup(bot):
    await bot.add_cog(LilyTicketTool(bot))