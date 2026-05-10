import discord
from discord.ext import commands
import LilyModeration.db.sLilyModerationDatabaseAccess as LMDA

from Misc.sLilyEmbed import simple_embed

from typing import Optional, Callable

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
        name=f"{Config.emoji['bot']} Server",
        value=guild_name,
        inline=False,
    )

    return embed

class ModerationQueueClear(discord.ui.View):
    def __init__(self, moderation_queue: list[dict], interactor: discord.Member, ban_callback: Callable):
        super().__init__(timeout=300)
        self.moderation_queue = moderation_queue
        self.interactor: discord.Member = interactor
        self.ban_callback = ban_callback
        self.message: Optional[discord.Message] = None

    @discord.ui.button(
    label="Clear Moderation Queue",
    style=discord.ButtonStyle.danger
)
    async def clear_queue(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.interactor.id:
            return await interaction.response.send_message(
                embed=simple_embed("You cannot interact with this!", 'cross'),
                ephemeral=True
            )

        await interaction.response.defer(thinking=True)

        summary = await self.ban_callback(interaction, self.moderation_queue)

        for child in self.children:
            child.disabled = True

        if self.message:
            await self.message.delete()

        await interaction.followup.send(
            embed=simple_embed(f"Queue Processed:\n{summary}"),
            view=self,
        )

def moderation_queue_embed(ctx: commands.Context, moderation_queue: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        color=16777215,
        title="Moderation Queue",
        description="- If a staff member can’t perform an action, it will be added to this queue. Another staff member who has permission can then review and complete it.\n### Queue List",
    )
    embed.set_thumbnail(url=ctx.me.display_avatar.url)


    items_example = {
        "mod_type": "ban",
        "moderator_id": 12232323,
        "target_user_id": 987986978,
        "reason": "Hello what the hell!",
        "message_source": "url"
    }


    for i, items in enumerate(moderation_queue):
        embed.add_field(
                name=f"📌 Queue #{i} • {items.get("mod_type", "Not defined")}",
                value=f"> - User: <@{items.get("target_user_id")}>\n> - Moderator: <@{items.get("moderator_id")}>\n> - Reason: {items.get("reason")}\n> - [Message]({items.get("message_source")})",
                inline=True,
            )
    
    return embed