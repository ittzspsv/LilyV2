import re
import discord

from discord.ext import commands, tasks
from datetime import timedelta

from typing import Optional
from src.core.features.permissions.lily_permissions import permission
from src.core.utils import lily_utility as LilyUtility
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.features.management.controller.lily_management_controller import LilyManagementController
from src.core.features.management.types.staff_management_types import *
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from src.core.features.management.components.staff_management_components import LOARequestView


class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controller: Optional[LilyManagementController] = None
        self.db: Optional[BotGlobalsDatabaseAccess] = None

        self.message_reset_schedular.start()
        self.quota_reset_schedular.start()

    async def on_load(self):
        self.controller = LilyManagementController(self.bot.db)
        self.db = self.bot.db

        """ Initialize all LOA views """
        if self.db is not None:
            rows = await self.db.fetch_all_loa_pending()
            for row in rows:
                try:
                    view = LOARequestView(
                        self.db,
                        row["staff_id"],
                        row["guild_id"],
                        row["staff_pfp"],
                        row["reason"],
                        row["days"]
                    )

                    self.bot.add_view(view, message_id=row["message_id"])
                except Exception as e:
                    print(f"Exception [LOARequestView] {e}")
                    continue
            print("LOA Views Initialized!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.controller is not None:
            await self.controller.on_message(message=message)

    @tasks.loop(minutes=5)
    async def message_reset_schedular(self):
        if self.bot.db is None:
            return

        now = LilyUtility.utcnow()

        row = await self.bot.db.fetch_one(
            "SELECT next_day_update, next_week_update, next_month_update FROM updates"
        )

        if not row:
            return

        next_day, next_week, next_month = map(LilyUtility.parse_date, row)

        if next_day and now >= next_day:
            await self.daily_callback()

            new_day = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            await self.bot.db.execute(
                "UPDATE updates SET next_day_update = ?", 
                (LilyUtility.iso(new_day),),
                commit=True
            )

        if next_week and now >= next_week:
            await self.weekly_callback()

            days_ahead = 7 - now.weekday()
            if days_ahead == 0:
                days_ahead = 7

            new_week = (now + timedelta(days=days_ahead)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            await self.bot.db.execute(
                "UPDATE updates SET next_week_update = ?", 
                (LilyUtility.iso(new_week),),
                commit=True
            )

        if next_month and now >= next_month:
            await self.monthly_callback()

            if now.month == 12:
                new_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                new_month = now.replace(month=now.month + 1, day=1)

            new_month = new_month.replace(hour=0, minute=0, second=0, microsecond=0)

            await self.bot.db.execute(
                "UPDATE updates SET next_month_update = ?", 
                (LilyUtility.iso(new_month),),
                commit=True
            )

    @tasks.loop(minutes=1)
    async def quota_reset_schedular(self):
        if self.bot.db is None:
            return
        
        if self.controller is None:
            return

        now = LilyUtility.utcnow()

        row = await self.bot.db.fetch_one(
            "SELECT next_day_quota_update, next_week_quota_update, next_month_quota_update FROM updates"
        )

        if not row:
            return
        next_day, next_week, next_month = map(LilyUtility.parse_date, row)
        """ Quota evaluator """
        if next_day and now >= next_day:
            new_day = now.replace(
                hour=23,
                minute=55,
                second=0,
                microsecond=0
            )

            if now >= new_day:
                new_day += timedelta(days=1)

            await self.bot.db.execute(
                "UPDATE updates SET next_day_quota_update = ?",
                (LilyUtility.iso(new_day),),
                commit=True
            )


            """ Daily quota evaluator method here """
            await self.controller.automatic_quota_evaluator("1d", self.bot)


        """ Weekly quota evaluator """
        if next_week and now >= next_week:
            days_ahead = 7 - now.weekday()
            if days_ahead == 0:
                days_ahead = 7

            new_week = (
                (now + timedelta(days=days_ahead))
                .replace(hour=0, minute=0, second=0, microsecond=0)
                - timedelta(minutes=5)
            )


            await self.bot.db.execute(
                "UPDATE updates SET next_week_quota_update = ?",
                (LilyUtility.iso(new_week),),
                commit=True
            )
            """ Weekly quota evaluator reset """
            await self.controller.automatic_quota_evaluator("7d", self.bot)


        """ Monthly quota evaluate """
        if next_month and now >= next_month:
            if now.month == 12:
                new_month = now.replace(
                    year=now.year + 1,
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
            else:
                new_month = now.replace(
                    month=now.month + 1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

            new_month -= timedelta(minutes=5)


            await self.bot.db.execute(
                "UPDATE updates SET next_month_quota_update = ?",
                (LilyUtility.iso(new_month),),
                commit=True
            )


            """ Monthly Quota evaluator """
            await self.controller.automatic_quota_evaluator("30d", self.bot)

    async def daily_callback(self):
        if self.db is None:
            return

        await self.db.reset_messages("daily")

    async def weekly_callback(self):
        if self.db is None:
            return
        
        await self.db.reset_messages("weekly")

    async def monthly_callback(self):
        if self.db is None:
            return
        
        await self.db.reset_messages("monthly")

    @commands.hybrid_group(name="staff", description="Staff management commands")
    async def staff(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily Staff Management System"
                )
            )

    @commands.hybrid_group(name="infraction", description="infraction management commands")
    async def strike(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily Staff Strikes Management System"
                )
            )

    @commands.hybrid_group(name="loa", description="Leave of absence management")
    async def loa(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily LOA Management System"
                )
            )

    @commands.hybrid_group(name="rank", description="Promotion and demotion commands")
    async def rank(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily Rank Management System (Promotion, Demotion)"
                )
            )

    @commands.hybrid_group(name="quota", description="Quota management commands")
    async def quota(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily Quota Management System"
                )
            )

    @commands.hybrid_group(name="dev", description="Developer utility commands")
    async def dev(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily Developer-Only Command Group"
                )
            )

    @commands.hybrid_group(name="staff_role", description="Staff Management role utility commands")
    async def staff_role(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                embed=simple_embed(
                    "Lily Staff Role Management Command Group"
                )
            )

    @staff.command(name='data', description='shows data for a particular staff')
    @permission(command_name="staff_data")
    async def staff_data(self, ctx:commands.Context, user:discord.Member=None):
        if not user:
            user = ctx.author
        if self.controller is not None:
            await self.controller.fetch_staff_detail(ctx, user)

    @staff.command(name='list', description='shows all staff registered name with the count')
    @permission(command_name="staff_list")
    async def staffs(self, ctx:commands.Context):
        if self.controller is not None:
            await self.controller.fetch_all_staffs(ctx)


    @strike.command(name='issue', description='Issue an infraction')
    @permission(command_name="strike_add")
    async def staffstrike(self, ctx: commands.Context, staff: discord.Member):
        if self.controller is not None:
            await self.controller.strike_staff(ctx, staff)

    @strike.command(name='remove', description='Remove an infraction')
    @permission(command_name="strike_remove")
    async def removestrike(self, ctx: commands.Context, infraction_id: str):
        if self.controller is not None:
            await self.controller.remove_strike_staff(ctx, int(infraction_id))

    @strike.command(name="edit", description="Edit a reason of a infraction")
    @permission(command_name="strike_edit")
    async def strike_edit(self, ctx: commands.Context, infraction_id: str, new_reason: str):
        if self.controller is not None:
            await self.controller.edit_strike(ctx, int(infraction_id), new_reason)

    @staff.command(name='edit', description='edits a staff data')
    @permission(command_name="staff_edit")
    async def EditStaff(self, ctx: commands.Context, staff_id: str,name: str = None, joined_on: str = None, timezone: str = None,responsibility: str = None):
        if self.controller is not None:
            await self.controller.edit_staff(ctx, int(staff_id), name, joined_on, timezone, responsibility)

    @staff.command(name="self_edit", description="edits your staff data")
    @permission(command_name="staff_self_edit")
    async def self_edit_staff_data(self, ctx: commands.Context, name: str=None, timezone: str=None):
        if self.controller is not None:
            if not bool(re.fullmatch(r'[+-](0?\d|1[0-4]):[0-5]\d', timezone)):
                await ctx.reply(embed=simple_embed("Invalid Timezone Format! Timezone should be given by `+05:30` or Similar", 'cross'))
                return 
            await self.controller.edit_staff(ctx, ctx.author.id, name, None, timezone, None)

    @strike.command(name='show', description='shows infractions for a concurrent staff')
    @permission(command_name="strike_show")
    async def strikes(self, ctx: commands.Context, staff: discord.Member):
        if self.controller is not None:
            await self.controller.list_strikes(ctx, staff)

    @staff.command(name='add', description='Adds a member to staff_data')
    @permission(command_name="staff_add")
    async def add_staff(self, ctx: commands.Context, staff: discord.Member):
        if self.controller is not None:
            await self.controller.add_staff(ctx, staff)

    @staff.command(name='add_batch', description='Adds a batch of staffs to staff_data')
    @permission(command_name="staff_add_batch")
    async def add_staffs_batch(self, ctx: commands.Context, staffs: str):
        await ctx.defer()
        if self.controller is not None:
            await self.controller.add_staff_batch(ctx, staffs)


    @staff.command(name='remove', description='Removes a member from staff_data')
    @permission(command_name="staff_remove")
    async def remove_staff(self, ctx: commands.Context, staff: discord.Member, reason: str):
        if self.controller is not None:
            await self.controller.remove_staff(ctx, staff, reason)


    @staff.command(name='remove_raw', description='Removes a member from staff_data')
    @permission(command_name="staff_remove_raw")
    async def remove_staff_raw(self, ctx: commands.Context, staff: str, reason: str):
        if self.controller is not None:
            await self.controller.remove_staff(ctx, int(staff), reason)


    @staff.command(name='roles', description='Returns all staff roles')
    @permission(command_name="staff_roles")
    async def get_all_staff_roles(self, ctx: commands.Context):
        if self.controller is not None:
            await self.controller.get_all_staff_roles(ctx)

    @dev.command(name='staff_update', description='updates all staff details')
    @permission(command_name="dev_staff_update", restrict=True)
    async def update_all_staffs(self, ctx: commands.Context):
        await ctx.defer()
        if self.controller is not None:
            await self.controller.update_all_staffs(ctx)

    @loa.command(name='add', description='Assigns a staff leave')
    @permission(command_name="loa_add")
    async def add_loa(self, ctx: commands.Context, staff: discord.Member, *, reason: str):
        if self.controller is not None:
            await self.controller.add_loa(ctx, staff, reason)

    @loa.command(name='delete', description='Delete an LOA entry from the database')
    @permission(command_name="loa_delete")
    async def loa_delete(self, ctx: commands.Context, leave_id: int):
        if self.controller is not None:
            await self.controller.loa_delete(ctx, leave_id)



    @loa.command(name='remove', description='Removes a staff leave')
    @permission(command_name="loa_remove")
    async def remove_loa(self, ctx: commands.Context, staff: discord.Member):
        if self.controller is not None:
            await self.controller.remove_loa(ctx, staff)

    @loa.command(name="show", description="List all LOA for a particular staff")
    @permission(command_name="loa_show")
    async def show_loa(self, ctx: commands.Context, staff: discord.Member=None):
        if staff is None:
            current_staff = ctx.author
        else:
            current_staff = staff

        if self.controller is not None and isinstance(current_staff, discord.Member):
            await self.controller.list_loa(ctx, current_staff)

    @loa.command(name="request", description="Request LOA")
    @permission(command_name="loa_request")
    async def request_loa(self, ctx: commands.Context):
        if self.controller is not None:
            await self.controller.request_loa(ctx)


    @rank.command(name='promote', description='Promotes a staff to upper rank')
    @permission(command_name="rank_promote")
    async def promote(self, ctx: commands.Context, staff: discord.Member, * ,reason: str):
        await ctx.defer()
        if self.controller is not None:
            await self.controller.update_staff(ctx, staff, reason, "promotion")

    
    @rank.command(name='promote_batch', description='Promotes a batch of staffs to upper rank')
    @permission(command_name="rank_promote_batch")
    async def promote_batch(self, ctx: commands.Context, *, query: str):
        await ctx.defer()
        if self.controller is not None:
            await self.controller.update_staff_batch(ctx, query, "promotion")


    @rank.command(name='demote', description='Demotes a staff to lower rank')
    @permission(command_name="rank_demote")
    async def demote(self, ctx: commands.Context, staff: discord.Member, *, reason: str):
        await ctx.defer()
        if self.controller is not None:
            await self.controller.update_staff(ctx, staff, reason, "demotion")

    @quota.command(name="add", description="Adds a staff quota to check by")
    @permission(command_name="quota_add")
    async def add_quota(self, ctx: commands.Context, quota_role: discord.Role, minimum_ms: int, minimum_msg: int, on_quota_pass: OnQuotaEvent, on_quota_fail: OnQuotaEvent, check_by: QuotaCheckBy):
        if self.controller is not None:
            await self.controller.add_staff_quota(ctx, quota_role, minimum_ms, minimum_msg, on_quota_pass, on_quota_fail, check_by)


    @quota.command(name="list", description="List all defined quotas for this server")
    @permission(command_name="quota_list")
    async def list_quota(self, ctx: commands.Context):
        if self.controller is not None:
            await self.controller.fetch_staff_quota(ctx)


    @quota.command(name="remove", description="Remove a defined quota by its ID")
    @permission(command_name="quota_remove")
    async def remove_quota(self, ctx: commands.Context, quota_id: str):
        if self.controller is not None:
            await self.controller.remove_staff_quota(ctx, quota_id)

    @quota.command(name="check", description="Check quota for a given staff")
    @permission(command_name="quota_check")
    async def check_quota(self, ctx: commands.Context, staff: discord.Member = None):
        staff_member = staff or ctx.author
        if self.controller is not None:
            await self.controller.check_staff_quota(ctx, staff_member)


    @quota.command(name="evaluate", description="Evaluates Staff quota and updates the results")
    @permission(command_name="quota_evaluate")
    async def evaluate_staff_quota(self, ctx: commands.Context, role: discord.Role):
        if self.controller is not None:
            await self.controller.evaluate_staff_quota(ctx, role)
        
    @staff_role.command(name="remove", description="Removes a staff role from the database")
    @permission(command_name="staff_role_remove")
    async def remove_role(self, ctx: commands.Context, role: discord.Role):
        if self.controller is not None:
            await self.controller.remove_role(ctx, role.id)


    @staff_role.command(name="remove_raw", description="Removes a staff role from the database")
    @permission(command_name="staff_role_remove_raw")
    async def remove_role_raw(self, ctx: commands.Context, role: str):
        if self.controller is not None:
            await self.controller.remove_role(ctx, int(role))



async def setup(bot):
    cog = LilyManagement(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()