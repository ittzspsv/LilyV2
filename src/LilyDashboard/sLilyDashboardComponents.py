import discord

from typing import Dict, Tuple, Callable, Any

class MainDashboard(discord.ui.LayoutView):
    def __init__(self, *, timeout = 3600):
        super().__init__(timeout=timeout)

        self.component_selectors: Dict[str, Tuple[str, str, Callable]] = {
            "Bot Customization" : ("", "Customize bot's profile, banner and description"),
            "Lily Blox Fruits Module" : ("", "All Blox Fruit related Modules"),
            "Lily Moderation" : ("", "Moderation Module"),
            "Lily Management" : ("", "Manage staff roles and permission hierrachy for lily"),
            "Lily Leveling" : ("", "Setup Leveling system for lily"),
            "Lily Ticket Tool" : ("", "Setup Thread based ticketing system")
        }

        self.module_selection = discord.ui.Select(
            custom_id = "module_selection",
            options=[
                discord.SelectOption(label=key, value=key.replace(" ", "_").lower(), emoji=values[1])
                for key, values in self.component_selectors.items()
            ]
        )

        self.module_selection.callback = self.module_selection_callback


        self.container = discord.ui.Container(
            discord.ui.Section(
            discord.ui.TextDisplay(content="## Lily Dashboard\n"),
            discord.ui.TextDisplay(content="- This dashboard contains everything needed to customize the Lily Bot. Quickly access the core essential settings required for the bot to function properly on your server."),
            accessory=discord.ui.Thumbnail(
                media="https://media.discordapp.net/attachments/1438505067341680690/1471162540338843834/Lily.png?ex=69987a62&is=699728e2&hm=d1af2b70cbc58c1f6f08df701cac35b08dcf8a93f7119e8182937ac1b252e341&=&format=webp&quality=lossless&width=1496&height=1496",
            ),
        ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="## Components\n- Please Select a component from a selector to customize."),
            discord.ui.ActionRow(self.module_selection),
            accent_colour=discord.Colour(16777215),
        )

        self.add_item(self.container)

    async def module_selection_callback(self, interaction: discord.Interaction):
        pass