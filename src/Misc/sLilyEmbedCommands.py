import aiohttp

import discord
import os
import json
import LilyLogging.sLilyLogging as LilyLogging

from discord import SelectOption, Interaction, ui

from discord.ext import commands
import Config.sBotDetails as Config
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Misc.sLilyEmbed as sLilyEmbed

class LilyEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @PermissionEvaluator(RoleAllowed=Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles + Config.StaffRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name="embed_create", description="Creates an embed based on JSON config and sends it to a specific channel")
    async def create_embed(self, ctx: commands.Context, channel_to_send: discord.TextChannel, * ,embed_json_config: str = "{}"):
        try:
            if embed_json_config.startswith("http://") or embed_json_config.startswith("https://"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(embed_json_config) as resp:
                            if resp.status != 200:
                                await ctx.send("Failed to fetch data from the provided link.")
                                return
                            embed_json_config = await resp.text()
                except Exception as fetch_error:
                    await ctx.send(f"Fetch Failure {str(fetch_error)}")
                    return

            
            try:
                json_data = json.loads(embed_json_config)
            except json.JSONDecodeError:
                await ctx.send("Invalid JSON Format")
                return
            
            try:
                content, embeds = sLilyEmbed.ParseAdvancedEmbed(json_data)
                await channel_to_send.send(content=content, embeds=embeds)
                await ctx.send("Embed sent successfully.")
                await LilyLogging.WriteLog(ctx, ctx.author.id, f"Has Sent an Embed to <#{channel_to_send.id}>")
            except Exception as embed_error:
                await ctx.send(f"Parser Failure: {str(embed_error)}")

        except Exception as e:
            await ctx.send(f"Unhandled Exception: {str(e)}")

    @PermissionEvaluator(RoleAllowed=Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name="create_formatted_embed", description="Creates a formatted embed with custom buttons using a set of instructions")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def create_formatted_embed(self, ctx:commands.Context, channel_to_send: discord.TextChannel, link: str = "", simulate_as:discord.Member=None):
            await ctx.defer()

            ButtonSessionMemory = f"storage/{ctx.guild.id}/sessions/ButtonSessionMemory.json"
            try:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(link) as response:
                            if response.status != 200:
                                await ctx.send(f"HTTP Exception: {response.status}")
                                return
                            config = await response.text()
                    except aiohttp.ClientError as e:
                        await ctx.send(f"Error Fetching Config: {str(e)}")
                        return

                try:
                    if simulate_as == None:
                        embeds, buttons = sLilyEmbed.EmbedParser(config, ctx.author)
                    else:
                        embeds, buttons = sLilyEmbed.EmbedParser(config, simulate_as)
                except Exception as e:
                    await ctx.send(f"Parser Error: {str(e)}")
                    return

                view = discord.ui.View(timeout=None)
                persistent_buttons = []

                for idx, (button, embed) in enumerate(buttons):
                    button.custom_id = f"guide_button_{ctx.message.id}_{idx}"

                    async def callback(interaction, embed=embed):
                        try:
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                        except Exception as e:
                            try:
                                await interaction.response.send_message(f"Displaying Embed Failure: {str(e)}", ephemeral=True)
                            except:
                                pass

                    button.callback = callback
                    view.add_item(button)

                    persistent_buttons.append({
                        "label": button.label,
                        "style": button.style.value,
                        "custom_id": button.custom_id,
                        "embed": embed.to_dict()
                    })

                try:
                    if embeds:
                        message = await channel_to_send.send(embeds=embeds, view=view)
                        await ctx.send("Embeds sent successfully.")
                    elif buttons:
                        message = await channel_to_send.send(content="Use the buttons to explore the guide:", view=view)
                        await ctx.send("Embeds sent successfully.")
                    else:
                        await ctx.send("No embeds or buttons were found in the config. Please check your format.", ephemeral=True)
                        return
                except Exception as e:
                    await ctx.send(f"Failed to send message to the specified channel: {str(e)}", ephemeral=True)
                    return

                persistent_data = {
                    "message_id": message.id,
                    "channel_id": channel_to_send.id,
                    "buttons": persistent_buttons
                }

                try:
                    if os.path.exists(ButtonSessionMemory):
                        with open(ButtonSessionMemory, "r") as f:
                            content = f.read().strip()
                            all_views = json.loads(content) if content else []
                    else:
                        all_views = []
                except (json.JSONDecodeError, OSError):
                    all_views = []

                all_views.append(persistent_data)

                try:
                    with open(ButtonSessionMemory, "w") as f:
                        json.dump(all_views, f, indent=4)
                except Exception as e:
                    try:
                        await ctx.send(f"Failed to save Button Session. You may have to post this embed again if program got restarted: {str(e)}", ephemeral=True)
                    except:
                        pass

            except Exception as e:
                try:
                    await ctx.send(f"Unhandled Exception: {str(e)}", ephemeral=True)
                except:
                    pass

    @PermissionEvaluator(RoleAllowed=Config.DeveloperRoles + Config.OwnerRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name="update_formatted_embed", description="Update an existing formatted embed with a new config rule data")
    async def update_formatted_embed(self, ctx:commands.Context, link: str, simulate_as:discord.Member=None):
        await ctx.defer()

        ButtonSessionMemory = f"storage/{ctx.guild.id}/sessions/ButtonSessionMemory.json"

        if not os.path.exists(ButtonSessionMemory):
            await ctx.send("No previous sessions found.", ephemeral=True)
            return

        try:
            with open(ButtonSessionMemory, "r") as f:
                all_views = json.load(f)
        except json.JSONDecodeError:
            await ctx.send("Session memory file is corrupted.")
            return

        if not all_views:
            await ctx.send("No saved embed sessions to update.")
            return
        bot = self.bot
        class SessionSelect(ui.Select):
            def __init__(self, sessions):
                self.bot = bot
                options = [
                    SelectOption(
                        label=f"Message ID: {s['message_id']}",
                        description=f"Channel ID: {s['channel_id']}",
                        value=str(i)
                    ) for i, s in enumerate(sessions)
                ]
                super().__init__(placeholder="Choose Embed Session to Update", options=options)

            async def callback(self, interaction: Interaction):
                index = int(self.values[0])
                session = all_views[index]

                try:
                    channel = self.bot.get_channel(session["channel_id"]) or await self.bot.fetch_channel(session["channel_id"])
                    message = await channel.fetch_message(session["message_id"])
                except discord.NotFound:
                    await interaction.response.send_message("Message not found. It may have been deleted.", ephemeral=True)
                    return

                await interaction.response.defer(ephemeral=True)

                async with aiohttp.ClientSession() as session_obj:
                    async with session_obj.get(link) as response:
                        if response.status != 200:
                            await interaction.followup.send(f"Failed to load new config (status {response.status})", ephemeral=True)
                            return
                        new_config = await response.text()

                try:
                    if simulate_as == None:
                        new_embeds, new_buttons = sLilyEmbed.EmbedParser(new_config, ctx.author)
                    else:
                        new_embeds, new_buttons = sLilyEmbed.EmbedParser(new_config, simulate_as)
                except Exception as e:
                    await interaction.followup.send(f"Failed to parse new config: {str(e)}", ephemeral=True)
                    return

                new_view = ui.View(timeout=None)
                updated_buttons = []

                for idx, (button, embed) in enumerate(new_buttons):
                    button.custom_id = f"guide_button_{message.id}_{idx}"

                    async def callback(interaction: Interaction, embed=embed):
                        await interaction.response.send_message(embed=embed, ephemeral=True)

                    button.callback = callback
                    new_view.add_item(button)

                    updated_buttons.append({
                        "label": button.label,
                        "style": button.style.value,
                        "custom_id": button.custom_id,
                        "embed": embed.to_dict()
                    })

                try:
                    if new_embeds:
                        await message.edit(embeds=new_embeds, view=new_view)
                    elif new_buttons:
                        await message.edit(content="Use the buttons to explore the updated guide:", embeds=[], view=new_view)
                    else:
                        await interaction.followup.send("Invalid content in the new config.", ephemeral=True)
                        return
                except Exception as e:
                    await interaction.followup.send(f"Failed to update message: {str(e)}", ephemeral=True)
                    return
                all_views[index]["buttons"] = updated_buttons
                with open(ButtonSessionMemory, "w") as f:
                    json.dump(all_views, f, indent=4)

                await interaction.followup.send("Embed updated successfully.", ephemeral=True)

        class SessionSelector(ui.View):
            def __init__(self, sessions):
                super().__init__(timeout=60)
                self.add_item(SessionSelect(sessions))

        await ctx.send("Select the session you'd like to update:", view=SessionSelector(all_views), ephemeral=True)


async def setup(bot):
    await bot.add_cog(LilyEmbed(bot))