from discord.ext import commands
from core.utils.embeds.sLilyEmbed import simple_embed
from core.features.blox_fruits.routes.blox_fruits_router import BloxFruitsController
from core.database.integrations.blox_fruits import BloxFruitsDatabase

import discord
import json
import core.utils.sFruitImageDownloader as FID
import re

from typing import Optional

from core.features.permissions.lily_permissions import permission

class LilyBloxFruits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: Optional[BloxFruitsDatabase] = None
        self.controller: Optional[BloxFruitsController] = None

    async def on_load(self):
        self.db = await BloxFruitsDatabase.connect("storage/configs/ValueData.db")
        self.controller = BloxFruitsController(self.db)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
              return

        #await LBFC.MessageEvaluate(self.bot, message)
        if self.controller is not None:
            await self.controller.on_message(message, self.bot)

    @commands.hybrid_group()
    async def bloxfruits(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Blox Fruits Command Hierarchy!"))

    @bloxfruits.command(name='update_image', description='updates an image of blox fruits')
    @permission(command_name="update_image", restrict=True)
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

    @bloxfruits.command(name='update_value', description='updates an value of an item in blox fruits')
    @permission(command_name="update_value", restrict=True)
    async def UpdateValue(
        self,
        ctx: commands.Context,
        name: str,
        physical_value: Optional[str] = None,
        permanent_value: Optional[str] = None,
        physical_demand: Optional[str] = None,
        permanent_demand: Optional[str] = None,
        demand_type: Optional[str] = None,
        permanent_demand_type: Optional[str] = None,
        category: Optional[str] = None,
        aliases: Optional[str] = None,
        icon_url: Optional[str] = None,
    ):
        if self.db is None:
            return

        await ctx.defer()

        def parse_number(value):
            if value is None:
                return None
            if isinstance(value, int):
                return value

            value = str(value).replace(",", "").strip().lower()
            match = re.match(r"(\d+\.?\d*)([kmb]?)", value)
            if not match:
                return None

            number, suffix = match.groups()
            multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
            return int(float(number) * multiplier.get(suffix, 1))

        try:
            row = await self.db.fetch_one(
                "SELECT * FROM BF_ItemValues WHERE name = ?",
                (name.title(),)
            )

            if not row:
                await ctx.send(f"No item found with name `{name}`.")
                return

            (
                _name,
                current_physical_value,
                current_permanent_value,
                current_physical_demand,
                current_permanent_demand,
                current_demand_type,
                current_permanent_demand_type,
                current_category,
                current_aliases,
                current_icon_url,
            ) = row

            physical_value = parse_number(physical_value)
            permanent_value = parse_number(permanent_value)

            if aliases is not None:
                alias_list = [a.strip() for a in aliases.split(",") if a.strip()]
                aliases = json.dumps(alias_list)
            else:
                aliases = current_aliases

            update_fields = {
                "physical_value": physical_value or current_physical_value,
                "permanent_value": permanent_value or current_permanent_value,
                "physical_demand": physical_demand or current_physical_demand,
                "permanent_demand": permanent_demand or current_permanent_demand,
                "demand_type": demand_type or current_demand_type,
                "permanent_demand_type": permanent_demand_type or current_permanent_demand_type,
                "category": category or current_category,
                "aliases": aliases,
                "icon_url": icon_url or current_icon_url,
            }

            set_clause = ", ".join(f"{k} = ?" for k in update_fields)
            values = list(update_fields.values()) + [name.title()]

            await self.db.execute(
                f"UPDATE BF_ItemValues SET {set_clause} WHERE name = ?",
                tuple(values)
            )

            await self.db.load_cache()

            await ctx.send(f"Updated `{name}` successfully.")

        except Exception as e:
            print(f"[UpdateValue] {e}")
            await ctx.send("An error occurred while updating the item.")

async def setup(bot):
    cog = LilyBloxFruits(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()