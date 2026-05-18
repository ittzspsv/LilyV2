from dataclasses import dataclass
from typing import Any
import discord

@dataclass
class OverloadData:
    message: discord.Message
    bot: Any