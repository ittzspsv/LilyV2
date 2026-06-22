import discord
from discord.ext import commands
from src.core.utils.embeds.sLilyEmbed import simple_embed
from typing import Optional, Callable
from datetime import datetime, timezone
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from src.core.logging.components.logging_components import ProofsComponentCommandModal

import src.core.configs.sBotDetails as Config
import io

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
    def __init__(self, bot: discord.Member, db: BotGlobalsDatabaseAccess):
        super().__init__(timeout=300)

        self.bot = bot
        self.message: Optional[discord.Message] = None
        self.logs_db: BotGlobalsDatabaseAccess = db

        self.ms_leaderboard_options = discord.ui.Select(
            custom_id="ms_leaderboard_options",
            options=[
                discord.SelectOption(label="Daily", value="daily", description="Displays moderation stat leaderboard from the last 24 hours."),
                discord.SelectOption(label="Weekly", value="weekly", description="Displays moderation stat leaderboard for the current week"),
                discord.SelectOption(label="Monthly", value="monthly", description="Displays moderation stat leaderboard for the current month"),
                discord.SelectOption(label="Total", value="total", description="Displays moderation stat leaderboard for the current month"),
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
        if interaction.guild is None:
            await interaction.response.send_message(embed=simple_embed("Can only be interacted inside an guild", 'cross'), ephemeral=True)
            return 

        if self.logs_db is None:
            await interaction.response.send_message(embed=simple_embed("Internal Failure", 'cross'), ephemeral=True)
            return 
        await interaction.response.defer()

        selected_ms_leaderboard_option = self.ms_leaderboard_options.values[0]
        ms_data_dict: dict = await self.logs_db.fetch_moderation_leaderboard(interaction.guild.id, selected_ms_leaderboard_option)


        ms_data: list = ms_data_dict.get("moderator_statistics_leaderboard", [])
        if not ms_data:
            await interaction.followup.send(embed=simple_embed("No Moderation Data Available", 'cross'))
            return


        view = Leaderboard(self.bot, selected_ms_leaderboard_option, ms_data)
        await interaction.followup.send(view=view, ephemeral=True)

    async def on_timeout(self):
        self.ms_leaderboard_options.disabled = True
        if self.message is not None:
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

def build_ms_embed(
    moderator: discord.Member | discord.User,
    logs: list[dict],
    stats: dict,
    total_logs: int,
    page_start: int = 0
) -> list[discord.Embed]:

    embed1 = discord.Embed(
        title=f"{Config.emoji['arrow']} {moderator.display_name}'s Moderation Statistics",
        description=(
            f"### Total Stats : **{total_logs}**\n"
            f"- Mutes : **{stats['mute']['total']}**\n"
            f"- Warns: **{stats['warn']['total']}**\n"
            f"- Quarantines: **{stats['quarantine']['total']}**\n"
            f"- Bans: **{stats['ban']['total']}**"
        ),
        colour=16777215
    )

    embed1.set_thumbnail(
        url=moderator.avatar.url if moderator.avatar else Config.img['member']
    )
    embed1.set_image(url=Config.img['border'])

    embed2 = discord.Embed(
        title="Statistics Overview",
        colour=16777215
    )

    embed2.set_image(url=Config.img['border'])

    actions = ["mute", "warn", "ban", "quarantine"]

    for action in actions:
        embed2.add_field(
            name=f"{action.title()} • Today",
            value=stats[action]["today"],
            inline=True
        )
        embed2.add_field(
            name=f"{action.title()} • 7d",
            value=stats[action]["7d"],
            inline=True
        )
        embed2.add_field(
            name=f"{action.title()} • 30d",
            value=stats[action]["30d"],
            inline=True
        )

    logs_text = ""

    for index, log in enumerate(logs, start=page_start + 1):
        ts_unix = int(log["timestamp"])

        logs_text += (
            f"📌 **Log #{index} - {log['mod_type'].title()}**\n"
            f"> {Config.emoji['member']} User: <@{log['target_user_id']}>\n"
            f"> {Config.emoji['bookmark']} Reason: {log['reason']}\n"
            f"> {Config.emoji['clock']} Time: <t:{ts_unix}:R>\n\n"
        )

    embeds = [embed1, embed2]

    if logs_text:
        embed_logs = discord.Embed(
            title=f"{Config.emoji['arrow']} Moderator Action Logs",
            description=logs_text,
            colour=16777215
        ).set_image(
            url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png"
        )

        embeds.append(embed_logs)

    return embeds

def build_mod_logs_embed(
    user: discord.User | discord.Member,
    display_logs: list[dict],
    mod_type_counts: dict,
    total_count: int,
    page_start: int = 0
) -> list[discord.Embed]:

    now = datetime.now(timezone.utc)

    embed_summary = (
        discord.Embed(
            color=16777215,
            title=f"{Config.emoji['arrow']} {user.display_name}'s Moderation Logs",
        )
        .set_thumbnail(url=user.avatar.url if user.avatar else Config.img['member'])
        .set_image(url=Config.img['border'])
        .add_field(name="Total Logs", value=str(total_count), inline=True)
        .add_field(name="Date", value=now.strftime("%Y-%m-%d"), inline=True)
    )

    summary_text = "\n".join(
        f"- {action.title()}s: `{count}`"
        for action, count in mod_type_counts.items()
    )

    embed_summary.add_field(
        name="Logs Summary",
        value=summary_text or "No actions recorded",
        inline=False
    )

    embed_logs = (
        discord.Embed(
            color=16777215,
            title=f"{Config.emoji['arrow']} Log's Overview",
        )
        .set_thumbnail(url=Config.img['logs'])
        .set_image(url=Config.img['border'])
    )

    for index, log in enumerate(display_logs, start=page_start + 1):

        ts = log.get("timestamp")

        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

        ts_unix = int(dt.timestamp())
        reason_text = log.get("reason") or "No reason provided"

        embed_logs.add_field(
            name=f"📌 Log #{log.get('case_id')} • {log['mod_type'].title()}",
            value=(
                f"> {Config.emoji['shield']} Moderator : <@{log['moderator_id']}>\n"
                f"> {Config.emoji['pencil']} Reason : **{reason_text}**\n"
                f"> {Config.emoji['clock']} Time : <t:{ts_unix}:R>"
            ),
            inline=False
        )

    return [embed_summary, embed_logs]

def build_mod_logs_embed_absolute(
    username: str,
    avatar: str,
    display_logs: list[dict],
    mod_type_counts: dict,
    total_count: int,
    page_start: int = 0
) -> list[discord.Embed]:

    now = datetime.now(timezone.utc)

    embed_summary = (
        discord.Embed(
            color=16777215,
            title=f"{Config.emoji['arrow']} {username}'s Moderation Logs",
        )
        .set_thumbnail(url=avatar if avatar else Config.img['member'])
        .set_image(url=Config.img['border'])
        .add_field(name="Total Logs", value=str(total_count), inline=True)
        .add_field(name="Date", value=now.strftime("%Y-%m-%d"), inline=True)
    )

    summary_text = "\n".join(
        f"- {action.title()}s: `{count}`"
        for action, count in mod_type_counts.items()
    )

    embed_summary.add_field(
        name="Logs Summary",
        value=summary_text or "No actions recorded",
        inline=False
    )

    embed_logs = (
        discord.Embed(
            color=16777215,
            title=f"{Config.emoji['arrow']} Log's Overview",
        )
        .set_thumbnail(url=Config.img['logs'])
        .set_image(url=Config.img['border'])
    )

    for index, log in enumerate(display_logs, start=page_start + 1):

        ts = log.get("timestamp")

        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

        ts_unix = int(dt.timestamp())
        reason_text = log.get("reason") or "No reason provided"

        embed_logs.add_field(
            name=f"📌 Log #{log.get('case_id')} • {log['mod_type'].title()}",
            value=(
                f"> {Config.emoji['shield']} Moderator : <@{log['moderator_id']}>\n"
                f"> {Config.emoji['pencil']} Reason : **{reason_text}**\n"
                f"> {Config.emoji['clock']} Time : <t:{ts_unix}:R>"
            ),
            inline=False
        )

    return [embed_summary, embed_logs]

class ProofsView(discord.ui.View):
    def __init__(self, logs, logging_channel_id: int, guild_id: int):
        super().__init__(timeout=180)

        self.logs_channel_id = logging_channel_id
        self.channel = None
        self.guild = None
        self._guild_id: int = guild_id

        self.options = []
        self.proofs = {}
        for log in logs:
            if log["proofs_reference"]:
                self.options.append(
                    discord.SelectOption(label=f"Proofs #{log['case_id']}", description="All proofs associated with that case", value=log["case_id"])
                )

                self.proofs[log['case_id']] = log["proofs_reference"]

        self.proofs_selector = discord.ui.Select(
            placeholder="Show Proofs...",
            min_values=1,
            max_values=1,
            options=self.options
        )

        self.proofs_selector.callback = self.proofs_selector_callback
        self.add_item(self.proofs_selector)

    async def proofs_selector_callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return
        case_id = int(self.proofs_selector.values[0])
        proofs_msg_id = self.proofs[case_id]

        await interaction.response.defer()


        if not self.logs_channel_id:
            await interaction.followup.send(
                embed=simple_embed(
                    "Proofs cannot be retrieved: logging channel is not configured.",
                    "cross"
                ),
                ephemeral=True
            )
            return
        
        if self.channel is None:
            if self._guild_id == interaction.guild.id:

                self.channel = interaction.guild.get_channel(self.logs_channel_id)

                if self.channel is None:
                    try:
                        self.channel = await interaction.guild.fetch_channel(self.logs_channel_id)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        await interaction.followup.send(
                            embed=simple_embed(
                                "Proofs cannot be retrieved: logging channel is missing or inaccessible.",
                                "cross"
                            ),
                            ephemeral=True
                        )
                        return
            else:
                if self.guild is None:
                    self.guild =  interaction.client.get_guild(self._guild_id)

                    if self.guild is None:
                        try:
                            self.guild = await interaction.client.fetch_guild(self._guild_id)
                        except (discord.NotFound, discord.HTTPException):
                             await interaction.followup.send(
                            embed=simple_embed(
                                "Proofs cannot be retrieved: supplementary guild is missing or inaccessible.",
                                "cross"
                            ),
                            ephemeral=True
                        )
                        return
                    
                self.channel = self.guild.get_channel(self.logs_channel_id)

                if self.channel is None:
                    try:
                        self.channel = await self.guild.fetch_channel(self.logs_channel_id)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        await interaction.followup.send(
                            embed=simple_embed(
                                "Proofs cannot be retrieved: logging channel is missing or inaccessible.",
                                "cross"
                            ),
                            ephemeral=True
                        )
                        return

            
        if not isinstance(self.channel, discord.TextChannel):
            return

        files: list[discord.File] = []

        for message_id in proofs_msg_id:
            try:
                message = await self.channel.fetch_message(message_id)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                await interaction.followup.send(
                    embed=simple_embed(
                        "Missing permission to read messages in the logging channel.",
                        "cross"
                    ),
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                continue

            for attachment in message.attachments:
                try:
                    data = await attachment.read()
                    files.append(
                        discord.File(
                            fp=io.BytesIO(data),
                            filename=attachment.filename
                        )
                    )
                except discord.HTTPException:
                    continue

        if not files:
            await interaction.followup.send(
                embed=simple_embed(
                    "No valid proof attachments were found for this case.",
                    "cross"
                ),
                ephemeral=True
            )
            return

        await interaction.followup.send(
            content=f"Proofs for case `{case_id}`",
            files=files,
            ephemeral=True
        )

class CaseProofsView(discord.ui.View):
    def __init__(self, case_id: int, controller, message: Optional[discord.Message]):
        super().__init__(timeout=300)

        self.case_id = case_id
        self.controller = controller
        self.message = message

    @discord.ui.button(
        label="Attach Proofs",
        style=discord.ButtonStyle.secondary
    )
    async def click_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        assert isinstance(self.message, discord.Message)
        await interaction.response.send_modal(ProofsComponentCommandModal(controller=self.controller, case_id=self.case_id, cmd_view=self, msg=self.message))