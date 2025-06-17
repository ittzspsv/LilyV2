import json
import discord
import Config.sBotDetails as Config
import pandas as pd

from datetime import datetime
from discord.ext import commands

def FetchStaffDetail(staff: discord.Member):
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as data:
            staff_data = json.load(data)
            
            staff_info = staff_data.get(str(staff.id))

            if not staff_info:
                raise ValueError("Staff data not found.")

            start_date = datetime.strptime(staff_info['join_date'], "%d/%m/%Y")
            current_date = datetime.today()

            years = current_date.year - start_date.year
            months = current_date.month - start_date.month
            days = current_date.day - start_date.day

            if days < 0:
                months -= 1
                days += 30
            if months < 0:
                years -= 1
                months += 12

            embed = discord.Embed(title=staff_info['name'].title(), colour=0xf50000)

            embed.add_field(name="Role", value=staff_info['role'], inline=False)
            embed.add_field(name="Responsibilities", value=staff_info['responsibility'], inline=False)
            embed.add_field(name="Join Date", value=staff_info['join_date'], inline=False)
            embed.add_field(name="Evaluated Experience In Server", 
                            value=f"{years} years {months} months {days} days", inline=False)
            embed.add_field(name="Strike Count", value=f"{len(staff_info['strikes'])}", inline=False)
            embed.set_thumbnail(url=staff.avatar.url)

            return embed
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), colour=0xf50000)
        return embed
    

def FetchAllStaffs():
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as data:
            staff_data = json.load(data)

            embed = discord.Embed(
                title="STAFF LIST",
                description=f"**Total Count : {len(staff_data)}**",
                colour=0x3100f5
            )

            roles = {}
            active_moderators = 0
            loa_moderators = 0

            for staff_id, staff_info in staff_data.items():
                role = staff_info["role"]
                mention = f"<@{staff_id}>"

                if role not in roles:
                    roles[role] = []

                roles[role].append(mention)

                if staff_info.get("LOA") is True:
                    loa_moderators += 1
                elif staff_info.get("higher_staff") is False and staff_info.get("LOA") is False:
                    active_moderators += 1

            for role, mentions in roles.items():
                count = len(mentions)
                names_with_bullet = "- " + "\n- ".join(mentions)

                embed.add_field(
                    name=f"__{role}__ ({count})",
                    value=names_with_bullet,
                    inline=False
                )

            analysis_text = f"**Staff Prioritized on Moderation:** {active_moderators}\n**Staffs in LOA:** {loa_moderators}"
            embed.add_field(
                name="__ANALYSIS__",
                value=analysis_text,
                inline=False
            )

            return embed

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=str(e),
            colour=0xf50000
        )
        return embed
    

def FetchAllStaffsFiltered(filter_type=None, filter_value=None):
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as data:
            staff_data = json.load(data)

        staff_list = [(staff_id, info) for staff_id, info in staff_data.items()]

        if filter_type:
            if filter_type == "role":
                staff_list = [(sid, info) for sid, info in staff_list if info.get("role") == filter_value]
            elif filter_type == "LOA":
                staff_list = [(sid, info) for sid, info in staff_list if info.get("LOA") == bool(filter_value)]
            elif filter_type == "higher_staff":
                staff_list = [(sid, info) for sid, info in staff_list if info.get("higher_staff") == bool(filter_value)]
            elif filter_type == "strikes":
                staff_list.sort(key=lambda x: len(x[1].get("strikes", [])), reverse=True)
            elif filter_type == "join_date":
                from datetime import datetime
                staff_list.sort(
                    key=lambda x: datetime.strptime(x[1].get("join_date", "01/01/2099"), "%d/%m/%Y")
                )

        embed = discord.Embed(
            title="STAFF LIST",
            description=f"**Total Count : {len(staff_list)}**",
            colour=0x3100f5
        )

        roles = {}
        active_moderators = 0
        loa_moderators = 0

        for staff_id, info in staff_list:
            role = info.get("role", "Unknown")
            mention = f"<@{staff_id}>"

            if role not in roles:
                roles[role] = []
            roles[role].append(mention)

            if info.get("LOA"):
                loa_moderators += 1
            elif not info.get("higher_staff", False) and not info.get("LOA"):
                active_moderators += 1

        for role, mentions in roles.items():
            embed.add_field(
                name=f"__{role}__ ({len(mentions)})",
                value="- " + "\n- ".join(mentions),
                inline=False
            )

        analysis = f"**Staff Prioritized on Moderation:** {active_moderators}\n**Staffs in LOA:** {loa_moderators}"
        embed.add_field(name="__ANALYSIS__", value=analysis, inline=False)

        return embed

    except Exception as e:
        return discord.Embed(
            title="Error",
            description=str(e),
            colour=0xf50000
        )


def StrikeStaff(ctx:commands.Context, staff_id: str, reason: str, ):
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as data:
            staff_data = json.load(data)
        
        if staff_id in staff_data:
            strike = {
                "reason": reason,
                "date": datetime.today().strftime("%d/%m/%Y"),
                "manager": ctx.author.id
            }
            staff_data[staff_id]["strikes"].append(strike)

            with open("src/LilyManagement/StaffManagement.json", "w") as data:
                json.dump(staff_data, data, indent=2)
            embed = discord.Embed(title=f"",description=f'**Successfully Striked Staff <@{staff_id}>**',
                      colour=0xf50000)
            return embed
        else:
            embed = discord.Embed(title="Staff Member Not Found",
                      colour=0xf50000)
            return embed
    except Exception as e:
        embed = discord.Embed(title=f"Exception : {e}",
                      colour=0xf50000)
        return embed
    
def ListStrikes(staff_id: str):
    try:
         with open("src/LilyManagement/StaffManagement.json", "r") as data:
             staff_data = json.load(data)
             strikes = staff_data[staff_id].get("strikes", [])

             embed = discord.Embed(title="Strikes",
                        description=f"Showing for <@{staff_id}>",
                        colour=0xf50000)
             j = 1
             for i in strikes:
                embed.add_field(name="Strike 1",
                value=f"**Reason     : {i['reason']} **\n**Date          : {i['date']}**\n**Manager  : <@{i['manager']}>**",
                inline=False)

                j += 1

             return embed
                       

    except Exception as e:
        embed = discord.Embed(title=f"Exception : {e}",
                      colour=0xf50000)
        return embed

def ExportStaffDataAsCSV():
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as data:
            staff_data = json.load(data)
        flattened_data = []

        for staff_id, staff_info in staff_data.items():
            strikes = staff_info["strikes"]
            strikes_str = json.dumps(strikes) if strikes else "[]"

            flattened_data.append({
                "Staff ID": staff_id,
                "Name": staff_info["name"],
                "Role": staff_info["role"],
                "Responsibility": staff_info["responsibility"],
                "Join Date": staff_info["join_date"],
                "Strikes": strikes_str,
                "LOA" : staff_info["LOA"],
                "higher_staff" : staff_info["higher_staff"]
            })


        df = pd.DataFrame(flattened_data)

        return df
    except Exception as e:
        return pd.DataFrame()
    
def ImportStaffDataFromCSV(df: pd.DataFrame):
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as file:
            staff_data = json.load(file)

        new_staff_data = {}
        current_ids = set()

        for _, row in df.iterrows():
            staff_id = str(row["Staff ID"])
            current_ids.add(staff_id)
            strikes_json = row.get("Strikes", "[]")

            try:
                strikes = json.loads(strikes_json) if isinstance(strikes_json, str) else strikes_json
            except json.JSONDecodeError:
                strikes = []

            new_staff_data[staff_id] = {
                "name": row["Name"],
                "role": row["Role"],
                "responsibility": row["Responsibility"],
                "join_date": row["Join Date"],
                "strikes": strikes,
                "LOA" : row["LOA"],
                "higher_staff" : row["higher_staff"]

            }

        with open("src/LilyManagement/StaffManagement.json", "w") as file:
            json.dump(new_staff_data, file, indent=2)

        return True
    except Exception as e:
        print(e)
        return False

def AddStaff(staff: discord.Member):
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as f:
            data = json.load(f)

        if staff.id in data:
            print("Staff id in data")
            return False

        data[staff.id] = {
            "name": staff.display_name,
            "role": staff.top_role.name,
            "responsibility": "NIL",
            "join_date": datetime.now().strftime("%d/%m/%Y"),
            "strikes": [],
            "LOA" : False,
            "higher_staff" : False
        }

        with open("src/Management/StaffManagement.json", "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(e)
        return False
    
def RemoveStaff(staff: discord.Member):
    try:
        with open("src/LilyManagement/StaffManagement.json", "r") as f:
            data = json.load(f)

        staff_id = str(staff.id)
        if staff_id not in data:
            print("Staff id not in data")
            return False

        del data[staff_id]

        with open("src/LilyManagement/StaffManagement.json", "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(e)
        return False
