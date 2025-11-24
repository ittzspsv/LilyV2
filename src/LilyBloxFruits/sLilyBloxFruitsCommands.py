from discord.ext import commands
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Values.sStockValueJSON as StockValueJSON
import LilyLogging.sLilyLogging as LilyLogging
import LilyManagement.sLilyStaffManagement as LSM
import re

import Combo.LilyComboManager as LCM
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

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='update_image_blox_fruits', description='updates an image of blox fruits')
    async def UpdateImageBloxFruits(self, ctx: commands.Context, name: str = ""):
        parser = [n.strip() for n in name.split(",") if n.strip()]

        if not parser:
            return await ctx.send("Please provide at least one fruit name.")

        results = []

        for fruit_name in parser:
            cursor = await VC.vdb.execute(
                "SELECT icon_url FROM BF_ItemValues WHERE name = ?",
                (fruit_name,)
            )
            row = await cursor.fetchone()
            await cursor.close()

            if row:
                url = row[0]
                result = await FID.DownloadImage(fruit_name, "src/ui/fruit_icons", url)

                if result:
                    results.append(f"Image updated for **{fruit_name}**")
                else:
                    results.append(f"Failed downloading image for **{fruit_name}**")
            else:
                results.append(f"`{fruit_name}` not found in database.")

        await ctx.send("\n".join(results))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('ValueTeam', 'Developer')))
    @commands.hybrid_command(name='update_bf_value', description='updates an value of an item in blox fruits')
    async def UpdateValue(self, ctx: commands.Context,name: str,physical_value: str = None,permanent_value: str = None,physical_demand: str = None,permanent_demand: str = None,demand_type: str = None,permanent_demand_type: str = None,category: str = None,aliases: str = None,icon_url: str = None):
        def parse_number(value):
            if value is None:
                return None
            if isinstance(value, int):
                return value
            value = str(value).replace(",", "").strip().lower()
            match = re.match(r"(\d+\.?\d*)([kmb]?)", value)
            if not match:
                return
            number, suffix = match.groups()
            number = float(number)
            multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
            return int(number * multiplier.get(suffix, 1))
        try:
            cursor = await VC.vdb.execute("SELECT * FROM BF_ItemValues WHERE name = ?", (name.title(),))
            row = await cursor.fetchone()
            if not row:
                await ctx.send(f"No item found with name {name}.")
                return

            columns = [d[0] for d in cursor.description]
            current_values = dict(zip(columns, row))

            physical_value = parse_number(physical_value)
            permanent_value = parse_number(permanent_value)

            if aliases is not None:
                alias_list = [alias.strip() for alias in aliases.split(",") if alias.strip()]
                aliases_json = json.dumps(alias_list)
            else:
                aliases_json = current_values["aliases"]

            update_values = {
                "physical_value": physical_value if physical_value is not None else current_values["physical_value"],
                "permanent_value": permanent_value if permanent_value is not None else current_values["permanent_value"],
                "physical_demand": physical_demand if physical_demand is not None else current_values["physical_demand"],
                "permanent_demand": permanent_demand if permanent_demand is not None else current_values["permanent_demand"],
                "demand_type": demand_type if demand_type is not None else current_values["demand_type"],
                "permanent_demand_type": permanent_demand_type if permanent_demand_type is not None else current_values["permanent_demand_type"],
                "category": category if category is not None else current_values["category"],
                "aliases": aliases_json,
                "icon_url": icon_url if icon_url is not None else current_values["icon_url"],
            }

            set_clause = ", ".join([f"{col} = ?" for col in update_values])
            values = list(update_values.values())
            values.append(name)

            query = f"UPDATE BF_ItemValues SET {set_clause} WHERE name = ?"
            await VC.vdb.execute(query, values)
            await VC.vdb.commit()

            await ctx.send(f"Item {name} updated successfully.")
        except Exception as e:
            print(e)
            await ctx.send(f"An error occurred: {e}")

async def setup(bot):
    await bot.add_cog(LilyBloxFruits(bot))