from discord.ext import commands
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Values.sStockValueJSON as StockValueJSON
import LilyLogging.sLilyLogging as LilyLogging

import Combo.LilyComboManager as LCM
import Config.sBotDetails as Config

import ui.sComboImageGenerator as CIG

import discord
import ast
import io
import os
import json

class LilyBloxFruits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='combo_lookup_by_id', description='looks for a specific combo, ref=id')
    async def combo_lookup_by_id(self, ctx:commands.Context, id:str=""):
                        try:
                            combo = LCM.ComboLookupByID(int(id))

                            id = combo['id']
                            user_id = combo['user_id']
                            combo_data = combo['combo_data']
                            Item_List = {}
                            if combo.get("Fruit"):
                                Item_List[combo["Fruit"]] = "fruit_icons"
                            if combo.get("Sword"):
                                Item_List[combo["Sword"]] = "sword_icons"
                            if combo.get("Fighting Style"):
                                Item_List[combo["Fighting Style"]] = "fighting_styles"
                            if combo.get("Gun"):
                                Item_List[combo["Gun"]] = "gun_icons"
                            Item_Icon_List = []
                            
                            for key, value in Item_List.items():
                                if key and key.strip():
                                    imod = key.replace(" ", "_")
                                    icon = f'src/ui/{value}/{imod}.png'
                                    Item_Icon_List.append(icon)

                            combo_text = ""
                            #Parsing Combo Texts
                            for base, nested in ast.literal_eval(combo_data):
                                combo_ = " ".join(nested)
                                name_formatted = base.title()
                                combo_text += f"- **{name_formatted}: {combo_}**\n"

                            img = CIG.CreateBaseBuildIcon(Item_Icon_List)
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='PNG')
                            img_byte_arr.seek(0)

                            embeds = []
                            imgfile = discord.File(img_byte_arr, filename="image.png")
                            embed = discord.Embed(title="__BUILD__",colour=0xf5008f)

                            embed.set_author(name=f"{Config.server_name} Combos")
                            embed.set_image(url="attachment://image.png")

                            embeds.append(embed)

                            divider_text = "<:divider:1374032878760886342>"
                            divider_texts = ""
                            for i in range(0, 22):
                                divider_texts += divider_text

                            embed = discord.Embed(title=f"__COMBO__",
                            description=combo_text,
                            colour=0xf5008f)
                            
                            embed.add_field(name="",
                                value=divider_texts,
                                inline=False)
                            
                            embed.add_field(name="",
                                value=f"Combo ID : {id} \nCombo By <@{user_id}>",
                                inline=False)
                            
                            embeds.append(embed)


                            await ctx.send(file=imgfile, embeds=embeds)
                        except Exception as e:
                            await ctx.send(e)

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles + Config.StaffManagerRoles + Config.TrustedStaffRoles)
    @commands.hybrid_command(name='delete_combo_by_id', description='deletes a combo, ref=id')
    async def delete_combo_by_id(self, ctx:commands.Context, id:str=""):
        try:
            LCM.DeleteComboByID(int(id))
            await ctx.send("Deleted Successfully")
        except Exception as e:
            await ctx.send(e)

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='updatevalue', description='updates the given fruit value with str:cache')
    async def update_value(self, ctx: commands.Context, *, update_cache: str = ""):
        user_message = update_cache.lower()
        message_parsed = user_message.split()

        fields = {
            "name": None,
            "physical_value": None,
            "permanent_value": None,
            "physical_demand": None,
            "permanent_demand": None,
            "demand_type": None,
            "permanent_demand_type": None
        }

        current_key = None
        for word in message_parsed:
            if word in fields:
                current_key = word
                fields[current_key] = ""
            elif current_key is not None:
                if fields[current_key]:
                    fields[current_key] += " "
                fields[current_key] += word

        if not fields["name"] or not fields["name"].strip():
            await ctx.send("Name is required for update.")
            return

        fields["name"] = fields["name"].title()
        fruit_data = StockValueJSON.fetch_fruit_details(fields["name"])

        if not fruit_data:
            await ctx.send(f"Could not find fruit named **{fields['name']}**.")
            return

        if fields["demand_type"]:
            fields["demand_type"] = fields["demand_type"].title()
        if fields["permanent_demand_type"]:
            fields["permanent_demand_type"] = fields["permanent_demand_type"].title()

        fields["physical_value"] = fields["physical_value"] or fruit_data.get("physical_value")
        fields["permanent_value"] = fields["permanent_value"] or fruit_data.get("permanent_value")
        fields["physical_demand"] = fields["physical_demand"] or fruit_data.get("physical_demand")
        fields["permanent_demand"] = fields["permanent_demand"] or fruit_data.get("permanent_demand")
        fields["demand_type"] = fields["demand_type"] or fruit_data.get("demand_type")
        fields["permanent_demand_type"] = fields["permanent_demand_type"] or fruit_data.get("permanent_demand_type")

        StockValueJSON.update_fruit_data(
            name=fields["name"],
            physical_value=fields["physical_value"],
            permanent_value=fields["permanent_value"],
            physical_demand=fields["physical_demand"],
            permanent_demand=fields["permanent_demand"],
            demand_type=fields["demand_type"],
            permanent_demand_type=fields["permanent_demand_type"]
        )

        await ctx.send(f"Updated value for **{fields['name']}**")
        await LilyLogging.WriteLog(ctx, ctx.author.id, f"Updated {fields['name']} values.")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='fetch_combo_file', description='updates the given fruit value with str:cache')
    async def fetch_combo_file(self, ctx: commands.Context):
        file_path = "storage/common/Comboes/Comboes.csv"
        try:
            await ctx.send("Here is your CSV file:", file=discord.File(file_path))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='upload_combo_csv', description='updates the given fruit value with str:cache')
    async def upload_combo_csv(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("Please append an csv file formatter")
            return
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".csv"):
            await ctx.send("Please append an csv file formatter")
            return
        save_path = "storage/common/Comboes/Comboes.csv"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            await attachment.save(save_path)
            await ctx.send(f"CSV File Replaced.")
        except Exception as e:
            await ctx.send(f"Exception {e}")


    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='modify_combo_config', description='updates the combo config with desired input attached')
    async def modify_combo_config(ctx, file_name: str):
        dir_path = "src/Config/JSONData"
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

            await ctx.send(f"Successfully updated Combo Contents")
        except Exception as e:
            await ctx.send(f"Exception {e}")
async def setup(bot):
    await bot.add_cog(LilyBloxFruits(bot))