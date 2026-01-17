import discord
import aiosqlite
import Config.sBotDetails as Configs
import LilyModeration.sLilyModeration as mLily

from datetime import datetime

from discord.ext import commands


vodb = None


async def ValidateVouch(interaction: discord.Interaction,vouch_by: discord.Member,vouch_to: discord.Member,desc: str,proofs):
    try:
        now = int(datetime.now().timestamp())
        await vodb.execute("INSERT OR IGNORE INTO service_provider (provider_id, trusted, potential_scammer)VALUES (?, 0, 0)",(vouch_to.id,))
        await vodb.execute("INSERT INTO vouch (guild_id, vouched_by, vouch_to, vouch_description, vouched_at, proofs) VALUES (?, ?, ?, ?, ?, ?)",(interaction.guild.id, vouch_by.id, vouch_to.id, desc, now, str(proofs)))
        await vodb.commit()

        await interaction.followup.send(
            embed=mLily.SimpleEmbed(
                f"Successfully vouched {vouch_to.mention}"
            ),ephemeral=True
        )

    except Exception as e:
        await vodb.rollback()
        print(f"Exception [VALIDATE VOUCH] {e}")

        await interaction.followup.send(embed=mLily.SimpleEmbed("Failed to vouch member.","cross"),ephemeral=True)

class ProofsModal(discord.ui.Modal):
    def __init__(self, vouch_by: discord.Member, vouch_to: discord.Member, desc: str="None"):
        super().__init__(title="Proofs")
        self.vouch_by = vouch_by
        self.vouch_to = vouch_to
        self.desc = desc

        self.images = discord.ui.Label(
            text='Images',
            description='Upload any relevant images to prove he helped.',
            component=discord.ui.FileUpload(
                max_values=10,
                custom_id='proof_images',
                required=True,
            ),
        )

        self.add_item(self.images)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.defer()
        proofs_url = [attachment.url for attachment in self.images.component.values]
        await ValidateVouch(interaction, self.vouch_by, self.vouch_to, self.desc, proofs_url)


async def Initialize():
    global vodb
    vodb = await aiosqlite.connect("storage/vouches/Vouch.db")

async def AddVouch(ctx: commands.Context, vouch_by: discord.Member, vouch_to: discord.Member, desc: str="None"):
    if not ctx.interaction:
        await ctx.send(embed=mLily.SimpleEmbed(f"Please use this command as slash command", 'cross'))
    else:
        try:
            await ctx.interaction.response.send_modal(ProofsModal(vouch_by, vouch_to, desc))
        except Exception as e:
            print(e)

async def RemoveVouch(ctx: commands.Context, vouch_id: int):
    await ctx.defer()
    try:
        await vodb.execute("DELETE FROM vouch WHERE id = ?", (vouch_id,))
        await vodb.commit()
        await ctx.send(embed=mLily.SimpleEmbed(f"Successfully Removed"))
    except Exception as e:
        print(f"Exception [REMOVE VOUCH] {e}")
        await ctx.send(embed=mLily.SimpleEmbed(f"Failed to Delete Vouch", 'cross'))

async def AssignTrustedServiceProvider(ctx: commands.Context, member: discord.Member):
    try:
        await vodb.execute("UPDATE service_provider SET trusted = 1 WHERE provider_id = ?", (member.id,))
        await vodb.commit()
        await ctx.send(embed=mLily.SimpleEmbed(f"Successfully Made the Service provider {member.mention} Trusted"))
    except Exception as e:
        print(f"Exception [AssignTrustedServiceProvider] {e}")
        await ctx.send(embed=mLily.SimpleEmbed(f"Command Failure", 'cross'))

async def RemoveTrustedServiceProvider(ctx: commands.Context, member: discord.Member):
    try:
        await vodb.execute("UPDATE service_provider SET trusted = 0 WHERE provider_id = ?", (member.id,))
        await vodb.commit()
        await ctx.send(embed=mLily.SimpleEmbed(f"Removed the trusted key from the service provider {member.mention}"))
    except Exception as e:
        print(f"Exception [RemoveTrustedServiceProvider] {e}")
        await ctx.send(embed=mLily.SimpleEmbed(f"Command Failure", 'cross'))

async def ShowVouches(ctx: commands.Context, member: discord.Member):
    try:
        cursor = await vodb.execute(
            """
            SELECT 
                sp.trusted,
                sp.potential_scammer,
                COUNT(v.id) AS total_vouches
            FROM service_provider sp
            LEFT JOIN vouch v ON v.vouch_to = sp.provider_id
            WHERE sp.provider_id = ?
            GROUP BY sp.provider_id
            """,
            (member.id,)
        )
        row = await cursor.fetchone()

        if not row:
            await ctx.send(
                embed=mLily.SimpleEmbed(
                    f"{member.mention} is not registered as a service provider.",
                    "cross"
                )
            )
            return

        trusted, potential_scammer, total_vouches = row

        cursor_a = await vodb.execute(
            """
            SELECT
                v.vouched_by,
                v.vouch_description,
                v.vouched_at,
                v.proofs
            FROM vouch v
            WHERE v.vouch_to = ?
            ORDER BY v.vouched_at DESC
            LIMIT 5
            """,
            (member.id,)
        )
        rows_a = await cursor_a.fetchall()

        cursor_b = await vodb.execute(
            """
            SELECT COUNT(id)
            FROM vouch
            WHERE vouch_to = ? AND scam_vouch = 1
            """,
            (member.id,)
        )
        rows_b = await cursor_b.fetchone()
        scam_count = rows_b[0] or 0

        title = f"{Configs.emoji['arrow']} {member.name}'s Vouches "
        if trusted == 1:
            title += Configs.emoji['checked']
        if potential_scammer == 1:
            title += "⭕"

        profile_embed = discord.Embed(
            title=title,
            description="- Showing Profile Information for the Service Provider",
            color=0xFFFFFF
        )

        profile_embed.add_field(
            name=f"{Configs.emoji['bookmark']} Total Vouches",
            value=f"- {total_vouches}",
            inline=True
        )

        profile_embed.add_field(
            name=f"{Configs.emoji['warn']} Scam Vouches",
            value=f"- {scam_count}",
            inline=True
        )

        profile_embed.add_field(
            name=f"{Configs.emoji['calender']} Experience",
            value="- Null Years",
            inline=True
        )

        profile_embed.set_thumbnail(url=member.display_avatar.url)
        profile_embed.set_image(url=Configs.img['border'])

        recent_embed = discord.Embed(
            title=f"{Configs.emoji['arrow']} Recent Vouches",
            description="- Showing the most recent vouches a member has received across all servers.",
            color=0xFFFFFF
        )

        recent_embed.set_thumbnail(url=Configs.img['bookmark'])
        recent_embed.set_image(url=Configs.img['border'])

        if not rows_a:
            recent_embed.add_field(
                name="No Vouches",
                value="This service provider has not received any vouches yet.",
                inline=False
            )
        else:
            for idx, (vouched_by, description, time, proofs) in enumerate(rows_a, start=1):
                proof_text = (
                    f"[Click here to view proof]({proofs})"
                    if proofs else "No proof provided"
                )

                recent_embed.add_field(
                    name=f"{Configs.emoji['ticket']} Vouch #{idx}",
                    value=(
                        f"> {Configs.emoji['member']} **Vouched By:** <@{vouched_by}>\n"
                        f"> {Configs.emoji['pencil']} **Vouch:** {description}\n"
                        f"> {Configs.emoji['clock']} **Time:** <t:{time}:R>\n"
                        f"> {Configs.emoji['ban_hammer']} {proof_text}"
                    ),
                    inline=False
                )

        await ctx.send(embeds=[profile_embed, recent_embed])

    except Exception as e:
        print(f"Exception [ShowVouches] {e}")
        await ctx.send(
            embed=mLily.SimpleEmbed("Command Failure", "cross")
        )