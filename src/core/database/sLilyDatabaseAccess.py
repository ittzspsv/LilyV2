import aiosqlite
import asyncio
from typing import Optional

class LilyDatabaseAccess:
    def __init__(self) -> None:
        self.db: Optional[aiosqlite.Connection] = None
        self.cache = {}
        self._lock = asyncio.Lock()

    @classmethod
    async def connect(cls, db_path: str = "database.db"):
        self = cls()
        self.db = await aiosqlite.connect(db_path)
        self.db.row_factory = aiosqlite.Row
        await self.load_cache()
        return self
    
    async def refresh_cache(self):
        await self.load_cache()
    
    def _validate_db(self) -> aiosqlite.Connection:
        if self.db is None:
            raise RuntimeError("Database not connected")
        return self.db

    async def execute(self, query: str, params: tuple = (), commit: bool = True):
        async with self._lock:
            assert self.db is not None
            cursor = await self.db.execute(query, params)

            if commit:
                await self.db.commit()

            return cursor.lastrowid

    async def executemany(self, query: str, params: list[tuple], commit: bool = True):
        async with self._lock:
            assert self.db is not None

            await self.db.executemany(query, params)

            if commit:
                await self.db.commit()

    async def commit(self):
        async with self._lock:
            assert self.db is not None
            await self.db.commit()

    async def fetch_one(self, query: str, params: tuple = ()):
        assert self.db is not None
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple = ()):
        assert self.db is not None
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def load_cache(self):
        raise NotImplementedError

    async def close(self):
        assert self.db is not None
        await self.db.close()