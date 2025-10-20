from discord.ext import commands
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Values.sStockValueJSON as StockValueJSON
import LilyLogging.sLilyLogging as LilyLogging
import LilyManagement.sLilyStaffManagement as LSM

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

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager', 'Administrator')))
    @commands.hybrid_command(name='delete_combo_by_id', description='deletes a combo, ref=id')
    async def delete_combo_by_id(self, ctx:commands.Context, id:str=""):
        try:
            LCM.DeleteComboByID(int(id))
            await ctx.send("Deleted Successfully")
        except Exception as e:
            await ctx.send(e)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='fetch_combo_file', description='updates the given fruit value with str:cache')
    async def fetch_combo_file(self, ctx: commands.Context):
        file_path = "storage/common/Comboes/Comboes.csv"
        try:
            await ctx.send("Here is your CSV file:", file=discord.File(file_path))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
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
    
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='load_combo_data', description='reloads combo data if any changes is done')
    async def load_combo_data(self, ctx):
        try:
            LCM.LoadComboData()
            await ctx.send("Success!")
        except Exception as e:
            await ctx.send(e)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
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

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('ValueTeam', 'Developer')))
    @commands.hybrid_command(name='update_bf_value', description='updates an value of an item in blox fruits')
    async def UpdateValue(self,ctx: commands.Context,name: str,physical_value: int = None,permanent_value: int = None,physical_demand: str = None,permanent_demand: str = None,demand_type: str = None,permanent_demand_type: str = None,category: str = None,aliases: str = None,icon_url: str = None):
        try:
            cursor = await VC.vdb.execute("SELECT * FROM BF_ItemValues WHERE name = ?", (name.title(),))
            row = await cursor.fetchone()
            if not row:
                await ctx.send(f"No item found with name {name}.")
                return


            columns = [d[0] for d in cursor.description]
            current_values = dict(zip(columns, row))


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

    

async def setup(bot):
    await bot.add_cog(LilyBloxFruits(bot))