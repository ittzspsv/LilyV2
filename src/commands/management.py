import re
import discord

from discord.ext import commands, tasks
from discord import app_commands
from datetime import timedelta
from zoneinfo import available_timezones
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.features.permissions.lily_permissions import permission
from src.core.utils import lily_utility as LilyUtility
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.features.management.controller.lily_management_controller import LilyManagementController
from src.core.features.management.types.staff_management_types import *
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from src.core.features.management.components.staff_management_components import LOARequestView, RankConfigureModal


class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controller: Optional[LilyManagementController] = None
        self.db: Optional[BotGlobalsDatabaseAccess] = None
        self.scheduler = AsyncIOScheduler(timezone="UTC")

        self.message_reset_schedular.start()

    async def timezone_autocomplete(self, interaction: discord.Interaction, current):
        matches = [
            tz for tz in sorted(available_timezones())
            if current.lower() in tz.lower()
        ]
        return [
            app_commands.Choice(name=tz, value=tz)
            for tz in matches[:25]
        ]

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

        """ Start the cron schedular """
        self.scheduler.add_job(
            self._run_daily,
            CronTrigger(hour=23, minute=55),
            id="quota_daily",
            misfire_grace_time=3600,
            coalesce=True,
            replace_existing=True
        )
        self.scheduler.add_job(
            self._run_weekly,
            CronTrigger(day_of_week="sun", hour=23, minute=55),
            id="quota_weekly",
            misfire_grace_time=3600,
            coalesce=True,
            replace_existing=True
        )
        self.scheduler.add_job(
            self._run_monthly,
            CronTrigger(day="last", hour=23, minute=55),
            id="quota_monthly",
            misfire_grace_time=3600,
            coalesce=True,
            replace_existing=True
        )
        self.scheduler.start()

    async def cog_unload(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _run_daily(self):
        if self.bot.db is None or self.controller is None:
            return
        await self.controller.automatic_quota_evaluator("1d", self.bot)

    async def _run_weekly(self):
        if self.bot.db is None or self.controller is None:
            return
        await self.controller.automatic_quota_evaluator("7d", self.bot)

    async def _run_monthly(self):
        if self.bot.db is None or self.controller is None:
            return
        await self.controller.automatic_quota_evaluator("30d", self.bot)

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
    async def staff_data(self, ctx:commands.Context, user: discord.Member| discord.User | None = None):
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
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    @permission(command_name="staff_edit")
    async def EditStaff(self, ctx: commands.Context, staff_id: str, name: str , joined_on: str | None = None, timezone: str | None = None,responsibility: str | None = None):
        if self.controller is not None:
            await self.controller.edit_staff(ctx, int(staff_id), name, joined_on, timezone, responsibility)

    @staff.command(name="self_edit", description="edits your staff data")
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    @permission(command_name="staff_self_edit")
    async def self_edit_staff_data(self, ctx: commands.Context, name: str, timezone: str | None =None):
        if self.controller is not None:
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

    @staff.command(name='remove', description='Removes a member from staff_data')
    @permission(command_name="staff_remove")
    async def remove_staff(self, ctx: commands.Context, staff: discord.Member | discord.User, reason: str):
        if self.controller is not None:
            await self.controller.remove_staff(ctx, staff, reason)


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
    async def show_loa(self, ctx: commands.Context, staff: discord.Member | None =None):
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
    
    @rank.command(name='demote', description='Demotes a staff to lower rank')
    @permission(command_name="rank_demote")
    async def demote(self, ctx: commands.Context, staff: discord.Member, *, reason: str):
        await ctx.defer()
        if self.controller is not None:
            await self.controller.update_staff(ctx, staff, reason, "demotion")

    @quota.command(name="add", description="Adds a staff quota to check by")
    @permission(command_name="quota_add")
    async def add_quota(self, ctx: commands.Context, quota_role: discord.Role, minimum_ms: int, minimum_msg: int, check_by: QuotaCheckBy):
        if self.controller is not None:
            await self.controller.add_staff_quota(ctx, quota_role, minimum_ms, minimum_msg, check_by)

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
    async def check_quota(self, ctx: commands.Context, staff: discord.Member | None = None):
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

    @rank.command(name="configure", description="Configure staff ranks")
    @permission(command_name="rank_configure")
    async def rank_configure(self, ctx: commands.Context):
        if ctx.interaction is None:
            await ctx.reply(embed=simple_embed(
                "This command can only be used as a slash command."
            ,'cross'), delete_after=5)
            return
        interaction = ctx.interaction

        if interaction.guild is None:
            await ctx.reply(embed=simple_embed(
                "This command can only be used inside an guild."
            ,'cross'), delete_after=5)
            return

        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        try:
            """ Get all rank role ids for autofilling """
            staff_ranks: list[int] = await bot_db.get_staff_ranks(interaction.guild.id)
            await interaction.response.send_modal(RankConfigureModal(bot_db, staff_ranks))
        except Exception as e:
            print(e)

    @staff.command(name="coverage", description="get the timezone coverage of all the staffs")
    @permission(command_name="staff_coverage")
    async def staff_coverage(self, ctx: commands.Context):
        if self.controller is not None:
            await self.controller.get_staffs_timezone_coverage(ctx)


async def setup(bot):
    cog = LilyManagement(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()