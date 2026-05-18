from lily_agent import tool
from pydantic import BaseModel, Field

import discord
from typing import Dict, Any
from ..data.overload_data import OverloadData

class CreateRole(BaseModel):
    role_name: str = Field(
        ...,
        description="Name of the role to create. If the user does not specify a name, default to 'new_role'."
    )

    color: int | None = Field(
        None,
        description="Optional role color as an integer (RGB hex format, e.g. 0xFF0000 for red). If not provided, no color is assigned."
    )

    hoist: bool = Field(
        False,
        description="Whether the role should be displayed separately in the member list (hoisted role). Default is False."
    )

    mentionable: bool = Field(
        False,
        description="Whether the role can be mentioned by all users using @role. Default is False."
    )

@tool(description="Create a discord role", parameters=CreateRole, overload=True)
async def create_role(
    data: OverloadData,
    role_name: str,
    color: int | None,
    hoist: bool,
    mentionable: bool
):
    message = data.message

    if isinstance(message.author, discord.Member) and not message.author.guild_permissions.manage_roles:
        return "The user does not have permission to execute this command. They need Manage Roles permission."

    if not message.guild:
        return "Guild object not found."
    
    additional_description = ""

    try:
        role_kwargs: Dict[str, Any] = {
            "name": role_name
        }

        if hoist is not None:
            role_kwargs["hoist"] = hoist

        if mentionable is not None:
            role_kwargs["mentionable"] = mentionable

        if color is not None:
            role_kwargs["colour"] = discord.Colour(color)

        if message.attachments:
            first_attachment = message.attachments[0]

            if first_attachment.content_type and first_attachment.content_type.startswith("image/"):
                icon_bytes = await first_attachment.read()
                role_kwargs["display_icon"] = icon_bytes

                additional_description += "With role icon that has been attached"
        else:
            additional_description += "Role icon has not been attached, so it's not assigned"

        role = await message.guild.create_role(**role_kwargs)

        return (
            f"Successfully created role '{role.name} {additional_description}' "
            f"(ID: {role.id}) in guild '{message.guild.name}'."
        )

    except Exception as e:
        return (
            f"Failed to create role '{role_name}' "
            f"in guild '{message.guild.name}': {str(e)}"
        )