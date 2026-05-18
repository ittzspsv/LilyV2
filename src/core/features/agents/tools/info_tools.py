from lily_agent import tool
from pydantic import BaseModel, Field
from typing import Optional

from ..data.overload_data import OverloadData

import discord
import re

class MemberDetails(BaseModel):
    member_id: str = Field(..., description="The member id.  It is passed in as 'user_id' or the user explicit gives you an id")

class GuildDetails(BaseModel):
    guild_id: str


@tool(description="Get to know about detail of a Discord member/user. Get their name, when they joined on, what's their profile and a lot of information by calling this tool.", parameters=MemberDetails, overload=True)
async def get_member_details(member_id: str, data: OverloadData):
    message = data.message

    if message.guild is None:
        return

    member_id = member_id.replace("<@", "").replace(">", "")
    user: Optional[discord.Member] = message.guild.get_member(int(member_id))

    if user is None:
        try:
            user = await message.guild.fetch_member(int(member_id))
        except discord.NotFound:
            return {"message": "Failed to fetch user information"}
        except discord.Forbidden:
            return {"message": "Failed to fetch user information due to permission issues"}
        except discord.HTTPException:
            return {"message": "Failed to fetch user information due to network error"}
        except Exception as e:
            print(e)
            return {"message": "An unexpected error occurred while fetching user information"}
    if user:
        return (
            f"User {user.name} "
            f"(ID: {user.id}, "
            f"display name: {getattr(user, 'display_name', user.name)}, "
            f"global name: {getattr(user, 'global_name', 'N/A')}, "
            f"account created: {user.created_at}, "
            f"avatar URL: {user.display_avatar.url if user.display_avatar else 'None'}, "
            f"banner URL: {user.display_banner.url if getattr(user, 'banner', None) else 'None'})"
        )
    else: 
        return (
            "Failed to retrieve the user!"
      )
    
@tool(description="Get to know about detail of this guild", parameters=GuildDetails, overload=True)
async def get_guild_details(guild_id: int, data: OverloadData) -> str:
    message = data.message
    guild = message.guild

    if guild is None:
        return "No guild information available (message sent outside a server)."

    owner = guild.get_member(guild.owner_id)
    if owner is None:
        try:
            owner = await guild.fetch_member(guild.owner_id)
        except Exception:
            owner = None

    return (
        f"Guild {guild.name} "
        f"(ID: {guild.id}, "
        f"description: {guild.description or 'None'}, "
        f"owner: {owner.name if owner else 'Unknown'} "
        f"member count: {guild.member_count}, "
        f"created at: {guild.created_at}, "
        f"vanity URL: {getattr(guild, 'vanity_url_code', None) or 'None'}, "
        f"icon URL: {guild.icon.url if guild.icon else 'None'}, "
        f"banner URL: {guild.banner.url if guild.banner else 'None'}, "
    )
