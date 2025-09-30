from discord.ext import commands
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Values.sStockValueJSON as StockValueJSON
import LilyLogging.sLilyLogging as LilyLogging

import Config.sBotDetails as Config

import ui.sComboImageGenerator as CIG
import Config.sValueConfig as VC
import Misc.sFruitImageDownloader as FID

import discord
import ast
import io
import os
import json

class LilyBloxFruits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='update_image_blox_fruits', description='reloads combo data if any changes is done')
    async def UpdateImageBloxFruits(self, ctx: commands.Context, name: str=""):
            cursor = await VC.vdb.execute(
                "SELECT icon_url FROM BF_ItemValues WHERE name = ?", 
                (name,)
            )
            row = await cursor.fetchone()
            await cursor.close()

            if row:
                url = row[0]
                result = await FID.DownloadImage(name, "src/ui/fruit_icons", url)
                if result:
                    await ctx.send(f"Image '{name}' updated successfully!")
            else:
                await ctx.send("Row Not Found Exception")

async def setup(bot):
    await bot.add_cog(LilyBloxFruits(bot))