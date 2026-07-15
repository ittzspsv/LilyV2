from ..database.integrations.bot_globals import BotGlobalsDatabaseAccess
from .embeds.logging_embeds import write_log_embed, moderation_embed
from ..features.moderation.components.sLilyModerationComponents import action_log

from discord.ext import commands
from datetime import datetime
from typing import Optional, Union, Sequence, List
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.utils.lily_utility import utcnow
from .components.logging_components import ProofComponentModal, AppealButton

import discord
import io
import re
import aiohttp

class LilyLoggingController:
    def __init__(self, bot_db: BotGlobalsDatabaseAccess) -> None:
        self.bot_db = bot_db

    async def write_log(self, ctx: commands.Context, user_id: int, log_txt: str) -> None:
        if ctx.guild is None:
            return

        await self.bot_db.write_log(ctx.guild.id, user_id, log_txt)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        
        logs_channel: int | None = self.bot_db.get_channel(ctx.guild.id, "logs_channel")
        if logs_channel:
            channel = ctx.bot.get_channel(logs_channel)
            if not channel:
                try:
                    channel = await ctx.guild.fetch_channel(logs_channel)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    return

            embed = write_log_embed(timestamp, user_id, log_txt)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)

    async def log_moderation_action(
        self,
        ctx: commands.Context | discord.Interaction,
        moderator: discord.Member | discord.User,
        target_user: discord.Member | discord.User,
        mod_type: str,
        reason: str = "No reason provided",
        proofs: Optional[Sequence[Union[discord.Attachment, str]]] = None
    ) -> int | None:
        if ctx.guild is None:
            content = "Guild object is required for this command to be executed"
            if isinstance(ctx, commands.Context):
                await ctx.reply(content)
            elif isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    await ctx.followup.send(content)
                else:
                    await ctx.response.send_message(content)

            return
        
        acronyms: dict[str, str] = await self.bot_db.get_moderation_acronyms(moderator.id, ctx.guild.id)
        reason = re.sub(
                    r"\b\w+\b",
                    lambda m: acronyms.get(m.group(0).lower(), m.group(0)),
                    reason
                )

        case_id = await self.bot_db.log_moderation_action(
            ctx.guild.id,
            moderator.id,
            target_user.id,
            mod_type,
            reason
        )

        """ Send Action DM to the User"""
        a_log = action_log(
            mod_type,
            reason,
            ctx.guild.name,
        )

        try:
            view = discord.ui.View(timeout=None)
            view.add_item(AppealButton(case_id))
            await target_user.send(embed=a_log, view=view)
        except Exception:
            pass
                
        embeds_to_send = moderation_embed(
            moderator.id,
            target_user.id,
            mod_type,
            reason,
            utcnow()
        )

        logs_channel_id = self.bot_db.get_channel(ctx.guild.id, "logs_channel")
        if not logs_channel_id:
            return case_id

        channel = ctx.guild.get_channel(logs_channel_id)

        if channel is None:
            try:
                channel = await ctx.guild.fetch_channel(logs_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return case_id

        if isinstance(channel, discord.TextChannel):
            await channel.send(
                content=f"{target_user.mention}",
                embeds=embeds_to_send
            )

            """ Also try sending proofs If the staff member has attached proofs"""
            if proofs and case_id:
                async with aiohttp.ClientSession() as session:
                    files: List[discord.File] = []
                    for proof in proofs:
                        if isinstance(proof, discord.Attachment):
                            data = await proof.read()
                            file = discord.File(
                                fp=io.BytesIO(data),
                                filename=proof.filename
                            )
                            files.append(file)
                        elif isinstance(proof, str):
                            async with session.get(proof) as resp:
                                if resp.status != 200:
                                    raise ValueError(f"Failed to fetch image: {proof}")

                                data = await resp.read()

                                filename = proof.split("?")[0].split("/")[-1]
                                if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                                    filename += ".png"

                                file = discord.File(
                                    fp=io.BytesIO(data),
                                    filename=filename
                                )

                                files.append(file)
                        else:
                            continue
                """ Send the proofs to the logging channel """
                message = await channel.send(
                    content=f"Proofs {target_user.mention}",
                    files=files
                )

                """ Store the message id on the database for future retrieval """
                if isinstance(ctx, commands.Context):
                    await self.bot_db.log_proof_action(ctx.guild.id, case_id, message.id, ctx.author.id)
                elif isinstance(ctx, discord.Interaction):
                    await self.bot_db.log_proof_action(ctx.guild.id, case_id, message.id, ctx.user.id)

        return case_id

    async def post_log(
        self,
        ctx: commands.Context, 
        embed: discord.Embed, 
        log_type:str="Default Log Type"
    ) -> None:
        if ctx.guild is None:
            content = "Guild object is required for this command to be executed"
            if isinstance(ctx, commands.Context):
                await ctx.reply(content)
            elif isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    await ctx.followup.send(content)
                else:
                    await ctx.response.send_message(content)

            return
        logs_channel = self.bot_db.get_channel(ctx.guild.id, "logs_channel")

        if not logs_channel:
            return

        channel = ctx.guild.get_channel(logs_channel)

        if channel is None:
            try:
                channel = await ctx.guild.fetch_channel(logs_channel)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        if isinstance(channel, discord.TextChannel):
            await channel.send(
                content=str(log_type),
                embeds=[embed]
            )

    async def send_proofs(
        self,
        interaction: discord.Interaction,
        proofs: List[discord.Attachment],
        case_id: int
    ) -> bool:
        if interaction.guild is None:
            return False
        
        case_exists = await self.bot_db.case_exists(case_id, interaction.guild.id)
        if not case_exists:
            return False

        logs_channel_id = self.bot_db.get_channel(interaction.guild.id, "logs_channel")
        if not logs_channel_id:
            return False
        
        channel = interaction.guild.get_channel(logs_channel_id)

        if channel is None:
            try:
                channel = await interaction.guild.fetch_channel(logs_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return False
        
        if proofs and case_id and isinstance(channel, discord.TextChannel):
            files: List[discord.File] = []
            for proof in proofs:
                if isinstance(proof, discord.Attachment):
                    data = await proof.read()
                    file = discord.File(
                            fp=io.BytesIO(data),
                            filename=proof.filename
                        )
                    files.append(file)
                else:
                    continue
            """ Send the proofs to the logging channel """
            message = await channel.send(
                content=f"Proofs #case-{case_id}\n-by {interaction.user.id}",
                files=files
            )

            """ Store the message id on the database for future retrieval """
            await self.bot_db.log_proof_action(interaction.guild.id, case_id, message.id, interaction.user.id)

            return True
        else:
            return False
        
    async def retrieve_proofs(
        self,
        ctx: commands.Context,
        case_id: int
    ) -> None:
        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "This command can only be executed inside a server.",
                    "cross"
                )
            )
            return
        
        await ctx.defer()

        """ Check the validity of the case """
        validity = await self.bot_db.case_exists(case_id, ctx.guild.id)
        if not validity:
            await ctx.reply(
                embed=simple_embed(
                    "Case doesn't exists!",
                    "cross"
                )
            )
            return

        message_ids = await self.bot_db.retrieve_proofs(case_id)

        if not message_ids:
            await ctx.reply(
                embed=simple_embed(
                    "No proofs found for the given case ID.",
                    "cross"
                )
            )
            return

        logs_channel_id = self.bot_db.get_channel(ctx.guild.id, "logs_channel")

        if not logs_channel_id:
            await ctx.reply(
                embed=simple_embed(
                    "Proofs cannot be retrieved: logging channel is not configured.",
                    "cross"
                )
            )
            return

        channel = ctx.guild.get_channel(logs_channel_id)

        if channel is None:
            try:
                channel = await ctx.guild.fetch_channel(logs_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await ctx.reply(
                    embed=simple_embed(
                        "Proofs cannot be retrieved: logging channel is missing or inaccessible.",
                        "cross"
                    )
                )
                return
            
        if not isinstance(channel, discord.TextChannel):
            return

        files: list[discord.File] = []

        for message_id in message_ids:
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                await ctx.reply(
                    embed=simple_embed(
                        "Missing permission to read messages in the logging channel.",
                        "cross"
                    )
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
            await ctx.reply(
                embed=simple_embed(
                    "No valid proof attachments were found for this case.",
                    "cross"
                )
            )
            return

        await ctx.reply(
            content=f"Proofs for case `{case_id}`",
            files=files
        )

    async def log_proofs(self, ctx: commands.Context):
        try:
            if ctx.guild is None:
                return

            if ctx.interaction is None:
                await ctx.reply(embed=simple_embed("Please run this command as a slash command.", 'cross'))  
                return

            interaction = ctx.interaction
            modal = ProofComponentModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(e)