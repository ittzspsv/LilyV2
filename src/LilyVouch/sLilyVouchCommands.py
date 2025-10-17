from LilyRulesets.sLilyRulesets import PermissionEvaluator

import discord
from discord.ext import commands
import Config.sBotDetails as Config
import LilyVouch.sLilyVouches as vLily
import LilyManagement.sLilyStaffManagement as LSM
import LilyModeration.sLilyModeration as mLily


class LilyVouch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(rate=1, per=160, type=commands.BucketType.user)
    @commands.hybrid_command(name='vouch', description='Vouch a service handler')
    async def vouch(self, ctx: commands.Context,  member: discord.Member, *,note: str = "", received: str = ""):
        if not member:
            pass
        elif member == ctx.author:
            await ctx.send(embed=mLily.SimpleEmbed("You cannot vouch yourself!"))
        else:
            account_age = (discord.utils.utcnow() - ctx.author.created_at).days
            m_account_age = (discord.utils.utcnow() - member.created_at).days
            if account_age < 90:
                await ctx.send(embed=mLily.SimpleEmbed("Your Account is Not Old Enough to Vouch! a Service provider"))
                return
            if m_account_age < 90:
                await ctx.send(embed=mLily.SimpleEmbed("Service Provider Account should be 3 months old!!"))
                return 
            await ctx.send(embed=vLily.store_vouch(ctx, member, note, received))

    @commands.cooldown(rate=1, per=160, type=commands.BucketType.user)
    @commands.hybrid_command(name='show_vouches', description='displays recent 5 vouches for a  service handler')
    async def show_vouches(self, ctx: commands.Context,  member: discord.Member, min:int = 0, max:int = 3):
        if not member:
            return

        if max > min + 10:
            max = min + 10
        await ctx.send(embed=vLily.display_vouch_embed(ctx, member, min, max))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Community Manager')))
    @commands.hybrid_command(name='verify_service_provider', description='if a service provider is trusted then he can be verified')
    async def verify_service_provider(self, ctx: commands.Context,  member: discord.Member):
        if not member:
            await ctx.send(embed=mLily.SimpleEmbed("No Members Passed in!"))
        else:
            await ctx.send(embed=vLily.verify_servicer(ctx, member.id))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Community Manager')))
    @commands.hybrid_command(name='unverify_service_provider', description='if a service provider is found to be  fraud after verification then he can be un-verified')
    async def unverify_service_provider(self, ctx: commands.Context,  member: discord.Member):
        if not member:
            await ctx.send(embed=mLily.SimpleEmbed("No Members Passed in!"))
        else:
            await ctx.send(embed=vLily.unverify_servicer(ctx, member.id))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Community Manager')))
    @commands.hybrid_command(name='delete_vouch', description='deletes a vouch from mentioned service provider at a particular timeframe')
    async def delete_vouch(self, ctx: commands.Context,  member: discord.Member, timestamp_str: str):
        if not member:
            await ctx.send(embed=mLily.SimpleEmbed("No Members Passed in!"))
        else:
            success = vLily.delete_vouch(ctx, member.id, timestamp_str)
            if success:
                await ctx.send(embed=mLily.SimpleEmbed("Successfully deleted vouch from the service provider"))
            else:
                await ctx.send(embed=mLily.SimpleEmbed("Unable to delete vouch from the service provider!  Verify correct timestamp"))


async def setup(bot):
    await bot.add_cog(LilyVouch(bot))