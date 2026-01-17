from discord.ext import commands
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Config.sValueConfig as LilyConfig
from discord import File
import LilyManagement.sLilyStaffManagement as LSM
import LilyModeration.sLilyModeration as mLily
import re

import Combo.LilyComboManager as LCM
import Misc.sLilyComponentV2 as CV2
import LilyLogging.sLilyLogging as LilyLogging

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
        await ctx.defer()
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

            updated_only = {
                "physical_value": physical_value,
                "permanent_value": permanent_value,
                "physical_demand": physical_demand,
                "permanent_demand": permanent_demand,
                "demand_type": demand_type,
                "permanent_demand_type": permanent_demand_type,
                "category": category,
                "aliases": aliases_json,
                "icon_url": icon_url,
            }

            updated_only = {k: v for k, v in updated_only.items() if v is not None}

            set_clause = ", ".join([f"{col} = ?" for col in update_values])
            values = list(update_values.values())
            values.append(name)

            query = f"UPDATE BF_ItemValues SET {set_clause} WHERE name = ?"
            await VC.vdb.execute(query, values)
            await VC.vdb.commit()

            await LilyLogging.LogValueAction(ctx, ctx.author, updated_only)

            await ctx.send(f"Item {name} updated successfully.")
        except Exception as e:
            print(e)
            await ctx.send(f"An error occurred: {e}")

    @commands.hybrid_command(name='add_combo', description='Adds a combo to the database')
    async def add_combo(self, ctx: commands.Context, *, combo: str = None):
        await ctx.defer()
        if not combo:
            await ctx.reply("Please provide a combo string to add.")
            return

        try:
            cursor = await LilyConfig.cdb.execute(
                "SELECT bf_combo_channel_id FROM ConfigData WHERE guild_id = ?", (ctx.guild.id,)
            )
            row = await cursor.fetchone()
        except Exception:
            await ctx.reply("Database error occurred.")
            return

        if not row or ctx.channel.id != row[0]:
            await ctx.reply("Combos can only be added in the configured combo channel.")
            return

        try:
            message_refined = " ".join(line.strip() for line in combo.splitlines() if line.strip()).lower()
            parsed_build, combo_data = await LCM.ComboPatternParser(message_refined)
            data = (parsed_build, combo_data)
        except Exception as e:
            await ctx.reply(f"Parsing failed: {e}")
            return

        try:
            if await LCM.ValidComboDataType(data):
                cid = await LCM.RegisterCombo(str(ctx.author.id), parsed_build, combo_data)
                combo = await LCM.ComboLookupByID(cid)

                combo_data_text = combo.get('combo_data', '[]')
                Item_List = {}
                for key_type in ["fruit", "sword", "fighting_style", "gun"]:
                    if combo.get(key_type):
                        mapping = {
                            "fruit": "fruit_icons",
                            "sword": "sword_icons",
                            "fighting_style": "fighting_styles",
                            "gun": "gun_icons"
                        }
                        Item_List[combo[key_type]] = mapping[key_type]

                Item_Icon_List = [
                    f'src/ui/{value}/{key.replace(" ", "_")}.png'
                    for key, value in Item_List.items() if key and key.strip()
                ]

                combo_text = ""
                for base, nested in ast.literal_eval(combo_data_text):
                    combo_ = " ".join(nested)
                    combo_text += f"{base.title()}: {combo_}\n"
                name_raw = ctx.author.name or "Unknown"
                name = re.sub(r'[^A-Za-z ]+', '', name_raw)
                img = CIG.CreateBaseBuildIcon(Item_Icon_List, combo_text=combo_text, rating_text=f'{combo.get("rating", "0")}/10', combo_id=str(combo['combo_id']), combo_by=name)
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                imgfile = File(img_byte_arr, filename="image.png")
                await ctx.reply(content='Success! Here is the preview of your combo', file=imgfile)
            else:
                await ctx.reply("Error parsing combo structure.")
        except Exception as e:
            await ctx.reply(f"Unexpected error: {e}")

    @commands.hybrid_command(name='find_combo', description='Finds a combo in the database')
    async def find_combo(self, ctx: commands.Context, *, build: str = None):
        await ctx.defer()
        if not build:
            await ctx.reply("Please provide a combo name to search.")
            return

        try:
            combo_obj = await LCM.ComboLookup(build.lower())
            if not combo_obj:
                await ctx.reply("No matching combo found.")
                return

            combo_data_text = combo_obj.get('combo_data', '[]')
            Item_List = {}
            for key_type in ["fruit", "sword", "fighting_style", "gun"]:
                if combo_obj.get(key_type):
                    mapping = {
                        "fruit": "fruit_icons",
                        "sword": "sword_icons",
                        "fighting_style": "fighting_styles",
                        "gun": "gun_icons"
                    }
                    Item_List[combo_obj[key_type]] = mapping[key_type]

            Item_Icon_List = [
                f'src/ui/{value}/{key.replace(" ", "_")}.png'
                for key, value in Item_List.items() if key and key.strip()
            ]

            combo_text = ""
            for base, nested in ast.literal_eval(combo_data_text):
                combo_ = " ".join(nested)
                combo_text += f"{base.title()}: {combo_}\n"

            combo_author_id = combo_obj.get("combo_author")
            combo_by = None

            if combo_author_id:
                combo_by = ctx.guild.get_member(int(combo_author_id))
                if combo_by is None:
                            try:
                                combo_by = await ctx.guild.fetch_member(int(combo_author_id))
                            except discord.NotFound:
                                    combo_by = None

            name_raw = combo_by.name if combo_by else "Unknown"
            name = re.sub(r'[^A-Za-z ]+', '', name_raw)
            img = CIG.CreateBaseBuildIcon(Item_Icon_List, combo_text=combo_text, rating_text=f"{combo_obj.get('rating', '0')}/10", combo_id=str(combo_obj['combo_id']), combo_by=name)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            imgfile = File(img_byte_arr, filename="image.png")
            view = CV2.RatingComponent(ctx.author, combo_obj['combo_id'])
            await ctx.reply(file=imgfile, view=view)
        except Exception as e:
            await ctx.reply(f"Exception: {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.hybrid_command(name='delete_combo', description='deletes a combo by its id')
    async def delete_combo(self, ctx: commands.Context, combo_id: str):
        try:
            row = await LCM.DeleteComboByID(combo_id)
            if row:
                await ctx.reply(embed=mLily.SimpleEmbed(f"Successfully deleted combo id {row}"))
            else:
                await ctx.reply(embed=mLily.SimpleEmbed(f"Cannot find the combo ID", 'cross'))
        except Exception as e:
            await ctx.reply(embed=mLily.SimpleEmbed(f"Exception Occured {e}", 'cross'))
    
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.hybrid_command(name='combo_lookup_by_id', description='Lookup a combo by its id')
    async def combo_lookup_by_id(self, ctx: commands.Context, combo_id: str):
        await ctx.defer()
        try:
            combo_obj = await LCM.ComboLookupByID(combo_id)
            if not combo_obj:
                await ctx.reply("No matching combo found.")
                return

            combo_data_text = combo_obj.get('combo_data', '[]')
            Item_List = {}
            for key_type in ["fruit", "sword", "fighting_style", "gun"]:
                if combo_obj.get(key_type):
                    mapping = {
                        "fruit": "fruit_icons",
                        "sword": "sword_icons",
                        "fighting_style": "fighting_styles",
                        "gun": "gun_icons"
                    }
                    Item_List[combo_obj[key_type]] = mapping[key_type]

            Item_Icon_List = [
                f'src/ui/{value}/{key.replace(" ", "_")}.png'
                for key, value in Item_List.items() if key and key.strip()
            ]

            combo_text = ""
            for base, nested in ast.literal_eval(combo_data_text):
                combo_ = " ".join(nested)
                combo_text += f"{base.title()}: {combo_}\n"

            img = CIG.CreateBaseBuildIcon(Item_Icon_List, combo_text=combo_text)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            imgfile = File(img_byte_arr, filename="image.png")
            view = CV2.RatingComponent(ctx.author, combo_obj['combo_id'])
            await ctx.reply(file=imgfile, view=view)
        except Exception as e:
            await ctx.reply(f"Exception: {e}")

async def setup(bot):
    await bot.add_cog(LilyBloxFruits(bot))