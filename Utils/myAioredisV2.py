# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/22 20:23

import sys
sys.path.append("/root/ExchangeApis")

from loguru import logger as log
from typing import Union

from aioredis import ConnectionPool, StrictRedis
from ujson import loads, dumps


class MyAioredis:

    def __init__(self, db: int = 0, max_connections: int = 100):
        self._pool = ConnectionPool(
            max_connections=max_connections,
            host="127.0.0.1",
            port=6379,
            db=db,
            password="8y7bZzQr3",
            decode_responses=True
        )
        self._functools = MyAioredisFunctools()

    async def open(self):
        self._functools.conn = await StrictRedis(connection_pool=self._pool)
        return self._functools


class MyAioredisFunctools:

    def __init__(self, connection: StrictRedis = None):
        self.conn = connection

    async def close(self):
        await self.conn.close()

    async def publish(self, channel: str, message: Union[str, dict]):
        await self.conn.publish(channel, message=dumps(message) if isinstance(message, dict) else message)

    async def subscribe(self, **kwargs):
        pub = self.conn.pubsub(ignore_subscribe_messages=True)
        await pub.subscribe(**kwargs)
        await pub.run()

    async def set(self, key: str, value: Union[str, int, float, dict], timeout: float = None):
        await self.conn.set(name=key, value=dumps(value) if isinstance(value, dict) else value, ex=timeout)

    async def get(self, key: str, load: bool = True) -> Union[str, int, float, dict]:
        data = await self.conn.get(name=key)
        try:
            if load:
                return loads(data) if data else None
            return data
        except TypeError:
            return {}

    async def delete(self, key: str):
        await self.conn.delete(key)

    async def hset(self, name: str, key: Union[str, int, float], value: Union[str, int, float, dict]):
        await self.conn.hset(name=name, key=key, value=dumps(value) if isinstance(value, dict) else value)

    async def hget(self, name: str, key: Union[str, int, float, list] = None, load: bool = True) -> Union[str, int, float, dict]:
        if key:
            if isinstance(key, list):
                data = await self.conn.hmget(name=name, keys=key)
            else:
                data = await self.conn.hget(name=name, key=key)
            return loads(data) if load else data
        else:
            return await self.conn.hgetall(name=name)

    async def hdel(self, name: str, key: Union[str, int, float, list]):
        await self.conn.hdel(name, key)


if __name__ == '__main__':
    pass
