import discord
import LilyModeration.db.sLilyModerationDatabaseAccess as LMDA

from Misc.sLilyEmbed import simple_embed

from typing import Optional

import Config.sBotDetails as Config

class Leaderboard(discord.ui.LayoutView):
    def __init__(self, bot: discord.Member, leaderboard_type: str, ms_data: list):
        super().__init__(timeout=None)

        self.leaderboard_type = leaderboard_type
        self.ms_data = ms_data

        self.bot = bot

        self.top_ms_staff: int = self.ms_data[0].get("moderator_id")
        self.least_ms_staff: int = self.ms_data[-1].get("moderator_id")

        self.leaderboard_value = ""

        for data in self.ms_data:
            moderator_id: int = data.get("moderator_id")
            ms: int = data.get("ms")

            self.leaderboard_value += f"- **({ms}ms)** <@{moderator_id}>\n"


        self.container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content="## Moderation Statistics Leaderboard"),
                discord.ui.TextDisplay(content=f"- Shows the leaderboard based on,\n  - **(mod_logs)** <@{self.bot.id}>"),
                discord.ui.TextDisplay(content=f"> **Top MS Staff** - <@{self.top_ms_staff}>\n> **Least MS Staff** - <@{self.least_ms_staff}>"),
                accessory=discord.ui.Thumbnail(
                    media=bot.display_avatar.url,
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"### __{self.leaderboard_type.title()} Leaderboard__"),
            discord.ui.TextDisplay(content=self.leaderboard_value),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(self.container)

class ModerationInsights(discord.ui.LayoutView):
    def __init__(self, bot: discord.Member):
        super().__init__(timeout=300)

        self.bot = bot

        self.message = None

        self.ms_leaderboard_options = discord.ui.Select(
            custom_id="ms_leaderboard_options",
            options=[
                discord.SelectOption(label="Daily", value="daily"),
                discord.SelectOption(label="Weekly", value="weekly"),
                discord.SelectOption(label="Monthly", value="monthly"),
                discord.SelectOption(label="Total", value="total"),
            ]
        )

        self.ms_leaderboard_options.callback = self.ms_leaderboard_options_callback

        self.container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(content="## Staff Moderation Insights"),
                discord.ui.TextDisplay(content="- Overview of Moderation data that helps the Management Team maintain a safe and well managed staff environment."),
                accessory=discord.ui.Thumbnail(
                    media=self.bot.display_avatar.url,
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="### Moderation Statistics Leaderboard"),
            discord.ui.ActionRow(self.ms_leaderboard_options),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(self.container)
    
    async def ms_leaderboard_options_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        selected_ms_leaderboard_option = self.ms_leaderboard_options.values[0]
        ms_data_dict: dict = await LMDA.fetch_moderation_leaderboard(interaction.guild.id, selected_ms_leaderboard_option)


        ms_data: list = ms_data_dict.get("moderator_statistics_leaderboard", [])
        if not ms_data:
            await interaction.followup.send(embed=simple_embed("No Moderation Data Available", 'cross'))
            return


        view = Leaderboard(self.bot, selected_ms_leaderboard_option, ms_data)
        await interaction.followup.send(view=view, ephemeral=True)

    async def on_timeout(self):
        self.ms_leaderboard_options.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass

def ban_embed(moderator: discord.Member, reason: Optional[str], appealLink: Optional[str], server_name: str) -> discord.Embed:
    embed = (
        discord.Embed(
            color=0xFFFFFF,
            title=f"{Config.emoji['arrow']} You Have Been Banned!",
        )
        .set_image(url=Config.img['border'])
        .add_field(
            name=f"{Config.emoji['bookmark']} Reason",
            value=reason,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['shield']} Moderator",
            value=moderator.name,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['bot']} Server",
            value=server_name,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['ban_hammer']} Appeal Your Ban Here",
            value=f"If you think your ban was wrongly done, please make an appeal here: {appealLink}",
            inline=False,
        )
    )
    return embed

def mute_embed(moderator: discord.Member, reason: Optional[str], guild_name: str) -> discord.Embed:
    embed = discord.Embed(
                    color=0xFFFFFF,
                    title=f"{Config.emoji['arrow']} YOU HAVE BEEN MUTED!",
                )
    embed.set_image(url=Config.img['border'])
    embed.add_field(
        name=f"{Config.emoji['bookmark']} Reason",
        value=reason,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['shield']} Moderator",
        value=moderator.mention,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['bot']} Server",
        value=guild_name,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['ban_hammer']} Appeal Your Ban Here",
        value=f"If you think your mute was wrongly done, please make an appeal here: {Config.appeal_server_link}",
        inline=False,
    )
    return embed

def warn_embed(moderator: discord.Member, reason: Optional[str], guild_name: str) -> discord.Embed:
    embed = discord.Embed(
        color=16777215,
        title=f"{Config.emoji['arrow']} You Have Been Warned!",
    )
    embed.set_thumbnail(url=Config.img['warn'])
    embed.add_field(
        name=f"{Config.emoji['bookmark']} Reason",
        value=reason,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['shield']} Moderator",
        value=moderator.mention,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['bot']} Server",
        value=guild_name,
        inline=False,
    )

    return embed