import discord
import LilyBloxFruits.core.sBloxFruitsCalculations as StockValueJSON
import LilyModeration.sLilyModeration as mLily
import Config.sValueConfig as VC
import Config.sBotDetails as Config
from discord.ui import View, Button, Modal, TextInput



import io
import Config.sBotDetails as Configs
import LilyBloxFruits.core.sFruitSuggestorAlgorthim as FSA

from LilyUtility.sLilyUtility import format_currency

class TradeSuggestorComponent(discord.ui.LayoutView):
    def __init__(self, bot, your_fruits, your_types, message, neglect_fruits, type):
        super().__init__()

        self.bot = bot
        self.your_fruits = your_fruits
        self.your_types = your_types
        self.message = message
        self.type = type

        self.permanent_emoji = discord.utils.get(self.bot.emojis, name="perm") or "✅"
        self.gamepass_emoji = discord.utils.get(self.bot.emojis, name="gamepass") or "🎟️"
        self.default_emoji = discord.utils.get(self.bot.emojis, name="default") or "🍉"
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
                discord.SelectOption(label="Suggest Fruit Skins", value="fruit_skins"),
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
            options=[discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 5)]
        )
        self.storage_select.callback = self.storage_select_callback

        self.suggest_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Suggest Trade",
            custom_id="suggest_trade"
        )
        self.suggest_button.callback = self.suggest_button_callback

        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## TRADE SUGGESTOR CONFIGURATION\n\n### • Customize your Suggester Settings, Then Click Suggest"),
            discord.ui.TextDisplay(content="**BASIC SUGGESTIONS**"),
            discord.ui.ActionRow(self.basic_select),
            discord.ui.TextDisplay(content="**TRADE PRICING SUGGESTIONS**"),
            discord.ui.ActionRow(self.pricing_select),
            discord.ui.TextDisplay(content="**TOTAL FRUIT CAPACITY**"),
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

            their_fruits, their_types, success = await FSA.trade_suggestor(
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
            else:
                            data = await StockValueJSON.j_LorW(
                                self.your_fruits, self.your_types,
                                their_fruits, their_types,
                                0
                            )

                            your_fruit_details = ""
                            their_fruit_details = ""

                            for i in range(len(self.your_fruits)):

                                fruit_name = self.your_fruits[i].replace(" ", "_").replace("-", "_").lower()
                                fruit_emoji = Configs.fruit_emojis.get(fruit_name, "🍎")
                                beli_emoji = Configs.emoji.get("beli", "💸")
                                perm_emoji = Configs.emoji.get("perm", "🔒")

                                value = data['Your_IndividualValues'][i]
                                formatted_value = f"{value:,}"
                                if self.your_types[i].lower() == "permanent":
                                    your_fruit_details += f"- {perm_emoji}{fruit_emoji} {beli_emoji} {formatted_value}\n"
                                else:
                                    your_fruit_details += f"- {fruit_emoji} {beli_emoji} {formatted_value}\n"
                                

                            for i in range(len(their_fruits)):
                                fruit_name = their_fruits[i].replace(" ", "_").replace("-", "_").lower()
                                fruit_emoji = Configs.fruit_emojis.get(fruit_name, "🍎")
                                beli_emoji = Configs.emoji.get("beli", "💸")
                                perm_emoji = Configs.emoji.get("perm", "🔒")

                                value = data['Their_IndividualValues'][i]
                                formatted_value = f"{value:,}"
                                if their_types[i].lower() == "permanent":
                                    their_fruit_details += f"- {perm_emoji}{fruit_emoji} {beli_emoji} {formatted_value}\n"
                                else:
                                    their_fruit_details += f"- {fruit_emoji} {beli_emoji} {formatted_value}\n"

                            embed = discord.Embed(title="My Trade Suggestion!",
                                description=f"## {data['TradeConclusion']}",
                                colour=16777215)

                            embed.add_field(name="Your Fruit Values",
                                            value=your_fruit_details,
                                            inline=True)
                            embed.add_field(name="Their Fruit Values",
                                            value=their_fruit_details,
                                            inline=True)
                            embed.add_field(name="Your Total Values:",
                                            value=format_currency(data['Your_TotalValue']),
                                            inline=False)
                            embed.add_field(name="Their Total Values:",
                                            value=format_currency(data['Their_TotalValue']),
                                            inline=False)
                            embed.add_field(name=data['Percentage'],
                                            value="",
                                            inline=False)   
                            embed.set_image(url=Config.img.get("border"))
                         
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

class RateComboModal(Modal):
    def __init__(self, combo_id: int):
        super().__init__(title="Rate This Combo")
        self.combo_id = combo_id

        self.rating_input = TextInput(
            label="Your rating (1-10)",
            placeholder="Enter a number between 1 and 10",
            style=discord.TextStyle.short,
            required=True,
            max_length=2
        )
        self.add_item(self.rating_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_rating = int(self.rating_input.value)
            if not (1 <= new_rating <= 10):
                await interaction.response.send_message(
                    "Please enter a number between 1 and 10!",
                    ephemeral=True
                )
                return

            cursor = await VC.combo_db.execute(
                "SELECT rating FROM Combos WHERE combo_id = ?",
                (self.combo_id,)
            )
            row = await cursor.fetchone()
            old_avg = row[0] or 0
            if old_avg == 0:
                average = new_rating
            else:
                average = (old_avg + new_rating) / 2

            await VC.combo_db.execute(
                "UPDATE Combos SET rating = ? WHERE combo_id = ?",
                (average, self.combo_id)
            )
            await VC.combo_db.commit()

            await interaction.response.send_message(
                f"Thanks! You rated the combo: {new_rating}/10",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred while rating the combo!",
                ephemeral=True
            )

class RatingComponent(discord.ui.View):
    def __init__(self, member: discord.Member, combo_id: int):
        super().__init__(timeout=300)
        self.member = member
        self.combo_id = combo_id

    @discord.ui.button(label="Rate Combo", style=discord.ButtonStyle.secondary, custom_id="rate_combo_btn")
    async def rate_combo_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RateComboModal(self.combo_id)
        await interaction.response.send_modal(modal)