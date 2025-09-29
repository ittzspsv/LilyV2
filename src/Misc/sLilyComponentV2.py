import discord
import Config.sValueConfig as VC

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
    