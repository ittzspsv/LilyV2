import discord

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
    def __init__(self, name: str = "", role: str = "", responsibilities: str = "",
                 join_date: str = "", experience: str = "", strike_count: int = 0, profile_link:str = ""):
        super().__init__()
        self.name = name
        self.role = role
        self.responsibilities = responsibilities
        self.join_date = join_date
        self.experience = experience
        self.strike_count = strike_count
        self.profile_link = profile_link

        
        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"# {self.name.upper()}"),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=self.profile_link,
                ),
            ),
            discord.ui.TextDisplay(content=f"- 🛡️ Role : **{self.role}**\n- 🔖Responsibilities : **{self.responsibilities}**\n- 📅 Join Date : **{self.join_date}**\n- 📆 Evaluated Experience In Server : **{self.experience}**\n- 📜Strike Count : **{self.strike_count}**"),
            accent_colour=discord.Colour(16711813),
        )

        self.add_item(self.container1)

class EmptyView(discord.ui.LayoutView):
    def __init__(self):
        self.text_display1 = discord.ui.TextDisplay(content="hi")
    