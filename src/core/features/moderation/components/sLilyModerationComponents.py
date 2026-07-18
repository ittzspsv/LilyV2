from __future__ import annotations

import discord
from src.core.utils.embeds.sLilyEmbed import simple_embed
from typing import Optional, cast, Any, TYPE_CHECKING, List, Dict
from datetime import datetime, timezone
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from src.core.logging.components.logging_components import ProofsComponentCommandModal

import src.core.configs.sBotDetails as Config
import io
from src.core.configs.sBotDetails import img
import re

if TYPE_CHECKING:
    from .....lily import Lily

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
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="### Moderation Analysis"),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="attachment://moderation_analytics.png",
                ),
            ),
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

from typing import Optional
import discord


def action_log(
    action: str,
    reason: Optional[str],
    guild_name: str,
) -> discord.Embed:
    action = action.lower()

    titles = {
        "ban": f"{Config.emoji['arrow']} You Have Been Banned!",
        "mute": f"{Config.emoji['arrow']} You Have Been Muted!",
        "quarantine": f"{Config.emoji['arrow']} You Have Been Quarantined!",
        "warn": f"{Config.emoji['arrow']} You Have Been Warned!",
    }

    if action not in titles:
        raise ValueError(f"Unknown action '{action}'. Must be one of {list(titles)}.")

    embed = discord.Embed(
        color=0xFFFFFF,
        title=titles[action],
    )
    if action == "warn":
        embed.set_thumbnail(url=Config.img['warn'])
    else:
        embed.set_image(url=Config.img.get(action, Config.img['border']))

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

        ts: str = cast(str, log.get("timestamp"))

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

        ts = cast(str, log.get("timestamp"))

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

class AppealForumCustomize(discord.ui.Modal):
    name = discord.ui.Label(
            text="Appeal Config",
            description="Appeal config should be in json",
            component=discord.ui.TextInput(
                style = discord.TextStyle.paragraph,
                required=True,
                placeholder="Enter a json config",
                default= """
                    [
                        {
                            "label": "Why should we remove the punishment?",
                            "description": "Explain why the punishment should be removed and how you will follow the rules in future."
                        },
                        {
                            "label": "Why did this happen?",
                            "description": "Explain what caused the punishment and what you will do to prevent it from happening again."
                        }
                    ]
                """
            )
        )
    
    def __init__(self, bot_db: BotGlobalsDatabaseAccess) -> None:
        super().__init__(title="Appeal Forum")

        self.bot_db = bot_db

    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        assert isinstance(self.name.component, discord.ui.TextInput)
        await self.bot_db.upsert_appeal_forum(
            interaction.guild.id,
            self.name.component.value
        )

        await interaction.response.send_message(
            embed=simple_embed("Successfully Updated Appeal Forum Config!")
        )

class AppealModal(discord.ui.Modal):
    def __init__(
        self,
        db: BotGlobalsDatabaseAccess,
        case_id: int,
        guild_id: int,
        config: List[Dict[str, Any]],
        _case
    ) -> None:
        super().__init__(
            title="Moderation Appeal",
            timeout=None,
        )

        self.db = db
        self.case_id = case_id
        self.guild_id = guild_id
        self.case = _case

        self.fields: list[tuple[str, discord.ui.TextInput]] = []

        for question in config[:5]:
            text_input = discord.ui.TextInput(
                style=discord.TextStyle.paragraph,
                required=True,
                placeholder="Enter your answer...",
                max_length=2000,
            )

            label = discord.ui.Label(
                text=question["label"],
                description=question.get("description"),
                component=text_input,
            )

            self.fields.append((question["label"], text_input))
            self.add_item(label)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {
            label: text_input.value
            for label, text_input in self.fields
        }

        await interaction.response.defer()
        guild = interaction.client.get_guild(self.guild_id)

        if guild is None:
            try:
                guild = await interaction.client.fetch_guild(self.guild_id)
            except discord.NotFound:
                await interaction.followup.send(
                    embed=simple_embed("Internal Error", 'cross')
                )
                return
            except discord.Forbidden:
                await interaction.followup.send(
                    embed=simple_embed("Internal Error", 'cross')
                )
                return

        appeal_channel_id: int | None = self.db.get_channel(
            self.guild_id,
            "moderation_appeal",
        )

        if appeal_channel_id is None:
            await interaction.followup.send(
                embed=simple_embed("The moderation appeal forum has not been configured.", "cross"),
                ephemeral=True,
            )
            return

        appeal_forum = guild.get_channel(appeal_channel_id)

        if appeal_forum is None:
            try:
                appeal_forum = await guild.fetch_channel(appeal_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await interaction.followup.send(
                    embed=simple_embed(
                        "The configured moderation appeal forum could not be found.",
                        "cross",
                    ),
                    ephemeral=True,
                )
                return
            
        assert isinstance(appeal_forum, discord.ForumChannel)

        """ Setup an embed """
        appeal_embed = discord.Embed(
            title="Case Appeal",
            description=f"- User: {interaction.user.mention}\n- ID: {interaction.user.id}",
            color=16777215,
        )

        for question, answer in answers.items():
            appeal_embed.add_field(
                name=question,
                value=answer[:1024] or "*No response*",
                inline=False,
            )

        appeal_embed.set_footer(text=f"Case ID: {self.case_id}")
        appeal_embed.set_image(url=img["border"])


        case_info_embed = discord.Embed(
            title="Case Information",
            color=16777215
        )

        case_info_embed.add_field(
            name="Case Type",
            value=self.case['mod_type'],
            inline=False
        )

        case_info_embed.add_field(
            name="Reason",
            value=self.case["reason"] or "No reason Provided",
            inline=False
        )

        case_info_embed.add_field(
            name="Moderator",
            value=f"<@{self.case['moderator_id']}>",
            inline=False
        )

        case_info_embed.set_image(url=img["border"])

        """ Create a thread inside that forum and post all of these"""
        avatar = await interaction.user.display_avatar.to_file(
            filename="avatar.png"
        )

        tag = discord.utils.get(
            appeal_forum.available_tags,
            name="Pending",
        )

        thread, message = await appeal_forum.create_thread(
            name=f"{interaction.user.display_name}'s {self.case['mod_type'].title()} Appeal",
            file=avatar,
            applied_tags=[tag] if tag else [],
            embeds=[appeal_embed, case_info_embed]
        )

        assert interaction.client.user is not None
        await thread.send(
            content=f"- To reply to the appealer, mention me (<@{interaction.client.user.id}>) and type your message.",
        )

        await self.db.create_appeal(
            self.case_id,
            thread.id
        )

        """ Get Proofs """
        case_proofs = await self.db.get_proof_references(self.guild_id, self.case_id)
        attachments: list[discord.File] = []

        if case_proofs:
            _logging_channel = self.db.get_channel(self.guild_id, "logs_channel")

            if _logging_channel is not None:
                logging_channel = guild.get_channel(int(_logging_channel))

                if logging_channel is None:
                    try:
                        logging_channel = await guild.fetch_channel(int(_logging_channel))
                    except (discord.NotFound, discord.Forbidden):
                        logging_channel = None

                if logging_channel is not None:
                    for message_id in case_proofs:
                        try:
                            assert isinstance(logging_channel, discord.TextChannel)
                            message = await logging_channel.fetch_message(message_id)
                        except (discord.NotFound, discord.Forbidden):
                            continue

                        for attachment in message.attachments:
                            attachments.append(await attachment.to_file())

        if len(case_proofs) > 0:
            await thread.send(
                content=f"### Case Proofs",
                files=attachments
            )

        await interaction.followup.send(
            embed=simple_embed(
                "Your appeal has been submitted successfully. Our staff will review it as soon as possible. Thank you for your patience."
            ),
            ephemeral=True
        )

        await interaction.followup.send(
            content="### You may continue sending messages in this DM if you'd like to provide any additional information.",
            ephemeral=True
        )

class AppealButton(discord.ui.DynamicItem[discord.ui.Button], template=r'button:case:(?P<id>[0-9]+)'):
    def __init__(self, case_id: int | None) -> None:
        super().__init__(
            discord.ui.Button(
                label='Appeal',
                style=discord.ButtonStyle.danger,
                custom_id=f'button:case:{case_id}',
            )
        )
        self.case_id: int | None = case_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Item[Any], match: re.Match[str], /):
        case_id = int(match['id'])
        return cls(case_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        db: Optional[BotGlobalsDatabaseAccess] = cast("Lily", interaction.client).db
        if db is None:
            return
        
        assert self.case_id is not None

        """ Check the validity of the case first """
        _case = await db.get_case(self.case_id)
        if _case is None:
            await interaction.response.send_message(
                embed=simple_embed(
                    "Maybe This case has been already resolved???",
                    "cross",
                ),
                ephemeral=True
            )

            return
        
        """ Check the status of the case """
        appeal_exists = await db.appeal_exists(self.case_id)
        print(appeal_exists)
        if appeal_exists:
            appeal_status = await db.get_appeal_status(self.case_id)
            print(appeal_status)

            if appeal_status == "pending":
                await interaction.response.send_message(
                    embed=simple_embed(
                        "You have already created an appeal for this case.",
                        "cross",
                    ),
                    ephemeral=True,
                )

                return

            elif appeal_status == "accepted":
                await interaction.response.send_message(
                    embed=simple_embed(
                        "This appeal has been accepted.",
                        "cross",
                    ),
                    ephemeral=True,
                )
            
                return

            elif appeal_status in ("denied", "rejected"):
                await interaction.response.send_message(
                    embed=simple_embed(
                        "This appeal has been denied.",
                        "cross",
                    ),
                    ephemeral=True,
                )

                return

        else:
            _config = await db.get_appeal_forum_config(_case["guild_id"])
            await interaction.response.send_modal(AppealModal(
                db,
                self.case_id,
                _case["guild_id"],
                _config,
                _case
            )
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