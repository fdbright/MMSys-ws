# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/19 00:24

import ujson
import aioredis
from typing import Union


class MyAioredis:

    def __init__(self, db: int = 0, max_conn: int = 100):

        self._pool = aioredis.ConnectionPool(
            max_connections=max_conn,
            host="127.0.0.1",
            port=6379,
            db=db,
            password="8y7bZzQr3",
            decode_responses=True
        )

        self._function = MyAioRedisFunction()

    async def get_conn(self):
        return await aioredis.Redis(connection_pool=self._pool)

    async def open(self, conn: bool = False):
        if conn:
            self._function.conn = await self.get_conn()
        else:
            self._function.conn = None
        return self._function


class MyAioRedisFunction:

    def __init__(self, conn: aioredis.Redis = None):
        self.conn = conn

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def subscribe(self, channel: str, conn: aioredis.Redis = None) -> aioredis.client.PubSub:
        _conn = conn if conn else self.conn
        pub = _conn.pubsub()
        pub.ignore_subscribe_messages = True
        await pub.subscribe(channel)
        return pub

    async def publish(self, channel: str, msg: dict, conn: aioredis.Redis = None) -> None:
        _conn = conn if conn else self.conn
        await _conn.publish(channel, ujson.dumps(msg))

    async def hGet(self, name: str, key: Union[str, list] = None, conn: aioredis.Redis = None) -> Union[dict, list, str]:
        _conn = conn if conn else self.conn
        if key:
            if isinstance(key, str):
                data = await _conn.hget(name, key)
                data = ujson.loads(data) if data else {}
            else:
                data = await _conn.hmget(name, key)
            return data
        else:
            return await _conn.hgetall(name)

    async def hSet(self, name: str, key: str, value: dict, conn: aioredis.Redis = None) -> None:
        _conn = conn if conn else self.conn
        await _conn.hset(name, key, ujson.dumps(value))

    async def hDel(self, name: str, key: str, conn: aioredis.Redis = None) -> None:
        _conn = conn if conn else self.conn
        await _conn.hdel(name, key)

    async def set(self, key: str, value: Union[str, dict], timeout: float = None, conn: aioredis.Redis = None) -> None:
        _conn = conn if conn else self.conn
        await _conn.set(name=key, value=value if isinstance(value, str) else ujson.dumps(value), ex=timeout)

    async def get(self, key: str, load: bool = True, conn: aioredis.Redis = None) -> Union[str, dict]:
        _conn = conn if conn else self.conn
        data = await _conn.get(name=key)
        if load:
            try:
                return ujson.loads(data) if data else None
            except Exception as e:
                return data
        else:
            return data

    async def delete(self, key: str, conn: aioredis.Redis = None) -> None:
        _conn = conn if conn else self.conn
        await _conn.delete(key)


if __name__ == '__main__':
    pass
