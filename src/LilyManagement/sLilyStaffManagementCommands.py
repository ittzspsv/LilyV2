from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator

import LilyManagement.sLilyStaffManagement as smLily
import LilyModeration.sLilyModeration as mLily
import Config.sBotDetails as Config
import discord
from discord.ext import commands



class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='staffdata', description='shows data for a particular staff')
    async def staffdata(self, ctx:commands.Context, id:str):
        id = id.replace("<@", "").replace(">", "")
        staff_member = await self.bot.fetch_user(int(id))
        await ctx.send(embed=await smLily.FetchStaffDetail(staff_member))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='staffs', description='shows all staff registered name with the count')
    async def staffs(self, ctx:commands.Context):
        try:
            await ctx.send(embeds=await smLily.FetchAllStaffs())
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Exception {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Developer')))
    @commands.hybrid_command(name='staff_strike', description='strikes a staff with a specified reason')
    async def staffstrike(self, ctx: commands.Context, id: str, *, reason: str):
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=await smLily.StrikeStaff(ctx, id, reason))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Developer')))
    @commands.hybrid_command(name='remove_strike', description='strikes a staff with a specified reason')
    async def removestrike(self, ctx: commands.Context, strike_id: str):
        try:
            await ctx.send(embed=await smLily.RemoveStrikeStaff(ctx, strike_id))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='strikes', description='shows strikes for a concurrent staff')
    async def strikes(self, ctx: commands.Context, id: discord.Member):
        try:
            await ctx.send(embed=await smLily.ListStrikes(id))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_staff_query', description='runs arbitrary  for the database Staff')
    async def run_staff_query(self, ctx: commands.Context, *, query: str):
        await smLily.run_query(ctx, query)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='add_staff', description='Adds a member to staff_data')
    async def add_staff(self, ctx: commands.Context, staff: discord.Member):
        try:
            await smLily.AddStaff(ctx, staff)
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='remove_staff', description='Removes a member from staff_data')
    async def remove_staff(self, ctx: commands.Context, staff: discord.Member):
        await smLily.RemoveStaff(ctx, staff.id)
    
    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='remove_loa', description='Removes LOA from a staff member')
    async def remove_loa(self, ctx: commands.Context, staff: discord.Member):
        result = await smLily.RemoveLoa(staff.id)
        if result:
            await ctx.reply("LOA Removed Successfully")
        else:
            await ctx.reply(f"An error occured while removing LOA")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='request_loa', description='Requests leave from higher staffs')
    async def request_loa(self, ctx: commands.Context):
        await smLily.RequestLoa(ctx)




async def setup(bot):
    await bot.add_cog(LilyManagement(bot))