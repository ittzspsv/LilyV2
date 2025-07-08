from discord.ext import commands
import discord
import io
import LilyLeveling.sLilyLevelingCore as LilyLevelCore
from ui.sWantedPoster import PosterGeneration
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Config.sBotDetails as Config
import os
import json


class LilyLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='profile', description='Generates a wanted poster image')
    async def profile(self, ctx: commands.Context, member:discord.Member=None):
            try:
                message = await ctx.reply("Thinking......")
                if not member:
                    input_image = ctx.author.display_avatar.url
                else:
                    input_image = member.display_avatar.url
                name, description, role, current_level, bounty = await LilyLevelCore.FetchProfileDetails(ctx, member)
                poster = await PosterGeneration(input_image, name, "", bounty, current_level, description, role)

                buffer = io.BytesIO()
                poster.save(buffer, format="PNG")
                buffer.seek(0)

                await message.edit(content=None, attachments=[discord.File(buffer, filename="wanted.png")])

            except Exception as e:
                await message.edit(content=f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='set_level', description='sets a level for user')
    async def set_level(self, ctx:commands.Context, member:discord.Member, level:int):
        await LilyLevelCore.SetLevel(ctx, member, level)

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='add_bounty', description='adds a bounty for user')
    async def add_bounty(self, ctx:commands.Context, member:discord.Member, amount:int):
        await LilyLevelCore.AddCoins(ctx, member, amount)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='set_profile', description='updates or adds a new profile')
    async def set_profile(self, ctx:commands.Context, name:str, role:str,* ,description:str):
        await LilyLevelCore.UpdateProfile(ctx, name, role,description)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='set_profile_for', description='updates or adds a new profile for a given member')
    async def set_profile_for(self, ctx:commands.Context, member:discord.Member,name:str, role:str,* ,description:str):
        await LilyLevelCore.UpdateProfileFor(ctx, member,name,role ,description)
        
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
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
async def setup(bot):
    await bot.add_cog(LilyLeveling(bot))