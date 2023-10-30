import asyncio
from contextlib import asynccontextmanager

import aiomysql
import ujson

from helpers.config import mysql_server, mysql_password, mysql_user


class _BotDB:
    pool: aiomysql.Pool = None
    loop = asyncio.get_event_loop()

    async def connect(self):
        self.pool = await aiomysql.create_pool(
            host=mysql_server, user=mysql_user, password=mysql_password, db='kozlo_db', autocommit=True, loop=self.loop)

    @asynccontextmanager
    async def cursor(self):
        if self.pool is None:
            await self.connect()

        conn_cm = self.pool.acquire()
        conn = await conn_cm.__aenter__()

        cur_cm = conn.cursor()
        try:
            yield await cur_cm.__aenter__()

        finally:
            await conn_cm.__aexit__(None, None, None)
            await cur_cm.__aexit__(None, None, None)

    async def execute(self, query, args=None, fetch=0):
        print(query, args)
        async with self.cursor() as cur:
            cur: aiomysql.Cursor
            await cur.execute(query, args)

            if fetch == 1:
                return await cur.fetchone()
            if fetch == 2:
                return await cur.fetchall()
            if fetch == 3:
                return cur.lastrowid

    async def fetchone(self, query, args=None):
        return await self.execute(query, args, 1)

    async def fetchall(self, query, args=None):
        return await self.execute(query, args, 2)

    async def autoincrement(self, query, args=None):
        return await self.execute(query, args, 3)

    async def new_user(self, chat_id, name, desc, is_private):
        await self.execute(
            "REPLACE INTO `users` SET `id` = %s, `name` = %s, `desc` = %s, `is_private` = %s, `only_chess` = 0",
            (chat_id, name, desc, is_private))

    async def set_state(self, chat_id, state: int, data=None):
        if data is not None:
            data = ujson.dumps(data)
        await self.execute("UPDATE `users` SET `state` = %s, `state_data` = %s WHERE `id` = %s;",
                           (state, data, chat_id))

    async def get_state(self, chat_id):
        state, data = await self.fetchone("SELECT `state`, `state_data` FROM `users` WHERE `id` = %s", chat_id)

        if data is not None:
            data = ujson.loads(data)

        return state, data

    async def set_state_safe(self, chat_id, state: int, data=None, allow_empty_state=False):
        if data is not None:
            data = ujson.dumps(data)
        await self.execute(f"UPDATE `users` SET  `state_data` = %s WHERE `id` = %s AND `state` = %s "
                           f"{' OR `state` = -1' if allow_empty_state else ''};",
                           (data, chat_id, state))

    async def get_coord(self, chat_id):
        return await self.fetchone("SELECT ST_X(`coord`), ST_Y(`coord`) FROM `users` WHERE `id` = %s", chat_id)

    async def get_balance(self, chat_id):
        return int((await self.fetchone("SELECT `balance` FROM `users` WHERE `id` = %s", chat_id))[0])


BotDB = _BotDB()
