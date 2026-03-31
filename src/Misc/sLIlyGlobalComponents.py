import discord
import Config.sBotDetails as Config

from discord.ext import commands



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