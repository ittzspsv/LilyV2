from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, cast
import re

import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter
from discord.utils import MISSING

from src.core.configs.sBotDetails import (
    appeal_server_link,
    emoji,
    img,
)

from src.core.features.moderation.components.sLilyModerationComponents import (
    ProofsView,
    ban_embed,
    build_mod_logs_embed_absolute,
    mute_embed,
    warn_embed,
)

from src.core.features.moderation.utils.moderation_utils import (
    mute_parser,
)

from src.core.utils.embeds.sLilyEmbed import (
    simple_embed,
)

from src.core.utils.lily_utility import (
    utcnow,
)

from ..classes.ticketing_classes import (
    DatabaseAccess,
)



bot = None

""" Modals for ticket panel moderation. This is indeed redundant, but we only have access to logging database, so we need to evaluate it again!"""
class MuteModal(discord.ui.Modal):
    duration = discord.ui.Label(
        text="Duration",
        description="Enter the duration of the mute. Example: (3d, 1hr, 22m)",
        component=discord.ui.TextInput(
            style=discord.TextStyle.short,
            max_length=50,
        )
    )

    reason = discord.ui.Label(
        text="Reason",
        description="Enter the reason for the mute",
        component=discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            max_length=512,
        )
    )

    footer = discord.ui.TextDisplay(
        'Note: Any proof attachments provided by the user will be automatically appended.'
    )


    def __init__(self, db: DatabaseAccess, member_id: int, proofs: List[str]) -> None:
        super().__init__(title="Mute User")

        self.db = db

        self.member_id = member_id
        self.proofs = proofs

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.duration.component, discord.ui.TextInput)
        assert isinstance(self.reason.component, discord.ui.TextInput)

        if interaction.guild is None:
            await interaction.response.send_message(embed=simple_embed("Command requires guild object inorder to execute", 'cross'), ephemeral=True)
            return
        
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message(embed=simple_embed("Command requires member object inorder to execute", 'cross'), ephemeral=True)
            return
        
        user: Optional[discord.Member] = None
        try:
            user = await interaction.guild.fetch_member(self.member_id)
        except discord.NotFound:
            await interaction.response.send_message(embed=simple_embed("User is not in the guild!", 'cross'), ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message(embed=simple_embed("Failed to fetch the member due to network error!", 'cross'), ephemeral=True)
            return
        except Exception:
            await interaction.response.send_message(embed=simple_embed("Failed to fetch the member due to unknown error!", 'cross'), ephemeral=True)
            return
        
        await interaction.response.defer()
        
        if user.timed_out_until and user.timed_out_until > discord.utils.utcnow():
            await interaction.followup.send(embed=simple_embed("This user is already muted", 'cross'), ephemeral=True)
            return

        if user.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send(embed=simple_embed("I cannot mute this user", 'cross'), ephemeral=True)
            return

        if user.top_role >= interaction.user.top_role:
            await interaction.followup.send(embed=simple_embed("I cannot mute a user with a role equal to or higher than yours.", 'cross'), ephemeral=True)
            return

        if user.id in {interaction.guild.owner_id, interaction.guild.me.id, interaction.user.id}:
            await interaction.followup.send(embed=simple_embed("Exception!. Stupid action detected errno 77777", 'cross'), ephemeral=True)
            return
        
        seconds = mute_parser(self.duration.component.value)
        until = utcnow() + timedelta(seconds=seconds)

        try:
            embed = mute_embed(interaction.user, self.reason.component.value, interaction.guild.name)
            await user.send(embed=embed)
        except Exception as e:
            print("DM failed:", e)

        await user.edit(timed_out_until=until, reason=self.reason.component.value)
        await self.db.logging_controller.log_moderation_action(interaction, interaction.user.id, user.id, "mute", self.reason.component.value, self.proofs)

        await interaction.followup.send(embed=simple_embed(
            f"Muted: <@{user.id}>"
        ))

class BanModal(discord.ui.Modal):
    reason = discord.ui.Label(
        text="Reason",
        description="Enter the reason for the ban",
        component=discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            max_length=512,
        )
    )

    footer = discord.ui.TextDisplay(
        'Note: Any proof attachments provided by the user will be automatically appended.'
    )


    def __init__(self, db: DatabaseAccess, member_id: int, proofs: List[str]) -> None:
        super().__init__(title="Ban User")

        self.db = db

        self.member_id = member_id
        self.proofs = proofs

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.reason.component, discord.ui.TextInput)

        if interaction.guild is None:
            await interaction.response.send_message(embed=simple_embed("Command requires guild object inorder to execute", 'cross'), ephemeral=True)
            return
        
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message(embed=simple_embed("Command requires member object inorder to execute", 'cross'), ephemeral=True)
            return
        
        
        jail_value = self.db.bot_db.global_config.jail if self.db.bot_db.global_config else 1
        role_ids = [str(r.id) for r in interaction.user.roles]
        if not role_ids:
            await interaction.response.send_message(embed=simple_embed("No permission.", 'cross'), ephemeral=True)
            return

        member: Optional[discord.Member] = None


        try:
            member = await interaction.guild.fetch_member(self.member_id)
        except discord.NotFound:
            await interaction.response.send_message(embed=simple_embed("User is not in the guild!", 'cross'), ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message(embed=simple_embed("Failed to fetch the member due to network error!", 'cross'), ephemeral=True)
            return
        except Exception:
            await interaction.response.send_message(embed=simple_embed("Failed to fetch the member due to unknown error!", 'cross'), ephemeral=True)
            return
        
        await interaction.response.defer()

        response = await self.db.bot_db.get_mod_queue_entry(member.id, interaction.guild.id)
        if response.get("success"):
            await interaction.followup.send(
                embed=simple_embed(
                    f"This user already has a pending action request from <@{response.get('moderator_id')}>.\n"
                    f"Check `/moderation_queue` for details.",
                    "cross"
                ),
                ephemeral=True
            )

            return

        if member.id == interaction.user.id:
            await interaction.followup.send(
                embed=simple_embed(
                    "You cannot moderate yourself.",
                    "cross"
                ),
                ephemeral=True
            )

            return

        if member.id == interaction.guild.me.id:
            await interaction.followup.send(
                embed=simple_embed(
                    "You cannot moderate the bot.",
                    "cross"
                ),
                ephemeral=True
            )

            return

        if member.id == interaction.guild.owner_id:
            await interaction.followup.send(
                embed=simple_embed(
                    "You cannot moderate the server owner.",
                    "cross"
                ),
                ephemeral=True
            )

            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send(
                embed=simple_embed(
                    "I cannot take action on this user because their role is higher than or equal to mine.",
                    "cross"
                ),
                ephemeral=True
            )

            return

        if member.top_role >= interaction.user.top_role:
            await interaction.followup.send(
                embed=simple_embed(
                    "You cannot take action on this user because their role is higher than or equal to yours.",
                    "cross"
                ),
                ephemeral=True
            )

            return
        author_roles = [role.id for role in interaction.user.roles if role.name != "@everyone"]
        status = await self.db.bot_db.get_ban_limit_status(interaction.guild.id, interaction.user.id, author_roles)

        if status.exceeded:
            await interaction.followup.send(embed=simple_embed(
                f"Daily limit exceeded.\n{status.remaining_time}", 'cross'
            ), ephemeral=True)

            return
        
        if self.db.bot_db.ban_queue(interaction.guild.id, author_roles):
            response = await self.db.bot_db.add_mod_queue(**{
                "guild_id"       : interaction.guild.id,
                "moderator_id"   : interaction.user.id,
                "target_user_id" : member.id,
                "mod_type"       : "quarantine" if jail_value == 1 else "ban",
                "reason"         : self.reason.component.value,
                "message_source" : interaction.message.jump_url if interaction.message else "No Messages Found",
            })

            try:
                await member.edit(
                    timed_out_until=datetime.now(timezone.utc) + timedelta(hours=6),
                    reason=f"{self.reason.component.value} | In Ban Queue",
                )
            except Exception:
                pass

            if response.get("success"):
                return await interaction.followup.send(embed=simple_embed(str(response.get("message"))), ephemeral=True)
                
        async def notify_and_log(action: str) -> int | None:
            assert isinstance(self.reason.component, discord.ui.TextInput)
            if interaction.guild is None:
                return

            if not isinstance(interaction.user, discord.Member):
                return
            
            try:
                await member.send(embed=ban_embed(
                    interaction.user, self.reason.component.value, appeal_server_link, interaction.guild.name
                ))
            except Exception:
                pass

            case_id = await self.db.logging_controller.log_moderation_action(
                interaction, interaction.user.id, member.id, action, self.reason.component.value, self.proofs.copy()
            )

            return case_id
        
        if jail_value == 0:
            await interaction.guild.ban(
                discord.Object(id=member.id),
                reason=f"By {interaction.user} | {self.reason.component.value}",
            )

            await notify_and_log("ban")        

            await interaction.followup.send(embed=simple_embed(
                f"Banned: <@{member.id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"
            ))
        else:
            quarantine_role = (
                    discord.utils.get(interaction.guild.roles, name="Quarantine")
                    or discord.utils.get(interaction.guild.roles, name="Prisoner")
                )

            if not quarantine_role or quarantine_role >= interaction.guild.me.top_role:
                await interaction.followup.send(embed=simple_embed("Quarantine role is higher than my role.", 'cross'), ephemeral=True)
                return

            if quarantine_role in member.roles:
                await interaction.followup.send(embed=simple_embed("Already quarantined.", 'cross'), ephemeral=True)
                return
            
            await member.add_roles(
                quarantine_role,
                reason=f"Quarantine by {interaction.user} | {self.reason.component.value}",
            )

            await notify_and_log("quarantine")

            """ If no proofs has been attached always send a button view to attach proofs """
            await interaction.followup.send(embed=simple_embed(
                f"Quarantined: <@{member.id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"
            ))
            
class WarnModal(discord.ui.Modal):
    reason = discord.ui.Label(
        text="Reason",
        description="Enter the reason for the warn",
        component=discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            max_length=512,
        )
    )

    footer = discord.ui.TextDisplay(
        'Note: Any proof attachments provided by the user will be automatically appended.'
    )


    def __init__(self, db: DatabaseAccess, member_id: int, proofs: List[str]) -> None:
        super().__init__(title="Warn User")

        self.db = db

        self.member_id = member_id
        self.proofs = proofs

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(embed=simple_embed("Command requires guild object inorder to execute", 'cross'), ephemeral=True)
            return
        
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message(embed=simple_embed("Command requires member object inorder to execute", 'cross'), ephemeral=True)
            return
        
        try:
            await interaction.response.defer()

            assert isinstance(self.reason.component, discord.ui.TextInput)
            member: discord.Member = await interaction.guild.fetch_member(self.member_id)

            await interaction.followup.send(embed=simple_embed(f"{member.mention} has been warned"))

            await self.db.logging_controller.log_moderation_action(interaction, interaction.user.id, member.id, "warn", self.reason.component.value, self.proofs)

            embed = warn_embed(interaction.user, self.reason.component.value, interaction.guild.name)
            try:
                await member.send(embed=embed)
            except Exception as e:
                print(e)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            await interaction.followup.send(embed=simple_embed("Failed to warn the user. Maybe they left?", 'cross'), ephemeral=True)

class TicketRatingModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="Ticket Feedback", timeout=600)

    rating = discord.ui.Label(
        text="Ticket Support Rating",
        description="Share your experience and rate the support you received!",
        component=discord.ui.RadioGroup(
            required=True,
            options=[
                discord.RadioGroupOption(
                    label="Poor",
                    description="Support was unsatisfactory, slow, or failed to resolve the issue."
                ),
                discord.RadioGroupOption(
                    label="Fair",
                    description="Some help was provided, but overall experience was below expectations."
                ),
                discord.RadioGroupOption(
                    label="Good",
                    description="Issue was handled adequately with acceptable service."
                ),
                discord.RadioGroupOption(
                    label="Great",
                    description="Helpful, efficient support with a positive experience."
                ),
                discord.RadioGroupOption(
                    label="Excellent",
                    description="Outstanding, fast, and highly effective support experience."
                ),
            ]
        )
    )

    rating_feedback = discord.ui.Label(
        text="Support Experience",
        description="Share your ticket support experience and overall satisfaction.",
        component=discord.ui.TextInput(
            style=discord.TextStyle.long,
            max_length=512,
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        ...

class TicketComponentEmbed(discord.ui.LayoutView):
    def __init__(self, opener: discord.Member | int, ticket_channel_id: int, submission_json: dict, core_json: dict, db: DatabaseAccess):
        super().__init__(timeout=None)

        self.opener: Optional[discord.Member] = opener if isinstance(opener, discord.Member) else None
        self.db = db
        if isinstance(opener, discord.Member):
            self.opener_id = opener.id
        elif isinstance(opener, int):
            self.opener_id = opener
        else:
            raise ValueError("Invalid Opener Type")
        

        self.ticket_channel_id: int = ticket_channel_id
        self.misc: Dict = {}

        self.submission_json = submission_json
        self.core_json = core_json

        base_name = self.submission_json.get("ticket_name_base", "ticket")
        self.ticket_name: str = base_name.replace("_", " ").title()
        roles = submission_json.get("ping_roles", [])
        self.ticket_mentions: str = " ".join(f"<@&{role_id}>" for role_id in roles) if roles else "No Mentions!"


        self.allowed_roles = set(submission_json.get("ping_roles", []))
        self.higher_staff_role_ids = set(self.core_json.get("BasicConfigurations").get("higher_staffs_role_id"))


        self.claim_ticket: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.green,
            label="Claim Ticket",
            custom_id=f"claim-ticket{self.ticket_channel_id}",
        )

        self.revoke_claim: discord.ui.Button = discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Revoke Claim",
                custom_id=f"revoke-claim{self.ticket_channel_id}",
            )

        
        self.actions: discord.ui.Select = discord.ui.Select(
                custom_id=f"actions{self.ticket_channel_id}",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label="Case List",
                        value="case_list",
                        description="View the cases of the user",
                        emoji=emoji["logs"]
                    ),
                    discord.SelectOption(
                        label="Ban",
                        value="ban",
                        description="Ban the reported user",
                        emoji=emoji["ban_hammer"]
                    ),
                    discord.SelectOption(
                        label="Mute",
                        value="mute",
                        description="Mute the reported user",
                        emoji=emoji["member"]
                    ),
                    discord.SelectOption(
                        label="Warn",
                        value="warn",
                        description="Warn the reported user",
                        emoji=emoji["warn"]
                    )
                ]
            )

        self.opener_actions: discord.ui.Select = discord.ui.Select(
                custom_id=f"opener-actions{self.ticket_channel_id}",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label="Case List",
                        value="case_list",
                        description="View the cases of the user",
                        emoji=emoji["logs"]
                    ),
                    discord.SelectOption(
                        label="Dummy",
                        value="dummy",
                        description="This is a dummy and it does nothing",
                        emoji=emoji["logs"]
                    )
                ]
            )

        self.claim_ticket.callback = self.claim_ticket_callback
        self.revoke_claim.callback = self.revoke_claim_callback
        self.actions.callback = self.actions_callback
        self.opener_actions.callback = self.opener_actions_callback

        opener_details = submission_json.get("opener", {})

        avatar_url = (
            self.opener.display_avatar.url
            if isinstance(self.opener, discord.Member)
            else opener_details.get("avatar")
        )


        content = (
            f"- **ID**: {opener_details.get("member_id", 0)}\n"
            f"- **Created on**: {opener_details.get("created_on")}\n"
            f"- **Joined on**: {opener_details.get("joined_on")}"
            if opener_details is not None
            else "**User information unavailable**"
        ) 

        mention = (
            self.opener.mention
            if isinstance(self.opener, discord.Member)
            else f"<@{opener_details.get("member_id")}>"
        )


        base_container = discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {self.ticket_name}"),
            discord.ui.TextDisplay(content=f"{self.ticket_mentions}"),
                
            discord.ui.Section(
                discord.ui.TextDisplay(content=f"**Ticket Opener Information | {mention}**"),
                discord.ui.TextDisplay(content=content),
                accessory=discord.ui.Thumbnail(
                    media=avatar_url,
                ),
            ),
            discord.ui.ActionRow(
                self.opener_actions
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
        )

        ticket_details = []
        field_data = self.submission_json["field_data"]

        for data in field_data:
            field = data.get("field")
            value = data.get("value")

            field_type = field.get("type")
            label = field.get("label", "label")

            if field_type in ("short", "long"):
                
                ticket_details.append(
                    discord.ui.TextDisplay(
                        f"**{label}**\n```{value}```"
                    )
                )

            elif field_type == "member":
                if value["flag"] == 0:
                    self.misc["reported_member"] = {
                        "id": value["member_id"],
                        "avatar": value["avatar"],
                        "username": value["username"]
                    }

                    ticket_details.append(
                        discord.ui.Section(
                            discord.ui.TextDisplay(content=f"**{label}** | <@{value["member_id"]}>"),
                            discord.ui.TextDisplay(content=f"- **ID**: **{value["member_id"]}**\n- **Created on**: {value["created_on"]}\n- **Joined on**: {value["joined_on"]}"),
                            accessory=discord.ui.Thumbnail(
                                media=value["avatar"],
                            ),
                        )
                    )
                    ticket_details.append(
                        discord.ui.ActionRow(
                            self.actions
                        )
                    )
                else:
                    ticket_details.append(
                    discord.ui.TextDisplay(
                        f"**{label}**\n```{value["username"]}```"
                    )
                )

                ticket_details.append(
                    discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
                )

            elif field_type in ("file_upload",):

                self.misc["proofs"] = value
                
                gallery = discord.ui.MediaGallery()
                gallery.items = [discord.MediaGalleryItem(media=url) for url in value]
                ticket_details.append(
                    discord.ui.TextDisplay(
                        f"**{label}**"
                    )
                )
                ticket_details.append(
                    gallery
                )

                ticket_details.append(
                    discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
                )


        ticket_details_container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## Ticket Details"
            ),
            *ticket_details
        )

        actions_container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## Ticket Actions"
            ),
            discord.ui.ActionRow(
                self.claim_ticket,
                self.revoke_claim
            )
        )

        self.add_item(base_container)
        self.add_item(ticket_details_container)
        self.add_item(actions_container)

    async def claim_ticket_callback(self, interaction: discord.Interaction) -> None:
        if interaction.channel is None or interaction.guild is None:
            return

        await interaction.response.defer()

        is_staff = any(role.id in self.allowed_roles for role in interaction.user.roles)
        is_opener = interaction.user.id == self.opener_id

        if not is_staff or is_opener:
            await interaction.followup.send(
                embed=simple_embed("You are not allowed to claim this ticket!", 'cross'),
                ephemeral=True
            )
            return

        success = await self.db.bot_db.set_ticket_claimer(interaction.user.id, interaction.channel.id, interaction.guild.id)
        if not success:
            claimer = await self.db.bot_db.get_ticket_claimer(interaction.channel.id)
            await interaction.followup.send(
                embed=simple_embed(f"<@{claimer}> has already claimed this ticket!", 'cross'),
                ephemeral=True
            )
            return

        channel = interaction.channel
        if isinstance(channel, discord.TextChannel) and isinstance(interaction.user, discord.Member):
            await channel.set_permissions(
                interaction.user,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
                use_external_emojis=True,
                read_message_history=True
            )

        self.claim_ticket.disabled = True
        self.claim_ticket.label = "Claimed"
        self.claim_ticket.style = discord.ButtonStyle.secondary
        self.ticket_message = interaction.message
        await interaction.message.edit(view=self)
        await interaction.followup.send(embed=simple_embed(f"{interaction.user.mention} has claimed the ticket!"))

    async def revoke_claim_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if interaction.channel is None or interaction.guild is None:
            return
        
        claimer = await self.db.bot_db.get_ticket_claimer(interaction.channel.id)


        if claimer is None:
            await interaction.followup.send(
                embed=simple_embed("No one has claimed this ticket!", 'cross'),
                ephemeral=True
            )
            return
        

        claimer_member: Optional[discord.Member] = None

        if claimer is not None:
            try:
                claimer_member = await interaction.guild.fetch_member(claimer)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                claimer_member = None


        if (interaction.user.id != claimer and not any(role.id in self.higher_staff_role_ids for role in interaction.user.roles)):            
            await interaction.followup.send(
                embed=simple_embed("You are not allowed to revoke ticket claims!", 'cross'),
                ephemeral=True
            )
            return

        if claimer is None:
            await interaction.followup.send(
                embed=simple_embed("This ticket is not currently claimed.", 'cross'),
                ephemeral=True
            )
            return

        channel = interaction.channel
        if claimer_member is not None and isinstance(channel, discord.TextChannel):
            await channel.set_permissions(claimer_member, overwrite=None)  


        self.claim_ticket.disabled = False
        self.claim_ticket.label = "Claim"
        self.claim_ticket.style = discord.ButtonStyle.green

        await self.db.bot_db.reset_ticket_claimer(interaction.channel.id)

        if interaction.message:
            await interaction.message.edit(view=self)

        await interaction.followup.send(
            embed=simple_embed("Ticket claim has been revoked!"),
            ephemeral=True
        )

        await channel.send(
            embed=simple_embed(f"{interaction.user.mention} revoked the ticket claim.")
        )

    async def case_list_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.guild is None:
            return
        
        """ Get member id """
        
        """ Fetch modlogs of the reported member """
        reported_member_data = self.misc["reported_member"]
        await self.case_list_handler(interaction, reported_member_data)

    async def case_list_callback_opener(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.guild is None:
            return
        
        """ If member instance is an integer we need to fetch him """
        if self.opener is None:
            member = interaction.guild.get_member(self.opener_id)

            if member is None:
                try:
                    member = await interaction.guild.fetch_member(self.opener_id)
                except discord.NotFound:
                    await interaction.followup.send(embed=simple_embed("Cannot fetch member.  He might have left the server", 'cross'))
                    return
        elif isinstance(self.opener, discord.Member):
            member = self.opener
        else:
            raise ValueError("Invalid member type")
        
        member_data = {
            "id": member.id,
            "avatar": member.display_avatar.url,
            "username": member.global_name
        }

        await self.case_list_handler(interaction, member_data)
            
    async def case_list_handler(self, interaction: discord.Interaction, member_data: dict) -> None:

        assert isinstance(interaction.guild, discord.Guild)

        _guild_id = self.db.bot_db.get_secondary_guild_id(interaction.guild.id) or interaction.guild.id
        
        """ Fetch modlogs of the given member """
        payload = {
            "guild_id": _guild_id,
            "target_user_id": member_data["id"],
            "moderator_id": None,
            "mod_type": "all",
            "page_start": 0,
            "page_end": 5
        }

        result = await self.db.bot_db.fetch_mod_logs(**payload)
        if not result["success"]:
            await interaction.followup.send(embed=simple_embed("No cases found.", 'cross'), ephemeral=True)
            return  

        embed =  build_mod_logs_embed_absolute(
            username=member_data["username"],
            avatar=member_data["avatar"],
            display_logs=result["logs"],
            mod_type_counts=result["counts"],
            total_count=result["total_logs"],
            page_start=0
        )
        
        logging_channel_id = self.db.bot_db.get_channel(_guild_id, "logs_channel")
        if logging_channel_id is not None and result["proofs_exists"]:
            view = ProofsView(result["logs"], logging_channel_id, _guild_id)
            await interaction.followup.send(embeds=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embeds=embed, ephemeral=True)

    async def actions_callback(self, interaction: discord.Interaction):
        """ Only allow staff members"""
        is_staff = any(role.id in self.allowed_roles for role in interaction.user.roles)
        is_opener = interaction.user.id == self.opener_id

        if not is_staff or is_opener:
            await interaction.response.send_message(
                embed=simple_embed("You are not allowed to use this!", 'cross'),
                ephemeral=True
            )
            return
        
        if interaction.guild is None:
            return

        assert isinstance(self.actions, discord.ui.Select)
        value = self.actions.values[0]
        
        if value == "case_list":
            await self.case_list_callback(interaction)

        elif value == "ban":
            await interaction.response.send_modal(
                BanModal(
                    db=self.db,
                    member_id=self.misc["reported_member"]["id"],
                    proofs=self.misc["proofs"]
                )
            )

        elif value == "warn":
            await interaction.response.send_modal(
                WarnModal(
                    db=self.db, 
                    member_id=self.misc["reported_member"]["id"],
                    proofs=self.misc["proofs"]
                )
            )

        elif value == "mute":
            await interaction.response.send_modal(
                MuteModal(
                    db=self.db, 
                    member_id=self.misc["reported_member"]["id"],
                    proofs=self.misc["proofs"]
                )
            )

    async def opener_actions_callback(self, interaction: discord.Interaction):
        is_staff = any(role.id in self.allowed_roles for role in interaction.user.roles)
        is_opener = interaction.user.id == self.opener_id

        if not is_staff or is_opener:
            await interaction.response.send_message(
                embed=simple_embed("You are not allowed to use this!", 'cross'),
                ephemeral=True
            )
            return
        
        if interaction.guild is None:
            return

        assert isinstance(self.actions, discord.ui.Select)
        value = self.opener_actions.values[0]
        
        if value == "case_list":
            await self.case_list_callback_opener(interaction)
        elif value == "dummy":
            await interaction.response.send_message("Oh!, The reason this dummy is here is due to how selectors in discord work.\n- You can only select the item inside a selector once, if that's only one Item.\n- Unless you reopen discord.", ephemeral=True)

class TicketModal(discord.ui.Modal):
    def __init__(self, title: str, modal_data: dict, json_data, db: DatabaseAccess, message: discord.Message):
        super().__init__(title=title)

        if not isinstance(modal_data, dict):
            raise TypeError(f"modal_data must be a dict, got {type(modal_data)}")

        self.db: DatabaseAccess = db
        self.components: List[Dict] = []
        self.modal_data = modal_data
        self.json_data = json_data
        self.converter = MemberConverter()
        self.message = message

        self.fields = self.modal_data.get("fields")

        if not isinstance(self.fields, list):
            raise TypeError(f"fields must be a list, got {type(self.fields)}")

        for field in self.fields:
            if not isinstance(field, dict):
                raise TypeError(f"Each field must be a dict, got {type(field)}")

            label = field.get("label", "")
            description = field.get("description", "")
            length = field.get("length", 100)
            field_type = field.get("type", "short")

            component = None

            """ Assign Components based on field type """
            if field_type in ("member", "long", "short"):
                style = (
                    discord.TextStyle.paragraph
                    if field_type == "long"
                    else discord.TextStyle.short
                )

                component=discord.ui.TextInput(
                    style=style,
                    max_length=length,
                    required=True
                )
            elif field_type == "file_upload":
                component = discord.ui.FileUpload(
                    max_values=10,
                    custom_id="report_images",
                    required=True
                )

            """ This wouldn't likely to occur """
            if component is None:
                raise ValueError

            item = discord.ui.Label(
                text=label,
                description=description if description else None,
                component=component
            )

            self.components.append({
                "field": field,
                "item": item
            })
            self.add_item(item)
        

    async def ticket_thread_constructor(self, interaction: discord.Interaction, core_json, submission_json) -> discord.TextChannel | discord.Thread | None:
        if interaction.guild is None:
            return None

        channel_id: int = int(submission_json.get("channel_id"))
        
        proof_attachments = submission_json.get("proof_images")
        proofs_flag = False
        if proof_attachments:
            proof_url = '\n'.join(proof_attachments)
            proofs_flag = True
        else:
            proof_url = "No Proofs Attached!"
            proofs_flag = False

        roles = submission_json.get("ping_roles", [])

        higher_staff_roles_ids = core_json.get("BasicConfigurations").get("higher_staffs_role_id")

        opener = interaction.user
        logging_channel_id = core_json.get("BasicConfigurations").get("TicketLoggingHandler")
        ticket_name_base = submission_json.get("ticket_name_base")
        channel_emoji = submission_json.get("channel_emoji", "")
        ticket_name = f"{channel_emoji}{ticket_name_base}"
    
        channel_category = interaction.guild.get_channel(channel_id)

        if not isinstance(channel_category, discord.CategoryChannel):
            channel_category = await interaction.guild.fetch_channel(channel_id)

        if not isinstance(channel_category, discord.CategoryChannel):
            await interaction.followup.send(
                embed=simple_embed("Misconfigured ticket category. Please contact an admin."),
                ephemeral=True
            )
            return None


        overwrites = {}

        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(
            view_channel=False
        )
        overwrites[opener] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            use_external_emojis=True,
            read_message_history=True
        )

        for role_id in roles:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    embed_links=True,
                    attach_files=True,
                    add_reactions=True,
                    use_external_emojis=True,
                    read_message_history=True,
                    create_public_threads=False,
                    create_private_threads=False
                )
        for role_id in higher_staff_roles_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    add_reactions=True,
                    use_external_emojis=True,
                    read_message_history=True,
                    create_public_threads=False,
                    create_private_threads=False
                )
        if isinstance(channel_category, discord.CategoryChannel):
            text_channel: discord.TextChannel = await interaction.guild.create_text_channel(
                name=f"{ticket_name}-{opener.name}",
                category=channel_category,
                overwrites=overwrites
            )
        else:
            text_channel: discord.TextChannel = await interaction.guild.create_text_channel(
                name=f"{ticket_name}-{opener.name}",
                overwrites=overwrites
            )

        if not isinstance(opener, discord.Member):
            return

        view = TicketComponentEmbed(opener=opener, ticket_channel_id=text_channel.id, submission_json=submission_json, core_json=core_json, db=self.db)
        ticket_message: discord.Message = await text_channel.send(view=view)

        """ Pin the message to the channel so that it's easily viewable """
        try:
            await ticket_message.pin()
        except discord.Forbidden:
            pass

        if proofs_flag:
            await text_channel.send(content=f"{proof_url}")

        await self.db.bot_db.create_ticket(
            text_channel.id,
            interaction.guild.id,
            opener.id,
            ticket_name_base,
            logging_channel_id,
            submission_json,
            ticket_message.id
        )
        return text_channel

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        rows = await self.db.bot_db.get_ticket_by_opener(interaction.user.id, interaction.guild.id)

        if len(rows) >= 3:
            references = ", ".join(f"<#{r[0]}>" for r in rows)
            await interaction.followup.send(
                embed=simple_embed(
                    "Your ticket cannot be created.\n"
                    "Please close your previous tickets first.\n"
                    f"**References:** {references}"
                ),
                ephemeral=True
            )
            return

        channel_id = self.modal_data.get("channel_id")
        ticket_name_base = self.modal_data.get("ticket_base_name", "ticket")
        channel_emoji = self.modal_data.get("channel_emoji", "")
        ping_roles = self.modal_data.get("ping_roles", [])
        logs_channel_id  = self.json_data["BasicConfigurations"]["TicketLoggingHandler"]

        """ Extracting field details and values and then storing it on fields """
        field_data: List[Dict] = []

        for data in self.components:
            field = data["field"]
            item = data["item"]

            field_type = field["type"]

            if field_type == "file_upload":
                field_data.append({
                    "field": field,
                    "value": [attachment.url for attachment in item.component.values]
                })
            elif field_type == "member":
                # Try fetching the member details.
                bot: commands.Bot = cast(commands.Bot, interaction.client)
                ctx = await bot.get_context(self.message)

                try:
                    user = re.sub(r"[^\w.]", "", str(item.component.value).lstrip("@"))

                    member: discord.Member = await self.converter.convert(
                        ctx,
                        user
                    )

                    field_data.append({
                        "field": field,
                        "value": {
                            "flag": 0,
                            "username": member.global_name,
                            "member_id": member.id,
                            "avatar": member.display_avatar.url,
                            "created_on": f"<t:{int(member.created_at.timestamp())}:R>",
                            "joined_on": f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "<t:0:R>",
                        }
                    })
                except:
                    field_data.append({
                        "field": field,
                        "value": {
                            "flag": 1,
                            "username": item.component.value
                        }
                    })

                ...
            else:
                field_data.append({
                    "field": field,
                    "value": item.component.value
                })

        opener_details = {
            "username": interaction.user.global_name,
            "member_id": interaction.user.id,
            "avatar": interaction.user.display_avatar.url,
            "created_on": f"<t:{int(interaction.user.created_at.timestamp())}:R>",
            "joined_on": f"<t:{int(interaction.user.joined_at.timestamp())}:R>" if interaction.user.joined_at else "<t:0:R>",
        }

        submission = {
            "opener": opener_details,
            "channel_id": channel_id,
            "fields": self.fields,
            "field_data": field_data,
            "ticket_name_base": ticket_name_base,
            "channel_emoji": channel_emoji,
            "logs_channel_id" : logs_channel_id,
            "ping_roles" : ping_roles
        }
        thread_channel: discord.TextChannel | discord.Thread | None = await self.ticket_thread_constructor(
            interaction,
            self.json_data,
            submission
        )

        if thread_channel is not None:
            await interaction.followup.send(
                embed=simple_embed(
                    f"Your ticket has been created: {thread_channel.mention}"
                ),
                ephemeral=True
            )

class TicketSelector(discord.ui.View):
    def __init__(self, json_data: dict, db: DatabaseAccess):
        super().__init__(timeout=None)

        self.json_data = json_data
        self.db = db
        self.tickets = json_data.get("Tickets", [])

        options = [
            discord.SelectOption(
                label=ticket["label"],
                emoji=ticket.get("emoji", None),
                description=ticket.get("description", None),
                value=str(index)
            )
            for index, ticket in enumerate(self.tickets)
        ]

        self.add_item(
            TicketSelect(
                options=options,
                tickets=self.tickets,
                json_data=self.json_data,
                db=self.db
            )
        )

class TicketSelect(discord.ui.Select):
    def __init__(
        self,
        options: list[discord.SelectOption],
        tickets: list[dict],
        json_data: dict,
        db: DatabaseAccess
    ):
        super().__init__(
            placeholder="Choose a ticket type...",
            options=options,
            custom_id="ticket_selector_main"
        )

        self.tickets = tickets
        self.json_data = json_data
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        selected_index = int(self.values[0])
        selected_ticket = self.tickets[selected_index]

        modal = TicketModal(
            title=selected_ticket["label"],
            modal_data=selected_ticket,
            json_data=self.json_data,
            db=self.db,
            message=interaction.message
        )

        await interaction.response.send_modal(modal)

async def TicketLogAction(interaction: discord.Interaction,thread: discord.Thread,opened_user_id: int,ticket_type: str,accessed_staff_ids: set, logs_channel: discord.TextChannel):
    embed = discord.Embed(
        title="Ticket Logs",
        description=f"### __TICKET DETAILS__\n> - Ticket Opener : <@{opened_user_id}>\n> - Ticket Thread Reference :  {thread.mention}",
        color=0xFFFFFF
    )

    embed.add_field(
        name="Ticket Thread ID",
        value=f"- ```{thread.id}```",
        inline=False
    )

    embed.add_field(
        name="Staff Closed Ticket",
        value=f"> - <@{interaction.user.id}>",
        inline=False
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=695fa4b2&is=695e5332&hm=4fc10e3e38fa5a3270fab5cd8fff0928472594db43955848c443dcddef447f5e&")

    embed.set_footer(text=ticket_type)
    try:
        await logs_channel.send(content=f'<@{opened_user_id}>', embed=embed)
    except Exception as e:
        print(f"Exception [TicketLogAction] {e}")

def TicketEmbed(ticket_opener: discord.Member, submission_data) -> discord.Embed:
    ticket_name = submission_data.get("ticket_name_base", "General Ticket").replace("_", " ").title()
    ticket_values = submission_data.get("inputs", {})
    embed = discord.Embed(
        color=16777215,
        title=f"<:arrow:1438045578721493062> {ticket_name} Ticket",
        description=f"<:member:1438045591098753104> Ticket Opened By {ticket_opener.mention}",
    )
    embed.set_author(
        name=ticket_opener.name,
        icon_url=ticket_opener.display_avatar.url,
    )
    embed.set_thumbnail(url=ticket_opener.display_avatar.url)
    embed.set_image(url=img['border'])
    embed.set_footer(
        text="Lily Ticketing",
    )

    for k, v in ticket_values.items():
        embed.add_field(
            name=k,
            value=f" >  - ```{v}```",
            inline=False,
        )
    return embed