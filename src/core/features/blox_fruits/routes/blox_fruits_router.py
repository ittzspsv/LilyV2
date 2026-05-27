from ....database.integrations.blox_fruits import BloxFruitsDatabase
from ...blox_fruits.utils.trade_matcher import match_fruit_set
from ..embeds.blox_fruits_embed import build_fruit_value_embed, build_win_loss_embed
from ..utils.trade_extractor import extract_trade_details
from ..utils.trade_calculator import win_or_lose
from typing import Optional, Any
from ..components.blox_fruits_components import TradeSuggestorComponent, InviteView
import re
import discord
import io

class BloxFruitsController:
    def __init__(self, db: BloxFruitsDatabase):
        super().__init__()

        self.db = db
        self.img_mode: int = 0

    async def on_message(self, message: discord.Message, bot: Optional[Any]=None):
        if bot and message.guild is not None:
            if message.channel.id in bot.db.get_channels(message.guild.id, "bf_fruit_values"):
                await self.fruit_value(message=message)

            elif message.channel.id in bot.db.get_channels(message.guild.id, "bf_win_loss"):
                await self.win_loss(message=message)


    async def fruit_value(self, message: discord.Message):
        item_name = re.sub(r"^(perm|permanent|fruit value of|value of|value)\s+", "", message.content.lower()).strip()

        alias_map = self.db.alias_map
        item_name = match_fruit_set(item_name, set(self.db.fruit_names_sorted), alias_map)

        if item_name:
            item_data = self.db.fetch_fruit_details(item_name)
            if isinstance(item_data, dict):
                overload_data = {
                    "fruit_name": item_data.get("name") or "Unknown",
                    "physical_value": item_data.get("physical_value") or "0",
                    "permanent_value": item_data.get("permanent_value") or "0",
                    "value": item_data.get("physical_value") or "0",
                    "demand": item_data.get("physical_demand") or "0",
                    "demand_type": item_data.get("demand_type") or "..",
                    "icon_url": (
                        item_data.get("icon_url")
                        or getattr(message.author.display_avatar, "url", None)
                    ),
                }

                if self.img_mode == 1:
                    pass

                else:
                    embed = build_fruit_value_embed(item_data)

                    if len(embed.fields) > 0:
                        await message.reply(content=None, embed=embed, view=InviteView())

    async def win_loss(self, message: discord.Message):
        your_fruits, your_fruit_types, their_fruits, their_fruit_types = extract_trade_details(message.content, self.db)
        if not any([
            your_fruits,
            your_fruit_types,
            their_fruits,
            their_fruit_types
        ]):
            return

        """ Check for fruit_suggestor fallback """
        if bool(your_fruits) != bool(their_fruits):
            fruits = your_fruits if your_fruits else their_fruits
            fruit_types = your_fruit_types if your_fruits else their_fruit_types            
            await self.trade_suggestor(message, fruits, fruit_types)

        else: 
            """ Normal w or l evaluation here"""
            calculated_result = win_or_lose(
                self.db,
                your_fruits[:4],
                your_fruit_types[:4],
                their_fruits[:4],
                their_fruit_types[:4]
            )

            if self.img_mode == 1:
                """ Generate win-loss image """
            else:
                """ Send embed """
                embed = build_win_loss_embed(
                    calculated_result,
                    your_fruits[:4],
                    your_fruit_types[:4],
                    their_fruits[:4],
                    their_fruit_types[:4]
                )

                await message.reply(embed=embed, view=InviteView())

    async def trade_suggestor(self, message: discord.Message ,fruits, fruit_types):
        view = TradeSuggestorComponent(
            self.db,
            fruits,
            fruit_types,
            message,
            [],
            self.img_mode
        )

        await message.reply(view=view)