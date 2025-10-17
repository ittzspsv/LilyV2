from discord.ext import commands

import LilyModeration.sLilyModeration as mLily
import LilyResponse.sLilyResponse as aiLily
import Config.sBotDetails as Config
import LilyManagement.sLilyStaffManagement as LSM

from LilyRulesets.sLilyRulesets import PermissionEvaluator

class LilyResponse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.hybrid_command(name='enable_response', description='sets auto response feature to boolean value 0 and 1')
    #feature_cache for Autoresponse, ChannelResponse = 1
    async def set_response_feature(self, ctx:commands.Context, feature_cache:str="0"):
        try:
            with open("src/Config/BotFeatures.txt", "w") as fileptr:
                fileptr.write(feature_cache)
                fileptr.close()
                await ctx.send(embed=mLily.SimpleEmbed(f"AutoResponse Feature set to boolean {feature_cache}"))
        except Exception as e:
            await ctx.send(mLily.SimpleEmbed(f'Exception {e}'))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.hybrid_command(name='update_response', description='updates auto response feature for the bot')
    async def update_response(self, ctx:commands.Context):
        success = aiLily.update_response()
        if success:
            await ctx.send("Successfully Updated Response")

async def setup(bot):
    await bot.add_cog(LilyResponse(bot))
