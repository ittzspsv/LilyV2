import discord
import Config.sValueConfig as VC
import io
import LilyAlgorthims.sFruitSuggestorAlgorthim as FSA
import Values.sStockValueJSON as StockValueJSON

def format_currency(val):
    value = int(val)
    if value >= 1_000_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000_000:.1f}DX"
    elif value >= 1_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000:.1f}NX"
    elif value >= 1_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000:.1f}OX"
    elif value >= 1_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000:.1f}SPX"
    elif value >= 1_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000:.1f}SX"
    elif value >= 1_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000:.1f}QI"
    elif value >= 1_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000:.1f}QT"
    elif value >= 1_000_000_000_000: 
        return f"{value / 1_000_000_000_000:.1f}T"
    elif value >= 1_000_000_000:  
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:  
        return f"{value / 1_000:.1f}k"
    else:
        return str(int(value))


class GAGPetValueComponent(discord.ui.LayoutView):
    def __init__(self, value, weight, age, name,link, mutations, pet_classifications):
        super().__init__()
        self.value = value
        self.weight = weight
        self.age = age
        self.name = name
        self.link = link
        self.mutations = mutations
        self.pet_classifications = pet_classifications

        self.container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=f"## {self.name}"),
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        media=self.link,
                    ),
                ),
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=f"### Basic Value Information\n- **Value : {self.value}**\n- **Weight : {self.weight}**\n- **Age : {self.age}**"),
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=f"### Additional Information\n- Mutations : {self.mutations}\n- Pet Classification : {self.pet_classifications}"),
                accent_colour=discord.Colour(16711813)
            )
        
        self.add_item(self.container1)

class GAGFruitValueComponent(discord.ui.LayoutView):
    def __init__(self, value, weight, variant, name,mutations,link):
        super().__init__()
        self.value = value
        self.weight = weight
        self.variant = variant
        self.name = name
        self.mutations = mutations
        self.link = link

        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {name}"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=self.link
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"- **Value : {self.value}**\n- **Weight : {self.weight}**\n- **Variant : {self.variant}**\n- **Mutations : {self.mutations}**"),
            accent_colour=discord.Colour(16711813),
        )

        self.add_item(self.container1)

class StaffDataComponent(discord.ui.LayoutView):    
    def __init__(self, name: str = "", role: str = "", responsibilities: str = "",timezone: str = "",
                 join_date: str = "", experience: str = "", strike_count: int = 0, profile_link:str = "", on_leave:int = 0):
        super().__init__()
        self.name = name
        self.role = role
        self.responsibilities = responsibilities
        self.timezone = timezone
        self.join_date = join_date
        self.experience = experience
        self.strike_count = strike_count
        self.profile_link = profile_link
        self.on_leave = on_leave

        
        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"# {self.name.upper()}"),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=self.profile_link,
                ),
            ),
            discord.ui.TextDisplay(content=f"- 🛡️ Role : **{self.role}**\n- 🔖Responsibilities : **{self.responsibilities}**\n- ⏲️Time Zone : **{self.timezone}**\n- 📅 Join Date : **{self.join_date}**\n- 📆 Evaluated Experience In Server : **{self.experience}**\n- 📜Strike Count : **{self.strike_count}**\n- 🏠 On Leave **{"Yes" if self.on_leave == 1 else "No"}**"),
            accent_colour=discord.Colour(16711813),
        )

        self.add_item(self.container1)

class EmptyView(discord.ui.LayoutView):
    def __init__(self):
        self.text_display1 = discord.ui.TextDisplay(content="hi")

class GAGStockComponent(discord.ui.LayoutView):
    def __init__(self, stock_name,seed_stock, pings):
        super().__init__()
        self.stock_name = stock_name
        self.seed_stock = seed_stock
        self.pings = pings

        sections = [
            discord.ui.TextDisplay(content=f"## {stock_name}"),
        ]

        sections.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media="attachment://border.png")
            )
        )

        for item in seed_stock:
            sections.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=(
                            f"### {item['display_name']}\n"
                            f"- Quantity : **x{item['quantity']}**\n"
                            f"- Rarity : Common"
                        )
                    ),
                    accessory=discord.ui.Thumbnail(media=item['icon']),
                )
            )

        sections.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media="attachment://border.png")
            )
        )

        if pings:
            pings_text = "## PINGS\n" + ", ".join(pings)
            sections.append(discord.ui.TextDisplay(content=pings_text))

        container1 = discord.ui.Container(
            *sections,
            accent_colour=discord.Colour(8447),  # blue accent
        )

        self.add_item(container1)

class PVBStockComponent(discord.ui.LayoutView):
    def __init__(self, stock_name,seed_stock):
        super().__init__()
        self.stock_name = stock_name
        self.seed_stock = seed_stock

        sections = [
            discord.ui.TextDisplay(content=f"## {stock_name}"),
        ]

        sections.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media="attachment://border.png")
            )
        )

        for item in seed_stock:
            sections.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=(
                            f"### {item['display_name']}\n"
                            f"- Quantity : **x{item['quantity']}**\n"
                            f"- Rarity : {item['rarity']}"
                        )
                    ),
                    accessory=discord.ui.Thumbnail(media=item['icon']),
                )
            )

        sections.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media="attachment://border.png")
            )
        )

        container1 = discord.ui.Container(
            *sections,
            accent_colour=discord.Colour(8447),  # blue accent
        )

        self.add_item(container1)

class BloxFruitStockComponent(discord.ui.LayoutView):
    def __init__(self, stock_type, container_items):
        super().__init__()
        container1 = discord.ui.Container(*container_items, accent_colour=discord.Colour(8447))
        self.add_item(container1)

    @classmethod
    async def create(cls, stock_data):
        stock_type, data = stock_data
        container_items = [discord.ui.TextDisplay(content=f"## {stock_type.upper()}")]

        container_items.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media="attachment://border.png")
            )
        )

        for item_name, price in data.items():
            cursor = await VC.vdb.execute(
                "SELECT category, icon_url FROM BF_ItemValues WHERE name = ?", (item_name,)
            )
            row = await cursor.fetchone()
            if row:
                rarity, image_url = row
            else:
                rarity, image_url = "Undefined", "https://static.wikia.nocookie.net/roblox-blox-piece/images/5/52/BloxFruitsHeader.png"

            section = discord.ui.Section(
                discord.ui.TextDisplay(
                    content=f"### {item_name}\n- Price: **${price}**\n- Rarity: {rarity.title()}"
                ),
                accessory=discord.ui.Thumbnail(media=image_url)
            )
            container_items.append(section)

        container_items.append(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(media="attachment://border.png")
            )
        )

        return cls(stock_type, container_items)

class TradeSuggestorComponent(discord.ui.LayoutView):
    def __init__(self, bot, your_fruits, your_types, message, neglect_fruits, type):
        super().__init__()

        self.bot = bot
        self.your_fruits = your_fruits
        self.your_types = your_types
        self.message = message
        self.type = type

        self.permanent_emoji = discord.utils.get(bot.emojis, name="perm") or "✅"
        self.gamepass_emoji = discord.utils.get(bot.emojis, name="gamepass") or "🎟️"
        self.default_emoji = discord.utils.get(bot.emojis, name="default") or "🍉"
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
            accent_colour=discord.Colour(786687),
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

        except Exception as e:
            try:
                await interaction.delete_original_response()
                await interaction.followup.send(
                    f"Failed to generate trade: {e}", ephemeral=True
                )
            except:
                print("Cannot send followup; interaction expired:", e)

class ModeratioNStatsComponent(discord.ui.LayoutView):
    def __init__(self):
        super().__init__()