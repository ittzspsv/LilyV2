from fastapi import FastAPI

from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from .routes.management import management_routes

class LilyAPI:
    def __init__(self, db: BotGlobalsDatabaseAccess) -> None:
        self.app = FastAPI(title="Lily API")
        self.db = db

        self.app.include_router(management_routes(self.db))

        @self.app.get("/")
        async def root():
            return {"api": "Lily-API", "status": "online"}
