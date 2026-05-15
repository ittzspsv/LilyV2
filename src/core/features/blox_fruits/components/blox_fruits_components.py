import discord
import core.configs.sBotDetails as config
from ..embeds.blox_fruits_embed import build_win_loss_embed
from ..utils.trade_calculator import win_or_lose
from ..utils.trade_suggestor import trade_suggestor
from ....database.integrations.blox_fruits import BloxFruitsDatabase

class TradeSuggestorComponent(discord.ui.LayoutView):
    def __init__(self, db: BloxFruitsDatabase ,your_fruits, your_types, message, neglect_fruits, type):
        super().__init__()

        self.db = db
        self.your_fruits = your_fruits
        self.your_types = your_types
        self.message = message
        self.type = type

        self.permanent_emoji = config.emoji.get('perm')
        self.gamepass_emoji = config.fruit_emojis.get('dark_blade')
        self.fruit_skins_emoji = config.fruit_emojis.get('galaxy_kitsune')
        self.default_emoji = config.emoji.get("default") or "🍉"
        self.overpay_emoji = "🔥"
        self.fair_emoji = "🤝"

        self.include_permanent = False
        self.include_gamepass = False
        self.include_skins = False
        self.overpay = False
        self.neglect_fruits = neglect_fruits
        self.storage_capacity = 1

        self.basic_select = discord.ui.Select(
            custom_id="basic_select",
            options=[
                discord.SelectOption(label="Default", value="default", emoji=self.default_emoji),
                discord.SelectOption(label="Suggest Permanent", value="permanent", emoji=self.permanent_emoji),
                discord.SelectOption(label="Suggest Gamepass", value="gamepass", emoji=self.gamepass_emoji),
                discord.SelectOption(label="Suggest Fruit Skins", value="fruit_skins", emoji=self.fruit_skins_emoji),
            ]
        )
        self.basic_select.callback = self.basic_select_callback

        self.pricing_select = discord.ui.Select(
            custom_id="pricing",
            options=[
                discord.SelectOption(label="Fair", value="fair", emoji=self.fair_emoji),
                discord.SelectOption(label="Overpay", value="overpay", emoji=self.overpay_emoji),
            ]
        )
        self.pricing_select.callback = self.pricing_select_callback

        self.storage_select = discord.ui.Select(
            custom_id="storage_select",
            options=[discord.SelectOption(label=str(i), value=str(i), emoji=config.fruit_emojis['fruit_storage']) for i in range(1, 5)]
        )
        self.storage_select.callback = self.storage_select_callback

        self.suggest_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Suggest Trade",
            custom_id="suggest_trade"
        )
        self.suggest_button.callback = self.suggest_button_callback

        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## Trade Suggestor Configuration\n\n### • Customize your Suggester Settings, Then Click Suggest"),
            discord.ui.TextDisplay(content="**Basic Suggestions**"),
            discord.ui.ActionRow(self.basic_select),
            discord.ui.TextDisplay(content="**Trade Pricing Suggestions**"),
            discord.ui.ActionRow(self.pricing_select),
            discord.ui.TextDisplay(content=f"**Your Total Fruit Storage**"),
            discord.ui.ActionRow(self.storage_select),
            discord.ui.ActionRow(self.suggest_button),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(container)

    def check_user(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.message.author.id

    async def reject_user(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Only the original user can use this configuration.",
            ephemeral=True
        )

    async def basic_select_callback(self, interaction: discord.Interaction):
        if not self.check_user(interaction):
            return await self.reject_user(interaction)

        selected = self.basic_select.values[0]
        self.include_permanent = selected == "permanent"
        self.include_gamepass = selected == "gamepass"
        self.include_skins = selected == "fruit_skins"

        await interaction.response.send_message(
            f"You selected: {selected}", ephemeral=True
        )

    async def storage_select_callback(self, interaction: discord.Interaction):
        if not self.check_user(interaction):
            return await self.reject_user(interaction)

        selected = self.storage_select.values[0]
        self.storage_capacity = int(selected)

        await interaction.response.send_message(
            f"Your Max Fruit Storage Capacity is {selected}", ephemeral=True
        )

    async def pricing_select_callback(self, interaction: discord.Interaction):
        if not self.check_user(interaction):
            return await self.reject_user(interaction)

        selected = self.pricing_select.values[0]
        self.overpay = selected == "overpay"

        await interaction.response.send_message(
            f"Pricing selected: {selected}", ephemeral=True
        )

    async def suggest_button_callback(self, interaction: discord.Interaction):
        if not self.check_user(interaction):
            return await self.reject_user(interaction)

        try:
            await interaction.response.defer()

            their_fruits, their_types, success = await trade_suggestor(
                self.db,
                self.your_fruits, self.your_types,
                self.include_permanent,
                self.include_gamepass,
                self.include_skins,
                self.overpay,
                self.neglect_fruits,
                self.storage_capacity
            )

            if not success:
                raise ValueError("Trade suggestion failed.")

            if self.type == 1:
                '''
                image = await StockValueJSON.j_LorW(
                    self.your_fruits, self.your_types,
                    their_fruits, their_types,
                    1, 1
                )

                if image is None:
                    raise ValueError("Image generation failed.")

                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                buffer.seek(0)

                try:
                    await interaction.delete_original_response()
                except:
                    pass

                await self.message.reply(
                    file=discord.File(fp=buffer, filename="trade_result.webp"),
                )
                '''
            else:
                data = win_or_lose(
                    self.db,
                    self.your_fruits, self.your_types,
                    their_fruits, their_types
                )

                embed = build_win_loss_embed(
                    result=data,
                    your_fruits=self.your_fruits,
                    your_fruit_types=self.your_types,
                    their_fruits=their_fruits,
                    their_fruit_types=their_types
                )
                
                try:
                    await interaction.delete_original_response()
                except:
                    pass
                await self.message.reply(embed=embed)

        except Exception as e:
            try:
                await interaction.delete_original_response()
                await interaction.followup.send(
                    f"Failed to generate trade: {e}", ephemeral=True
                )
            except:
                print("Cannot send followup; interaction expired:", e)