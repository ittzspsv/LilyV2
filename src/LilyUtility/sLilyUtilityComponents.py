import discord

class ProfileInformationComponent(discord.ui.LayoutView):
    def __init__(self, user: discord.User):
        super().__init__()

        avatar = user.avatar.url if user.avatar else user.default_avatar.url
        created_timestamp = int(user.created_at.timestamp())

        items = [
            discord.ui.Section(
                discord.ui.TextDisplay(content="## User Profile Information"),
                discord.ui.TextDisplay(content=f"**User ID**\n- ```{user.id}```"),
                discord.ui.TextDisplay(content=f"**Global Username**\n- ```{user.name}```"),
                accessory=discord.ui.Thumbnail(
                    media=avatar,
                ),
            )
        ]

        if user.banner:
            items.append(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        media=user.banner.url,
                    ),
                )
            )

        items.append(
            discord.ui.TextDisplay(
                content=f"**Member Since**\n- <t:{created_timestamp}:R>"
            )
        )

        self.container = discord.ui.Container(*items)

        self.add_item(self.container)