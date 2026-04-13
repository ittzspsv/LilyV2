from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator

import LilyManagement.sLilyStaffManagement as smLily
import LilyManagement.types.sLilyStaffManagementTypes as types
import LilyManagement.db.sLilyStaffDatabaseAccess as LSDB
import discord
from discord.ext import commands
import re

from discord.ui import RoleSelect
from Misc.sLilyEmbed import simple_embed


class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await LSDB.initialize()
        await LSDB.initialize_cache()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return

        staff_id = after.id
        guild_id = after.guild.id

        try:
            cursor = await LSDB.sdb.execute(
                "SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?",
                (staff_id, guild_id)
            )
            exists = await cursor.fetchone()

            if not exists:
                return
           

            cursor = await LSDB.sdb.execute("""
                SELECT role_id, role_type
                FROM roles
                WHERE guild_id = ?
            """, (guild_id,))
            db_roles = await cursor.fetchall()

            staff_role_ids = {r[0] for r in db_roles if r[1] == "Staff"}
            responsibility_role_ids = {r[0] for r in db_roles if r[1] == "Responsibility"}


            top_staff_role = None
            for role in sorted(after.roles, key=lambda r: r.position, reverse=True):
                if role.id in staff_role_ids:
                    top_staff_role = role
                    break

            discord_responsibilities = {
                role.id for role in after.roles
                if role.id in responsibility_role_ids
            }

            async with LSDB.sdb.execute("BEGIN IMMEDIATE"):
                await LSDB.sdb.execute(
                    "DELETE FROM staff_roles WHERE staff_id = ?",
                    (staff_id,)
                )

                if not top_staff_role:
                    await LSDB.sdb.execute("""
                        UPDATE staffs
                        SET retired = 1
                        WHERE staff_id = ? AND guild_id = ?
                    """, (staff_id, guild_id))

                    await LSDB.sdb.commit()
                    return

                await LSDB.sdb.execute("""
                    UPDATE staffs
                    SET retired = 0
                    WHERE staff_id = ? AND guild_id = ?
                """, (staff_id, guild_id))

                await LSDB.sdb.execute("""
                    INSERT INTO staff_roles (staff_id, role_id)
                    VALUES (?, ?)
                """, (staff_id, top_staff_role.id))

                if discord_responsibilities:
                    await LSDB.sdb.executemany("""
                        INSERT INTO staff_roles (staff_id, role_id)
                        VALUES (?, ?)
                    """, [(staff_id, rid) for rid in discord_responsibilities])
            print(f"[On_Role Update] Updated {after.name} Role On The Database")
            await LSDB.sdb.commit()

        except Exception as e:
            print(f"[on_member_update] Staff Sync Error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        pass
        await smLily.MessageTracker(message=message)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='staffdata', description='shows data for a particular staff')
    async def staffdata(self, ctx:commands.Context, user:discord.Member=None):
        if not user:
            user = ctx.author
        await ctx.reply(embed=await smLily.FetchStaffDetail(user))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='staffs', description='shows all staff registered name with the count')
    async def staffs(self, ctx:commands.Context):
        try:
            await smLily.FetchAllStaffs(ctx)
        except Exception as e:
            await ctx.reply(embed=simple_embed(f"Exception [staffs] {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name='staff_strike', description='strikes a staff with a specified reason')
    async def staffstrike(self, ctx: commands.Context, staff: discord.Member, *, reason: str):
        try:
            await smLily.StrikeStaff(ctx, staff, reason)
        except Exception as e:
            await ctx.reply(embed=simple_embed(f"Failed to strike staff", 'cross'))
            print(f"Staff Strike [Exception] {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name='remove_strike', description='strikes a staff with a specified reason')
    async def removestrike(self, ctx: commands.Context, strike_id: str):
        try:
            await smLily.RemoveStrikeStaff(ctx, strike_id)
        except Exception as e:
            await ctx.reply(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Developer')), allow_per_server_owners=True)
    @commands.hybrid_command(name='edit_staff', description='edits a staff data')
    async def EditStaff(self, ctx: commands.Context, staff_id: str,name: str = None, joined_on: str = None, timezone: str = None,responsibility: str = None):
        staff_id = int(staff_id)
        role_id = int(role_id) if role_id else None
        await smLily.EditStaff(
            ctx, staff_id, name, role_id, joined_on, timezone, responsibility
        )

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name="edit_my_staff_data", description="edits your staff data")
    async def self_edit_staff_data(self, ctx: commands.Context, name: str=None, timezone: str=None):
        if not bool(re.fullmatch(r'[+-](0?\d|1[0-4]):[0-5]\d', timezone)):
            await ctx.reply(embed=simple_embed("Invalid Timezone Format! Timezone should be given by `+05:30` or Similar", 'cross'))
            return 
        await smLily.EditStaff(ctx, ctx.author.id, name, None, None, timezone, None)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='strikes', description='shows strikes for a concurrent staff')
    async def strikes(self, ctx: commands.Context, id: discord.Member):
        try:
            await smLily.ListStrikes(ctx, id)
        except Exception as e:
            await ctx.reply(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='add_staff', description='Adds a member to staff_data')
    async def add_staff(self, ctx: commands.Context, staff: discord.Member):
        try:
            await smLily.AddStaff(ctx, staff)
        except Exception as e:
            await ctx.reply(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='add_staffs_batch', description='Adds a batch of staffs to staff_data')
    async def add_staffs_batch(self, ctx: commands.Context, staffs: str):
        await ctx.defer()
        await smLily.AddStaffBatch(ctx, staffs)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('SequentEval3942',)))
    @commands.hybrid_command(name='update_all_staffs', description='updates all staff details')
    async def update_all_staffs(self, ctx: commands.Context):
        await ctx.defer()
        await smLily.update_all_staffs(ctx)

    '''
    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Administrator', 'Senior Administrator')))
    async def update_staff(self, ctx: commands.Context, staff: discord.Member):
        await ctx.defer()
        await smLily.update_staff(ctx, staff)
    '''

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='remove_staff', description='Removes a member from staff_data')
    async def remove_staff(self, ctx: commands.Context, staff: discord.Member, reason: str):
        if isinstance(staff, discord.Member):
            await smLily.RemoveStaff(ctx, staff, reason)
        else:
            await ctx.reply(embed=simple_embed("Invalid type of staff has been passed.", 'cross'))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='remove_staff_raw', description='Removes a member from staff_data')
    async def remove_staff_raw(self, ctx: commands.Context, staff: str, reason: str):
        await smLily.RemoveStaff(ctx, int(staff), reason)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name='get_all_staff_roles', description='Returns all staff roles')
    async def get_all_StaffRoles(self, ctx: commands.Context):
        await smLily.GetAllStaffRoles(ctx)

    '''
    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Developer', 'Staff Manager')), allow_per_server_owners=True)
    @commands.hybrid_command(name='setup_staff_roles')
    async def setup_staff_roles(self, ctx: commands.Context):
        await ctx.send(view=smLily.StaffRoleView(self.bot, ctx.author))
    '''

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator', 'Administrator', 'Senior Moderator')))
    @commands.hybrid_command(name='add_loa', description='Assigns a staff leave')
    async def add_loa(self, ctx: commands.Context, staff: discord.Member, *, reason: str):
        await smLily.AddLOA(ctx, staff, reason)
    

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator', 'Administrator', 'Senior Moderator')))
    @commands.hybrid_command(name='remove_loa', description='Removes a staff leave')
    async def remove_loa(self, ctx: commands.Context, staff: discord.Member):
        await smLily.RemoveLOA(ctx, staff)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name='promote', description='Promotes a staff to upper rank')
    async def promote(self, ctx: commands.Context, staff: discord.Member, * ,reason: str):
        await ctx.defer()
        await smLily.UpdateStaff(ctx, staff, reason, "promotion")

    
    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Garbadsakjfsjdfhlaksdf',)))
    @commands.hybrid_command(name='promote_batch', description='Promotes a batch of staffs to upper rank')
    async def promote_batch(self, ctx: commands.Context, * ,query: str):
        await ctx.defer()
        await smLily.UpdateStaffBatch(ctx, query, "promotion")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name='demote', description='Demotes a staff to lower rank')
    async def demote(self, ctx: commands.Context, staff: discord.Member, * ,reason: str):
        await ctx.defer()
        await smLily.UpdateStaff(ctx, staff, reason, "demotion")

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name="quota_add", description="Adds a staff quota to check by")
    async def add_quota(self, ctx: commands.Context, quota_role: discord.Role, minimum_ms: int, minimum_msg: int, on_quota_pass: types.OnQuotaEvent=None, on_quota_fail: types.OnQuotaEvent=None, check_by: types.QuotaCheckBy=None):
        await smLily.AddStaffQuota(ctx, quota_role, minimum_ms, minimum_msg, on_quota_pass, on_quota_fail, check_by)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name="quota_list", description="List all defined quotas for this server")
    async def list_quota(self, ctx: commands.Context):
        await smLily.FetchStaffQuota(ctx)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator', 'Senior Administrator')))
    @commands.hybrid_command(name="quota_remove", description="Remove a defined quota by it's ID")
    async def remove_quota(self, ctx: commands.Context, quota_id: str):
        await smLily.RemoveStaffQuota(ctx, int(quota_id))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff',)))
    @commands.hybrid_command(name="quota_check", description="Check quota for a given staff")
    async def check_quota(self, ctx: commands.Context, staff: discord.Member=None):
        staff_member = None
        if staff is None:
            staff_member = ctx.author
        else:
            staff_member = staff
        await smLily.CheckStaffQuota(ctx, staff_member)

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator')))
    @commands.hybrid_command(name="remove_staff_role", description="Removes a staff role from the database")
    async def remove_role(self, ctx: commands.Context, role: discord.Role):
        await smLily.RemoveRole(ctx, role.id)
    
    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator')))
    @commands.hybrid_command(name="remove_staff_role_raw", description="Removes a staff role from the database")
    async def remove_role_raw(self, ctx: commands.Context, role: str):
        await smLily.RemoveRole(ctx, int(role))

    @PermissionEvaluator(RoleAllowed=lambda: smLily.GetRoles(('Staff Manager', 'Head Administrator')))
    @commands.hybrid_command(name="quota_evaluate", description="Evaluates Staff quota and updates the results")
    async def evaluate_staff_quota(self, ctx: commands.Context):
        await smLily.EvaluateStaffQuota(ctx)



async def setup(bot):
    await bot.add_cog(LilyManagement(bot))