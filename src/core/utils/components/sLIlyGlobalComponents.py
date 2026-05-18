import discord
from discord.utils import MISSING
import core.configs.sBotDetails as Config

from discord.ext import commands
from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.utils.embeds.sLilyEmbed import simple_embed



from typing import List

class CommandInfo(discord.ui.LayoutView):
    def __init__(self, ctx: commands.Context ,cmd_name: str, cmd_usage: List[str]):
        super().__init__()

        self.cmd_name = cmd_name
        self.cmd_usage: List[str] = cmd_usage

        self.formatted_usage: str = "\n".join(f"- {Config.bot_command_prefix}{cmd}" for cmd in self.cmd_usage)
        self.container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content=f"## {self.cmd_name}"),
                discord.ui.TextDisplay(content=f"- {ctx.command.description}"),
                discord.ui.TextDisplay(content=f"### Command Usage\n{self.formatted_usage}"),
                accessory=discord.ui.Thumbnail(
                    media=ctx.me.display_avatar.url,
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        )

        self.add_item(self.container)


class RoleCustomizationModal(discord.ui.Modal):
    def __init__(self, role_id: int ,db: BotGlobalsDatabaseAccess) -> None:
        super().__init__(title="Role Configuration")

        self.db = db
        self.role_id = role_id

    ban_limit = discord.ui.TextInput(
        label='Ban Limit',
        style=discord.TextStyle.short,
        placeholder='Hardcoded Limit that resets 24 hrs',
        required=True,
        max_length=5,
        default="0"
    )

    ban_queue_option = discord.ui.Label(
        text='Ban Queue',
        description='Should ban`s undergo a validation before action?',
        component=discord.ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label="Yes", value="1", description="Their bans require approval through /moderation queue before execution."),
                discord.RadioGroupOption(label="No", value="0", description="Their bans are executed instantly without queue validation.")
            ]
        )
    )

    assignment_scope = discord.ui.Label(
        text='Role Assignment Scope',
        description='Choose how broadly this role can assign roles',
        component=discord.ui.RadioGroup(
            options=[
                discord.RadioGroupOption(
                    label="None",
                    value="none",
                    description="This role cannot assign any roles."
                ),
                discord.RadioGroupOption(
                    label="All",
                    value="all",
                    description="This role can assign all available roles."
                ),
                discord.RadioGroupOption(
                    label="Except",
                    value="except",
                    description="This role can assign all roles except selected restricted roles."
                ),
                discord.RadioGroupOption(
                    label="Specified",
                    value="specific",
                    description="This role can only assign specifically selected roles."
                ),
            ]
        )
    )

    assignment_roles = discord.ui.Label(
        text='Role Assignments',
        description='Select roles allowed under the chosen assignment scope',
        component=discord.ui.RoleSelect(
            min_values=1,
            max_values=25,
            required=True
        )
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return
        
        await interaction.response.defer()

        assert isinstance(self.ban_limit, discord.ui.TextInput)
        assert isinstance(self.ban_queue_option.component, discord.ui.RadioGroup)
        assert isinstance(self.assignment_scope.component, discord.ui.RadioGroup)
        assert isinstance(self.assignment_roles.component, discord.ui.RoleSelect)



        response = await self.db.configure_role(
            interaction.guild.id,
            self.role_id,
            int(self.ban_limit.value),
            int(self.ban_queue_option.component.value or "0"),
            self.assignment_scope.component.value or "none",
            {role.id for role in (self.assignment_roles.component.values or [])}
        )

        if response.get("success"):
            await interaction.followup.send(embed=simple_embed(str(response.get("message"))))
        else:
            await interaction.followup.send(embed=simple_embed(str(response.get("message")), 'cross'))


