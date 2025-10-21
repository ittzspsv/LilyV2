import discord
import re

async def on_presence_update(before, after):
    try:
        guild = after.guild
        if guild is None:
            return
        target_role_name = "Media Perms"
        keyword = "bloxtrade"

        role = discord.utils.get(guild.roles, name=target_role_name)
        if not role:
            return

        before_status = next((a.state or a.name for a in before.activities if isinstance(a, discord.CustomActivity)), None)
        after_status = next((a.state or a.name for a in after.activities if isinstance(a, discord.CustomActivity)), None)

        if before_status == after_status:
            return

        text = (after_status or "").lower()

        words = re.findall(r"[a-zA-Z0-9]+", text)
        has_keyword = any(keyword in w for w in words)

        if has_keyword and role not in after.roles:
            await after.add_roles(role, reason=f"Custom status contains '{keyword}'")

        elif not has_keyword and role in after.roles:
            await after.remove_roles(role, reason=f"Custom status no longer contains '{keyword}'")

    except discord.Forbidden:
        pass
    except Exception as e:
        pass