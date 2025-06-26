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
    @commands.hybrid_command(name='upload_img', description='updates the gag image with desired input attached')
    async def upload_img(self, ctx, file_name: str):
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
async def setup(bot):
    await bot.add_cog(LilyGAG(bot))