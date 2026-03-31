import discord
import Config.sBotDetails as Configs

from typing import Dict
from discord.ext import commands
from Misc.sLilyEmbed import simple_embed
import LilyManagement.db.sLilyStaffDatabaseAccess as LSDA

from typing import List, Dict, Any

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
                            f"- Joined : <t:{staff.get('joined_on')}:R>"
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

class LOAStaffsView(discord.ui.LayoutView):
    def __init__(self, interaction: discord.Interaction ,staff_datas: List[Dict[str, Any]]):
        super().__init__()

        self.staff_datas = staff_datas
        self.interaction = interaction
        self.staff_ids = ""

        for staff_data in staff_datas:
            self.staff_ids += f'<@{staff_data.get("staff_id")}>\n'

        if not self.staff_ids:
            self.staff_ids = "No Staffs Returned"

        self.container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content="## LOA Staffs"),
                discord.ui.TextDisplay(content="- List all the staffs who are on leave"),
                accessory=discord.ui.Thumbnail(
                media = (
                    self.interaction.guild.icon.url
                    if self.interaction.guild.icon
                    else self.interaction.client.user.avatar.url
                    )                
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=self.staff_ids),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        )

        self.add_item(self.container)

class StaffsView(discord.ui.LayoutView):
    def __init__(self, ctx: commands.Context, overall_details: Dict, role_users_map):
        super().__init__(timeout=500)

        self.message = None
        self.role_users_map = role_users_map

        role_select_options = [
            discord.SelectOption(label=data["role_name"], value=str(role_id))
            for role_id, data in role_users_map.items()
            if role_id and data["role_name"] and data["role_type"] == "Staff"
        ]

        responsibility_select_options = [
            discord.SelectOption(label=data["role_name"], value=str(role_id))
            for role_id, data in role_users_map.items()
            if role_id and data["role_name"] and data["role_type"] == "Responsibility"
        ]

        self.roles_selector = discord.ui.Select(
            custom_id="roles_selector",
            options=role_select_options
        )

        self.responsibility_selector = discord.ui.Select(
            custom_id="responsibility_selector",
            options=responsibility_select_options
        )

        self.loa_staffs_btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="List LOA Staffs",
            )
        
        self.responsibility_loa_staff_btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="List LOA Staffs",
        )

        self.roles_selector.callback = self.role_selector_callback
        self.responsibility_selector.callback = self.responsibility_selector_callback
        self.loa_staffs_btn.callback = self.loa_staffs_callback
        self.responsibility_loa_staff_btn.callback = self.responsibility_loa_staff_btn_callback

        self.container_1 = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    content=(
                        "## Staff's Overview\n"
                        "- Lily's Staff Management System.\n\n"
                    )
                ),
                accessory=discord.ui.Thumbnail(media=ctx.guild.icon.url)
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="### Server Staff Team\n- List of Role Category who has **Moderation/Administration/Management** Authority"),
            discord.ui.TextDisplay(content=f"### __Overall Details__\n"
                        f"- **ON LOA** - `{overall_details.get("Staff").get('loa')}`\n"
                        f"- **Active Staffs** - `{overall_details.get("Staff").get('active')}`\n"
                        f"- **Total Staffs** - `{overall_details.get("Staff").get('total')}`"),
            discord.ui.ActionRow(self.roles_selector),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                    discord.ui.TextDisplay(content="### LOA Staffs"),
                    discord.ui.TextDisplay(content="- Displays All Engagement Staffs who are on leave"),
                    accessory=self.loa_staffs_btn
                ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="### Server Community Engagement Team\n- List of Role Category who engages the Community"),
            discord.ui.TextDisplay(content=f"### __Overall Details__\n"
                        f"- **ON LOA** - `{overall_details.get("Responsibility").get('loa')}`\n"
                        f"- **Active Staffs** - `{overall_details.get("Responsibility").get('active')}`\n"
                        f"- **Total Staffs** - `{overall_details.get("Responsibility").get('total')}`"),
            discord.ui.ActionRow(self.responsibility_selector),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                    discord.ui.TextDisplay(content="### LOA Staffs"),
                    discord.ui.TextDisplay(content="- Displays All Engagement Staffs who are on leave"),
                    accessory=self.responsibility_loa_staff_btn
                ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
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

    async def responsibility_selector_callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.responsibility_selector.values[0])
        role_data = self.role_users_map[selected_role_id]

        view = StaffListView(interaction, role_data, selected_role_id)

        await interaction.response.send_message(
            view=view,
            ephemeral=True
        )

    async def loa_staffs_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        staff_datas: List[Dict[str, Any]] = await LSDA.fetch_loa_staffs({"guild_id" : interaction.guild.id, "role_type" : "Staff"})
        view = LOAStaffsView(interaction, staff_datas)
        await interaction.followup.send(view=view, ephemeral=True)

    async def responsibility_loa_staff_btn_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        staff_datas: List[Dict[str, Any]] = await LSDA.fetch_loa_staffs({"guild_id" : interaction.guild.id, "role_type" : "Responsibility"})
        view = LOAStaffsView(interaction, staff_datas)
        await interaction.followup.send(view=view, ephemeral=True)

    async def on_timeout(self):
        self.roles_selector.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass

class RoleSelector(discord.ui.RoleSelect):
    def __init__(self, interactor: discord.Member):
        super().__init__(
            placeholder="Select Staff Roles...",
            min_values=1,
            max_values=25
        )

        self.interactor: discord.Member = interactor

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.interactor.id:
            roles: list[discord.Role] = self.values
            selected_roles: list = []

            for role in roles:
                selected_roles.append(
                    {
                        "role_name": role.name,
                        "role_id": role.id,
                        "role_icon": role.icon.url if role.icon else None
                    }
                )
            payload: dict = {
                "guild_id" : interaction.guild.id,
                "roles" : selected_roles
            }

            response = await LSDA.add_role_entries(payload=payload)
            if response.get("success"):
                await interaction.response.send_message(
                    embed=simple_embed(message=response.get("message"))
                )
            else:
                await interaction.response.send_message(
                    embed=simple_embed("An Error occured while adding roles", "cross")
                )

        else:
            await interaction.response.send_message(
                embed=simple_embed("You cannot interact with this", "cross"),
                ephemeral=True
            )

class StaffRoleView(discord.ui.LayoutView):
    def __init__(self, bot, interactor: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.original_interactor: discord.Member = interactor
        self.interactor = interactor

        self.container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content="## Staff Hierarchy Construction."),
                discord.ui.TextDisplay(content="- You can construct a staff hierarchy for your server and define it in Lily to give them various permissions."),
                accessory=discord.ui.Thumbnail(
                    media="https://tenor.com/view/undertale-asgore-nomercy-gif-4931669",
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="## Roles Construction\n- Select Your Staff Hierarchy\n- ⚠️ Your previous staff hierarchy will be cleared by doing so."),
            discord.ui.ActionRow(
                RoleSelector(self.interactor)
            ),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(self.container)
