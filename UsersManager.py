import aiosqlite


class UsersManager:
    def __init__(self):
        self.db = None

    async def init(self, filename):
        self.db = await aiosqlite.connect(filename)
        await self.db.execute("CREATE TABLE IF NOT EXISTS users(id VARCHAR(32) PRIMARY KEY, timezone VARCHAR(64) DEFAULT '', admin BOOL DEFAULT FALSE)")
        await self.db.commit()

    async def query_admin(self, user: str):
        async with self.db.execute("SELECT admin FROM users WHERE id = ?", (user,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                return False

    async def query_all_admins(self):
        async with self.db.execute("SELECT id FROM users WHERE admin = TRUE") as cursor:
            return await cursor.fetchall()

    async def update_admin(self, user: str, admin: bool):
        await self.db.execute(
            "INSERT INTO users (id, admin)"
            "VALUES (?, ?)"
            "ON CONFLICT(id) DO UPDATE SET admin = excluded.admin",
            (user, admin)
        )
        await self.db.commit()

    async def query_timezone(self, user: str):
        async with self.db.execute("SELECT timezone FROM users WHERE id = ?", (user,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            else:
                return None

    async def update_timezone(self, user: str, timezone: str):
        await self.db.execute(
            "INSERT INTO users (id, timezone)"
            "VALUES (?, ?)"
            "ON CONFLICT(id) DO UPDATE SET timezone = excluded.timezone",
            (user, timezone)
        )
        await self.db.commit()
