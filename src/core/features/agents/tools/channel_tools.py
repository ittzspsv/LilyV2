from lily_agent import tool
from pydantic import BaseModel, Field
from typing import Optional
from ..data.overload_data import OverloadData

import discord

class CreateChannel(BaseModel):
    channel_name: str = Field(..., description="The name of the channel.  if the user doesn't provides it default it to new_channel")
    reason: str = Field(..., description="The reason for creating the channel.")
    category: Optional[str] = Field(..., description="The cateogory of the channel.")


@tool(description="Create a discord text channel", parameters=CreateChannel, overload=True)
async def create_channel(channel_name: str, reason: str ,category: Optional[str] ,data: OverloadData):
    message = data.message
    guild = message.guild

    if isinstance(message.author, discord.Member) and not message.author.guild_permissions.manage_channels:
        return "The user does not have permission to execute this command. They would need manage channel permission!"

    if guild is None:
        return f"Guild was not found."

    try:
        if category is None:
            channel = await guild.create_text_channel(name=channel_name, reason=reason)
            return (
                f"Successfully created channel '{channel.name}' "
                f"(ID: {channel.id}) in guild '{guild.name}'."
            )
        else:
            category_ = discord.utils.get(guild.categories, name=category)
            if isinstance(category_, discord.CategoryChannel):
                channel = await guild.create_text_channel(name=channel_name, reason=reason, category=category_)
                return (
                    f"Successfully created channel '{channel.name}' "
                    f"in guild '{guild.name}'."
                )
            
            else:
                channel = await guild.create_text_channel(name=channel_name, reason=reason)
                return (
                    f"Successfully created channel '{channel.name}'"
                    f"in guild '{guild.name}'."
                    f"However channel category cannot be found"
                )

        

    except Exception as e:
        return (
            f"Failed to create channel '{channel_name}' "
            f"in guild '{guild.name}': {str(e)}"
        )
