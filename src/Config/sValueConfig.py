import aiosqlite

vdb = None
cdb = None
combo_db = None
async def initialize():
    global vdb, cdb, combo_db
    vdb = await aiosqlite.connect("storage/configs/ValueData.db")
    cdb = await aiosqlite.connect("storage/configs/Configs.db")
    combo_db = await aiosqlite.connect("storage/configs/ComboData.db")