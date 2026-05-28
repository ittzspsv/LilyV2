from fastapi import APIRouter
from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess

def management_routes(db: BotGlobalsDatabaseAccess):
    router = APIRouter(prefix="/management", tags=["Management"])

    @router.get("/staffs")
    async def staffs(guild_id: int):
        response = await db.fetch_all_staffs(guild_id)
        return response
    
    @router.get("/staff")
    async def staff(guild_id: int, staff_id: int):
        response = await db.fetch_staff_detail(staff_id, guild_id)
        return response

    return router