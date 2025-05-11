import Moderation.sLilyModeration as mLily
import Config.sBotDetails as Config


import re
import discord
import os
import pandas as pd


from enum import Enum
from discord.ext import commands
from datetime import datetime

class PositionType(str, Enum):
    Top = "Top"
    Bottom = "Bottom"

async def validate_data(ctx, name, color, position_type:PositionType = PositionType.Bottom, role_name_or_id:str = ""):
    guild = ctx.guild
    if ctx.author.id not in Config.staff_manager_ids + [845511381637529641]:
        return None, mLily.SimpleEmbed("Access Denied")
    
    RolesCSV = f"storage/{ctx.guild.id}/configs/roles.csv"

    os.makedirs(os.path.dirname(RolesCSV), exist_ok=True)
    if not os.path.isfile(RolesCSV):
        df = pd.DataFrame(columns=['role_name', 'role_id', 'creation_date'])
        df.to_csv(RolesCSV, index=False)

    df = pd.read_csv(RolesCSV)

    if len(df) >= Config.role_creation_limit:
        return None, mLily.SimpleEmbed(f"Role Limit Reached. You cannot exceed creating **{Config.role_creation_limit}** roles")

    role_color = None
    if color:
        color = color.lstrip("#")
        if re.fullmatch(r"[0-9a-fA-F]{6}", color):
            role_color = discord.Colour(int(color, 16))
        else:
            return None, mLily.SimpleEmbed("Invalid color format. Use hex like `#FFAA00` or `FFAA00`.")

    icon_bytes = None
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            return None, mLily.SimpleEmbed("Only image attachments like **PNG or JPG** are allowed.")
        icon_bytes = await attachment.read()

    ref_role = None
    if role_name_or_id:
        ref_role = discord.utils.get(guild.roles, name=role_name_or_id) or \
                   (guild.get_role(int(role_name_or_id)) if role_name_or_id.isdigit() else None)
        if not ref_role:
            return None, mLily.SimpleEmbed(f"Reference role **{role_name_or_id}** not found.")

    user_roles = [r for r in ctx.author.roles if r != guild.default_role]
    user_highest = max([r.position for r in user_roles]) if user_roles else 0

    position = 1
    if ref_role:
        position = ref_role.position + 1 if position_type == PositionType.Top else ref_role.position
        if position > user_highest:
            return None, mLily.SimpleEmbed("You cannot create a role above your highest role.")

    return {
        "guild": guild,
        "role_color": role_color,
        "icon_bytes": icon_bytes,
        "position": position
    }, None


async def create_guild_role(ctx:commands.Context, guild, name, role_color, icon_bytes, position, author, assignable_priority):
    new_role = await guild.create_role(
        name=name,
        colour=role_color,
        mentionable=False,
        reason=f"Created by {author} with assignable priority {assignable_priority}"
    )

    if icon_bytes:
        await new_role.edit(icon=icon_bytes)

    await guild.edit_role_positions({new_role: position})

    role_data = {
        "role_name": new_role.name,
        "role_id": new_role.id,
        "creation_date": datetime.utcnow().isoformat()
    }

    file_path = f"storage/{ctx.guild.id}/configs/roles.csv"

    file_exists = os.path.isfile(file_path)

    df = pd.DataFrame([role_data])
    df.to_csv(file_path, mode='a', header=not file_exists, index=False)

    await Config.save_roles(ctx, new_role.id, assignable_priority)

    return new_role

async def DeleteRole(ctx:commands.Context, role: discord.Role):
    try:
        file_path = f"storage/{ctx.guild.id}/configs/roles.csv"
        if not os.path.exists(file_path):
            await ctx.send("No roles have been created using the bot yet.")
            return False

        df = pd.read_csv(file_path)

        df['role_id'] = df['role_id'].astype('int64')

        role_id = role.id

        role_data = df[df['role_id'] == role_id]

        if role_data.empty:
            await ctx.send(f"Role with ID {role_id} cannot be deleted as it is not created using the bot.")
            return False

        await role.delete(reason="Deleted by bot command.")

        df = df[df['role_id'] != role_id]
        df.to_csv(file_path, index=False)

        await ctx.send(f"Role '{role.name}' has been successfully deleted")
        return True
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        return False