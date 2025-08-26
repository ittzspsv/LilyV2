import discord
from discord.ext import commands
from LilyRulesets.sLilyRulesets import PermissionEvaluator

import Config.sBotDetails as Config
import json
import os
import LilyGAG.sLilyGAGCore as GAGCore


class LilyGAG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='modify_gag_config', description='updates the gag config with desired input attached')
    async def modify_gag_config(self, ctx, file_name: str):
        dir_path = "src/LilyGAG/data"
        full_path = os.path.join(dir_path, file_name)
        if not os.path.isfile(full_path):
            await ctx.send(f"File {file_name} not found")
            return
        if not ctx.message.attachments:
            await ctx.send("Please attach a .json file to replace the contents.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".json"):
            await ctx.send("Invalid file formatter.")
            return

        try:
            data = await attachment.read()
            new_content = json.loads(data.decode())

            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(new_content, f, indent=4)
            
            GAGCore.UpdateData()
            await ctx.send(f"Successfully updated Combo Contents")
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='gag_upload_png', description='updates the gag image with desired input attached')
    async def gag_upload_img(self, ctx, file_name: str):
        if not ctx.message.attachments:
            await ctx.send("Please attach file formats")
            return

        attachment = ctx.message.attachments[0]
        ext = attachment.filename.lower().split('.')[-1]

        if ext not in ["png", "webp"]:
            await ctx.send("File format exception.  only .png and .webp allowed")
            return

        if not os.path.exists("src/ui/GAG"):
            os.makedirs("src/ui/GAG")

        save_path = os.path.join("src/ui/GAG", f"{file_name}.{ext}")
        await attachment.save(save_path)

        await ctx.reply(f"Success")
    
    @commands.hybrid_command(name='pet_weight_by_age', description='Relation between pet weight and age')
    async def pet_weight_ratio(self, ctx:commands.Context, weight:float, age:float):
        WeightRatio = GAGCore.PetWeightChart(age, weight)
        
        classification = ""
        classification_mapping = {
                    "Small": (0.7, 1.4),
                    "Normal": (1.4, 3.9),
                    "Semi Huge": (3.9, 4.9),
                    "Huge": (4.9, 7.9),
                    "Titanic": (7.9, 8.9),
                    "Godly": (8.9, 11)
                }

        value = float(GAGCore.PetWeightChart(age, weight)[0])
        for category, (low, high) in classification_mapping.items():
                if low <= value < high:
                    classification = category
                    break

        embed = discord.Embed(title=f"CLASSIFICATION : {classification.upper()}",
                      colour=0xd800f5)

        embed.set_author(name="Pet Age  / Weight Ratio")

        embed.add_field(name="Current Weight",
                        value=f"{weight}",
                        inline=True)
        embed.add_field(name=f"Current Age",
                        value=age,
                        inline=True)
        embed.add_field(name="Weight at Age 1",
                        value=f"{WeightRatio[0]}kg",
                        inline=False)
        embed.add_field(name="Weight at Age 100",
                        value=f"{WeightRatio[-1]}kg",
                        inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LilyGAG(bot))