from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess

templates = Jinja2Templates(directory="src/api/frontend")

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
    
    @router.get("/leaderboard")
    async def leaderboard(request: Request):
        response = await db.leaderboard(970643838047760384, 3)
        return templates.TemplateResponse(
            request=request,
            name="leaderboard/leaderboard.html",
            context={
                "data": response
            }
        )
    return router