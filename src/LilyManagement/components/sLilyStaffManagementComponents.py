import discord
import Config.sBotDetails as Configs

from typing import Dict
from discord.ext import commands

class StaffListView(discord.ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, role_data: dict, role_id: int, page: int = 0, per_page: int = 6):
        super().__init__()

        self.owner_id = interaction.user.id
        self.role_data = role_data
        self.role_id = role_id
        self.per_page = per_page

        staffs_complete = role_data.get("staff", [])
        self.total_staff = len(staffs_complete)

        max_page = max((self.total_staff - 1) // per_page, 0)
        self.page = max(0, min(page, max_page))

        start = self.page * per_page
        end = start + per_page
        staffs = staffs_complete[start:end]

        role = interaction.guild.get_role(role_id)
        role_icon_url = role.icon.url if role and role.icon else interaction.client.user.avatar.url

        staff_sections = []

        for i, staff in enumerate(staffs):
            avatar = staff.get('avatar_profile') or interaction.client.user.avatar.url

            staff_sections.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=(
                            f"### <@{staff.get('id','Unknown')}>\n"
                            f"- Timezone : {staff.get('timezone','Default')}\n"
                            f"- Joined : {staff.get('joined_on')}"
                        )
                    ),
                    accessory=discord.ui.Thumbnail(media=avatar)
                )
            )

            if i < len(staffs) - 1:
                staff_sections.append(
                    discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
                )

        role_section = discord.ui.Section(
            discord.ui.TextDisplay(
                content=f"## {role_data.get('role_name','Unknown')}\n"
                        f"- Total Staff: `{self.total_staff}`\n"
                        f"- Page: `{self.page+1}/{max_page+1}`"
            ),
            accessory=discord.ui.Thumbnail(media=role_icon_url)
        )

        container_items = [
            role_section,
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            *staff_sections
        ]

        buttons = discord.ui.ActionRow()

        if self.page > 0:
            left = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⏪")
            left.callback = self.left_paginator_callback
            buttons.add_item(left)

        if end < self.total_staff:
            right = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⏩")
            right.callback = self.right_paginator_callback
            buttons.add_item(right)

        if buttons.children:
            container_items.append(buttons)

        container_items.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media=Configs.img['border'])
            )
        )

        self.container = discord.ui.Container(*container_items)
        self.add_item(self.container)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only instigator has authority to access.",
                ephemeral=True
            )
            return False
        return True

    async def left_paginator_callback(self, interaction: discord.Interaction):
        view = StaffListView(
            interaction,
            self.role_data,
            self.role_id,
            page=self.page - 1
        )
        await interaction.response.edit_message(view=view)

    async def right_paginator_callback(self, interaction: discord.Interaction):
        view = StaffListView(
            interaction,
            self.role_data,
            self.role_id,
            page=self.page + 1
        )
        await interaction.response.edit_message(view=view)

class StaffsView(discord.ui.LayoutView):
    def __init__(self, ctx: commands.Context, overall_details: Dict, role_users_map):
        super().__init__(timeout=500)

        self.message = None
        self.role_users_map = role_users_map

        role_select_options = [
            discord.SelectOption(label=data["role_name"], value=str(role_id))
            for role_id, data in role_users_map.items()
            if role_id and data["role_name"]
        ]

        self.roles_selector = discord.ui.Select(
            custom_id="roles_selector",
            options=role_select_options
        )
        self.roles_selector.callback = self.role_selector_callback

        self.container_1 = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    content=(
                        "## Staff's Overview\n"
                        "- Lily's Staff Management System.\n\n"
                        f"### __Overall Details__\n"
                        f"- **ON LOA** - `{overall_details.get('LOA')}`\n"
                        f"- **Active Staffs** - `{overall_details.get('ActiveStaffs')}`\n"
                        f"- **Total Staffs** - `{overall_details.get('TotalStaffs')}`"
                    )
                ),
                accessory=discord.ui.Thumbnail(media=ctx.guild.icon.url)
            ),
            discord.ui.ActionRow(self.roles_selector),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media=Configs.img['border'])
            ),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(self.container_1)

    async def role_selector_callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.roles_selector.values[0])
        role_data = self.role_users_map[selected_role_id]

        view = StaffListView(interaction, role_data, selected_role_id)

        await interaction.response.send_message(
            view=view,
            ephemeral=True
        )

    async def on_timeout(self):
        self.roles_selector.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass

