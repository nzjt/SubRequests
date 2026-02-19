import aiosqlite


class RequestsManager:
    def __init__(self):
        self.db = None

    async def init(self, filename):
        self.db = await aiosqlite.connect(filename)
        await self.db.execute("CREATE TABLE IF NOT EXISTS requests(id VARCHAR(8) PRIMARY KEY, user VARCHAR(32), class VARCHAR(128), time int)")
        await self.db.execute("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value int)")
        await self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('index', 0)")
        await self.db.commit()

    async def get_index(self):
        async with self.db.execute("SELECT value FROM metadata WHERE key = 'index'") as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def add_request(self, user: str, class_: str, time: int):
        index = await self.get_index()
        await self.db.execute("INSERT INTO requests VALUES (?, ?, ?, ?)", (index, user, class_, time))
        await self.db.execute("UPDATE metadata SET value = value + 1 WHERE key = 'index'")
        await self.db.commit()

    async def remove(self, id_: str):
        await self.db.execute("DELETE FROM requests WHERE id = ?", (id_,))
        await self.db.commit()

    async def query_by_user(self, user: str = ""):
        async with self.db.execute("SELECT id, class, time FROM requests WHERE user = ? ORDER BY time", (user,)) as cursor:
            return await cursor.fetchall()

    async def query_all(self, user: str = ""):
        async with self.db.execute("SELECT * FROM requests ORDER BY time") as cursor:
            return await cursor.fetchall()

    async def query_by_id(self, id_: str = ""):
        async with self.db.execute("SELECT user, class, time FROM requests WHERE id = ?", (id_,)) as cursor:
            return await cursor.fetchone()
