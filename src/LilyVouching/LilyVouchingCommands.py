from discord.ext import commands

import LilyVouching.sLilyVouchCore as LVC
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import discord

class LilyVouch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='vouch', description='vouch a service provider')
    async def vouch(self, ctx: commands.Context, vouch_to: discord.Member, desc: str=None):
        await LVC.AddVouch(ctx, ctx.author, vouch_to, desc)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='remove_vouch', description='removes a vouch a service provider')
    async def remove_vouch(self, ctx: commands.Context, vouch_id: int):
        await LVC.RemoveVouch(ctx, vouch_id)

async def setup(bot):
    await bot.add_cog(LilyVouch(bot))