from typing import Union, Optional
import os
import json

from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
import aiohttp
from discord.ext import commands
from discord.ext.commands import MemberConverter

# Constants
UTC = timezone.utc


def format_currency(val: Union[str, int]) -> str:
    value = int(val)
    if value >= 1_000_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000_000:.1f}DX"
    elif value >= 1_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000:.1f}NX"
    elif value >= 1_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000:.1f}OX"
    elif value >= 1_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000:.1f}SPX"
    elif value >= 1_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000:.1f}SX"
    elif value >= 1_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000:.1f}QI"
    elif value >= 1_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000:.1f}QT"
    elif value >= 1_000_000_000_000: 
        return f"{value / 1_000_000_000_000:.1f}T"
    elif value >= 1_000_000_000:  
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:  
        return f"{value / 1_000:.1f}k"
    else:
        return str(int(value))
    
# function used to safely load an json
def load_json(path: Optional[str]) -> dict:
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except (json.JSONDecodeError, OSError):
        return {}
    
# returns current time based on ust
def utcnow() -> datetime:
    return datetime.now(UTC)

def parse_date(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromisoformat(ts)

def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()

async def get_safe_member(*,bot: Optional[commands.Bot],guild: Union[discord.Guild, int], id: int) -> Optional[discord.Member]:
    if isinstance(guild, discord.Guild):
        member = guild.get_member(id)

        if member:
            return member

        try:
            return await guild.fetch_member(id)
        except:
            return None

    guild_obj = bot.get_guild(guild) if bot else None

    if not guild_obj:
        try:
            guild_obj = await bot.fetch_guild(guild)
        except:
            return None

    try:
        return await guild_obj.fetch_member(id)
    except:
        return None
    
async def get_member_from_user(bot, interaction: discord.Interaction, user: Union[int, str]):
    converter = MemberConverter()

    try:
        ctx = await bot.get_context(interaction.message)
        member: Optional[discord.Member] = await converter.convert(ctx, user)
        print(member.id)
    except commands.CommandError:
        print("Error Processing the command")

async def fetch_json(session, url, method="GET", **kwargs):
    async with session.request(method, url, **kwargs) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise Exception(f"HTTP {resp.status}: {text}")
        return await resp.json()
    
async def get_user_data(username: str):
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(
            session,
            "https://users.roblox.com/v1/usernames/users",
            method="POST",
            json={"usernames": [username], "excludeBannedUsers": False}
        )

        if not data["data"]:
            raise Exception("User not found")

        user = data["data"][0]
        user_id = user["id"]

        user_info = await fetch_json(
            session,
            f"https://users.roblox.com/v1/users/{user_id}"
        )

        avatar_data = await fetch_json(
            session,
            f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false"
        )

        avatar_url = avatar_data["data"][0]["imageUrl"]

        presence_data = await fetch_json(
            session,
            "https://presence.roblox.com/v1/presence/users",
            method="POST",
            json={"userIds": [user_id]}
        )

        presence = presence_data["userPresences"][0]["userPresenceType"]

        presence_map = {
            0: "Offline",
            1: "Online",
            2: "In Game",
            3: "In Studio"
        }

        status = presence_map.get(presence, "Unknown")

        created = user_info["created"]
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        unix_timestamp = int(dt.timestamp())

        return {
            "display_name" : user_info["displayName"],
            "name" : user_info["name"],
            "user_id" : str(user_id),
            "avatar_url" : avatar_url,
            "status" : status,
            "created_at" : unix_timestamp,
            "description" : user_info["description"] or "No Description"
        }