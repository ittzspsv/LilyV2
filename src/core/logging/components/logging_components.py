import discord
from core.utils.embeds.sLilyEmbed import simple_embed

class ProofComponentModal(discord.ui.Modal):
    case_id = discord.ui.Label(
        text='Case ID',
        description='Please enter a case ID.',
        component=discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder='Enter a valid case ID',
            max_length=120,
        ),
    )

    images = discord.ui.Label(
        text='Proofs',
        description='Upload any relevant proofs for this case',
        component=discord.ui.FileUpload(
            max_values=10,
            custom_id='report_images',
            required=True,
        ),
    )

    footer = discord.ui.TextDisplay(
        'Please ensure that every proof you have attached here is valid!'
    )

    def __init__(self, controller) -> None:
        super().__init__(title="Case Proofs")
        self.controller = controller

    async def on_submit(self, interaction: discord.Interaction) -> None:

        await interaction.response.defer()
        
        assert isinstance(self.images.component, discord.ui.FileUpload)
        assert isinstance(self.case_id.component, discord.ui.TextInput)

        files = self.images.component.values
        success = await self.controller.send_proofs(interaction, files, int(self.case_id.component.value))

        if success:
            await interaction.followup.send(embed=simple_embed(f"Successfully appended proofs for •{self.case_id.component.value}"))
        else:
            await interaction.followup.send(embed=simple_embed(f"Failed to append proofs for •{self.case_id.component.value}. Please verify that the case ID is valid", 'cross'))