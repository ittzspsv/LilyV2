from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.logging.lily_logging import LilyLoggingController

from dataclasses import dataclass



@dataclass
class DatabaseAccess:
    bot_db: BotGlobalsDatabaseAccess
    logging_controller: LilyLoggingController