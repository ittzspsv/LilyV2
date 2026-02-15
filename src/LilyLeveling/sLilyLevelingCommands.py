from discord.ext import commands, tasks
from enum import Enum
import discord
from datetime import timedelta
import LilyLeveling.sLilyLevelingCore as LilyLevelCore
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import os
import json
import asyncio
import Config.sValueConfig as VC


class LilyLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_reset_schedular.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await LilyLevelCore.initialize()


    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='level', description='Get Your Current leveling info')
    async def level(self, ctx: commands.Context, member:discord.Member=None):
            await ctx.defer()
            await LilyLevelCore.FetchLevelDetails(ctx, member)
    
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='profile', description='Get Your Profile Information')
    async def profile(self, ctx: commands.Context, member:discord.Member=None):
            await ctx.defer()
            await LilyLevelCore.FetchProfileDetails(ctx, member)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager')))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='set_level', description='sets a level for user')
    async def set_level(self, ctx:commands.Context, member:discord.Member, level:int):
        await ctx.defer()
        await LilyLevelCore.SetLevel(ctx, member, level)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='update_leveling_config', description='updates or adds a new profile for a given member')
    async def update_leveling_config(self, ctx: commands.Context):
        await ctx.defer()
        path = "src/LilyLeveling/LevelingConfig.json"
        if not ctx.message.attachments:
            return await ctx.send("Please attach a JSON file")

        attachment = ctx.message.attachments[0]

        if not attachment.filename.endswith(".json"):
            return await ctx.send("The attached file must be a .json file.")

        try:
            file_bytes = await attachment.read()
            config_data = json.loads(file_bytes.decode('utf-8'))

            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, "w", encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            LilyLevelCore.InitializeConfig()
            await ctx.send("Leveling config updated successfully.")
        except Exception as e:
            await ctx.send(f"Exception  {e}")


    class LeaderboardType(str, Enum):
        Total = "Total"
        Weekly = "Weekly"
        Daily = "Daily"
        Levels = "Levels"


    @commands.cooldown(rate=1, per=10, type=commands.BucketType.guild)
    @commands.hybrid_command(name='leaderboard', description='Show Top 10 Leaderboard')
    async def leaderboard(self, ctx: commands.Context, type: LeaderboardType):
         await ctx.defer()
         await LilyLevelCore.FetchLeaderBoard(ctx, type.value)

    async def daily_callback(self):
        if LilyLevelCore.ldb is None:
            return
        await LilyLevelCore.ldb.execute("UPDATE message_counts SET daily = 0")

    async def weekly_callback(self):
        if LilyLevelCore.ldb is None:
            return
        await LilyLevelCore.ldb.execute("UPDATE message_counts SET weekly = 0")

    @tasks.loop(minutes=5)
    async def message_reset_schedular(self):
        if LilyLevelCore.ldb is None:
            return
        now = LilyLevelCore.utcnow()
        cursor = await LilyLevelCore.ldb.execute("SELECT next_day_update, next_week_update FROM updates")
        row = await cursor.fetchone()
        if not row:
             return
        
        next_day, next_week = map(LilyLevelCore.parse, row)
        if next_day and now >= next_day:
            await self.daily_callback()
            await LilyLevelCore.ldb.execute(
                "UPDATE updates SET next_day_update = ?",
                (LilyLevelCore.iso(now + timedelta(days=1)),)
            )

        if next_week and now >= next_week:
            await self.weekly_callback()
            await LilyLevelCore.ldb.execute(
                "UPDATE updates SET next_week_update = ?",
                (LilyLevelCore.iso(now + timedelta(days=7)),)
            )

        await LilyLevelCore.ldb.commit()
         
async def setup(bot):
    await bot.add_cog(LilyLeveling(bot))