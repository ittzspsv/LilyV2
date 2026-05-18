from lily_agent import tool
from pydantic import BaseModel, Field
from typing import Optional

from ..data.overload_data import OverloadData
from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess

import discord