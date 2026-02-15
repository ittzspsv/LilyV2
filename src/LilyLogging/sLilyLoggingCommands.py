import discord

import LilyLogging.sLilyLogging as fLilyLogging
from discord.ext import commands
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator


import Config.sBotDetails as Config

class LilyLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await fLilyLogging.initialize()


    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    @commands.hybrid_command(name='bot_logs', description='gets core bot logs')
    async def botlogs(self, ctx:commands.Context):
        if ctx.author.id not in Config.ids:
            return
        path = 'storage/LilyLogs.txt' 
        try:
            with open(path, 'rb') as f:
                await ctx.send(file=discord.File(f, filename='LilyLogs.txt'))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    @commands.hybrid_command(name='clear_bot_logs', description='clears all bot logs')
    async def clear_botlogs(self, ctx:commands.Context):
        if ctx.author.id not in Config.ids:
            await ctx.send("No Permission")
            return
        try:
            with open("storage/LilyLogs.txt", 'r+') as f:
                f.truncate(0)
            await ctx.send("Successfully Cleared Logs")
        except Exception as e:
            await ctx.send(f"Exception {e}")


async def setup(bot):
    await bot.add_cog(LilyLogging(bot))