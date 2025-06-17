from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator


import discord
import LilyManagement.sLilyStaffManagement as smLily
import LilyModeration.sLilyModeration as mLily
import Config.sBotDetails as Config
import re
import json
import io
import pandas as pd

from discord.ext import commands



class LilyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='staffdata', description='shows data for a particular staff')
    async def staffdata(self, ctx:commands.Context, id:str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        try:
            staff_member = await self.bot.fetch_user(int(id))
            await ctx.send(embed=smLily.FetchStaffDetail(staff_member))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='staffs', description='shows all staff registered name with the count')
    async def staffs(self, ctx:commands.Context, filter_type:str="default", * ,filter_value:str=""):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536, 1356198968962449478]:
            await ctx.send("Server Change!")
            return
        if filter_type == "default":
            await ctx.send(embed=smLily.FetchAllStaffs())
        else:
            try:
                await ctx.send(embed=smLily.FetchAllStaffsFiltered(filter_type, filter_value))
                
            except Exception as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Exception {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.StaffManagerRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='staffstrike', description='strikes a staff with a specified reason')
    async def staffstrike(self, ctx: commands.Context, id: str, *, reason: str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=smLily.StrikeStaff(ctx, id, reason))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.StaffManagerRoles + Config.OwnerRoles)
    @commands.hybrid_command(name='update_staff_data', description='updates staff data with a specific update_cache')
    async def update_staff_data(self, ctx: commands.Context, update_cache: str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        try:
            with open("src/Management/StaffManagement.json", "r") as f:
                data = json.load(f)
        except Exception as e:
            await ctx.send(f"Error loading staff data: {e}")
            return
        
        match = re.match(r"^([^:]+):([^:]+):(.+)$", update_cache)
        if not match:
            await ctx.send("Invalid update syntax. Use <user_id>:<key>:<new_value>")
            return
        
        user_id, key, new_value = match.groups()
        
        if user_id not in data:
            await ctx.send(embed=mLily.SimpleEmbed(f"User ID {user_id} not found in JSON source."))
            print(f"{user_id} not found in JSON source")
            return
        
        if key not in data[user_id]:
            await ctx.send(embed=mLily.SimpleEmbed(f"Key {key} not found for user `{user_id}`."))
            return
        
        old_value = data[user_id][key]
        data[user_id][key] = new_value
        
        try:
            with open("src/Management/StaffManagement.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            await ctx.send(f"Error saving staff data: {e}")
            return
        
        await ctx.send(embed=mLily.SimpleEmbed(
            f"Updated {key} for user {user_id} to {new_value}."
        ))
        
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='strikes', description='shows strikes for a concurrent staff')
    async def strikes(self, ctx: commands.Context, id: str):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        try:
            await ctx.send(embed=smLily.ListStrikes(id))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='export_staff_data', description='exports staff data as a .csv file')
    async def export_staff_data(self, ctx: commands.Context):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        staff_df = smLily.ExportStaffDataAsCSV()
        csv_buffer = io.StringIO()
        staff_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        await ctx.send("Here is the Source CSV", file=discord.File(csv_buffer, "staff_data.csv"))

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name='import_staff_data', description='imports staff data as a .csv file')
    async def import_staff_data(self, ctx: commands.Context):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        if not ctx.message.attachments:
            await ctx.send("Please attach a .csv file.")
            return

        attachment = ctx.message.attachments[0]
        
        if not attachment.filename.endswith(".csv"):
            await ctx.send("The file must be a .csv")
            return

        try:
            file_bytes = await attachment.read()
            df = pd.read_csv(io.BytesIO(file_bytes))
            
            success = smLily.ImportStaffDataFromCSV(df)

            if success:
                await ctx.send("Staff data imported successfully.")
            else:
                await ctx.send("Failed Import")
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles + Config.StaffManagerRoles)
    @commands.hybrid_command(name='add_staff', description='adds a staff to the data')
    async def addstaff(self, ctx:commands.Context, id:str=""):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        staff_member = await ctx.guild.fetch_member(id)
        await ctx.send("Staff Added Successfully") if smLily.AddStaff(staff_member) else await ctx.send("Failure")

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles + Config.StaffManagerRoles)
    @commands.hybrid_command(name='remove_staff', description='removes a staff to the data')
    async def removestaff(self, ctx:commands.Context, id:str=""):
        if ctx.guild.id not in [970643838047760384, 1240215331071594536]:
            await ctx.send("Server Change!")
            return
        id = id.replace("<@", "").replace(">", "")
        staff_member = await ctx.guild.fetch_member(id)
        await ctx.send("Staff Removed Successfully") if smLily.RemoveStaff(staff_member) else await ctx.send("Failure")


async def setup(bot):
    await bot.add_cog(LilyManagement(bot))