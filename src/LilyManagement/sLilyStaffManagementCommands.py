from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator

import LilyManagement.sLilyStaffManagement as smLily
import LilyModeration.sLilyModeration as mLily
import Config.sBotDetails as Config

from discord.ext import commands



class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='staffdata', description='shows data for a particular staff')
    async def staffdata(self, ctx:commands.Context, id:str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        staff_member = await self.bot.fetch_user(int(id))
        await ctx.send(view=await smLily.FetchStaffDetail(staff_member))

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='staffs', description='shows all staff registered name with the count')
    async def staffs(self, ctx:commands.Context):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536, 1356198968962449478]:
            await ctx.send("Server Change!")
            return
        try:
            await ctx.send(embed=await smLily.FetchAllStaffs())
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Exception {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.StaffManagerRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='staffstrike', description='strikes a staff with a specified reason')
    async def staffstrike(self, ctx: commands.Context, id: str, *, reason: str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=await smLily.StrikeStaff(ctx, id, reason))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.StaffManagerRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='removestrike', description='strikes a staff with a specified reason')
    async def removestrike(self, ctx: commands.Context, id: str, strike_id: str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=await smLily.RemoveStrikeStaff(ctx, id, strike_id))
        except Exception as e:
            await ctx.send(f"Exception {e}")


    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='strikes', description='shows strikes for a concurrent staff')
    async def strikes(self, ctx: commands.Context, id: str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=await smLily.ListStrikes(id))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles + Config.StaffManagerRoles)
    @commands.hybrid_command(name='run_query', description='runs arbitrary query')
    async def run_staff_query(self, ctx: commands.Context, *, query: str):
        await smLily.run_query(ctx, query)

async def setup(bot):
    await bot.add_cog(LilyManagement(bot))