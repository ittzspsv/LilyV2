from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator

import LilyManagement.sLilyStaffManagement as smLily
import LilyModeration.sLilyModeration as mLily
import Config.sBotDetails as Config
import discord
from discord.ext import commands



class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await smLily.initialize()

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='staffdata', description='shows data for a particular staff')
    async def staffdata(self, ctx:commands.Context, id:str):
        id = id.replace("<@", "").replace(">", "")
        staff_member = await self.bot.fetch_user(int(id))
        await ctx.send(embed=await smLily.FetchStaffDetail(staff_member))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='staffs', description='shows all staff registered name with the count')
    async def staffs(self, ctx:commands.Context):
        try:
            await smLily.FetchAllStaffs(ctx)
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Exception [staffs] {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Developer')), allow_per_server_owners=True)
    @commands.hybrid_command(name='staff_strike', description='strikes a staff with a specified reason')
    async def staffstrike(self, ctx: commands.Context, id: str, *, reason: str):
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=await smLily.StrikeStaff(ctx, id, reason))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Developer')), allow_per_server_owners=True)
    @commands.hybrid_command(name='remove_strike', description='strikes a staff with a specified reason')
    async def removestrike(self, ctx: commands.Context, strike_id: str):
        try:
            await ctx.send(embed=await smLily.RemoveStrikeStaff(ctx, strike_id))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Developer')), allow_per_server_owners=True)
    @commands.hybrid_command(name='edit_staff', description='edits a staff data')
    async def EditStaff(self, ctx: commands.Context, staff_id: str,name: str = None, role_id: str = None,joined_on: str = None, timezone: str = None,responsibility: str = None):
        staff_id = int(staff_id)
        role_id = int(role_id) if role_id else None
        await smLily.EditStaff(
            ctx, staff_id, name, role_id, joined_on, timezone, responsibility
        )

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='strikes', description='shows strikes for a concurrent staff')
    async def strikes(self, ctx: commands.Context, id: discord.Member):
        try:
            await ctx.send(embed=await smLily.ListStrikes(ctx, id))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_staff_query', description='runs arbitrary  for the database Staff')
    async def run_staff_query(self, ctx: commands.Context, *, query: str):
        await smLily.run_query(ctx, query)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='add_staff', description='Adds a member to staff_data')
    async def add_staff(self, ctx: commands.Context, staff: discord.Member):
        try:
            await smLily.AddStaff(ctx, staff)
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='remove_staff', description='Removes a member from staff_data')
    async def remove_staff(self, ctx: commands.Context, staff: discord.Member):
        await smLily.RemoveStaff(ctx, staff.id)
    
    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='remove_loa', description='Removes LOA from a staff member')
    async def remove_loa(self, ctx: commands.Context, staff: discord.Member):
        result = await smLily.RemoveLoa(ctx, staff.id)
        if result:
            await ctx.reply("LOA Removed Successfully")
        else:
            await ctx.reply(f"An error occured while removing LOA")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='request_loa', description='Requests leave from higher staffs')
    async def request_loa(self, ctx: commands.Context):
        await smLily.RequestLoa(ctx)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='add_role', description='adds a role to the role list')
    async def add_role(self, ctx: commands.Context, role: discord.Role, ban_limit: int, role_type: smLily.RoleType):
        await smLily.AddRole(ctx, role, ban_limit, role_type)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='get_all_staff_roles', description='Returns all staff roles')
    async def get_all_StaffRoles(self, ctx: commands.Context):
        await smLily.GetAllStaffRoles(ctx)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='remove_role', description='Removes a role from roles list')
    async def remove_role(self, ctx: commands.Context, role: discord.Role):
        await smLily.RemoveRole(ctx, role)


async def setup(bot):
    await bot.add_cog(LilyManagement(bot))