from discord.ext import commands
import discord
import io
import LilyLeveling.sLilyLevelingCore as LilyLevelCore
from ui.sWantedPoster import PosterGeneration
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Config.sBotDetails as Config
import ui.sProfileCardGenerator as PCG
import os
import json


class LilyLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        await LilyLevelCore.SetLevel(ctx, member, level)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='update_leveling_config', description='updates or adds a new profile for a given member')
    async def update_leveling_config(self, ctx: commands.Context):
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

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.hybrid_command(name='leaderboard', description='Show Top 10 Leaderboard')
    async def leaderboard(self, ctx: commands.Context):
         await ctx.defer()
         await LilyLevelCore.FetchLeaderBoard(ctx)
async def setup(bot):
    await bot.add_cog(LilyLeveling(bot))