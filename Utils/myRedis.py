# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 22:05

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import Union

import json
import redis
# from Config import Configure


class MyRedisFunction:

    def __init__(self, conn: redis.Redis = None):
        self.conn: Union[None, redis.Redis] = conn

    def close(self):
        if self.conn:
            self.conn.close()

    def subscribe(self, channel: str, conn: redis.Redis = None):
        """订阅频道"""
        conn = self.conn if self.conn else conn
        pub = conn.pubsub(ignore_subscribe_messages=True)
        pub.subscribe(channel)
        return pub

    def pub2channel(self, channel: str, msg: dict, conn: redis.Redis = None):
        """发布消息"""
        conn = self.conn if self.conn else conn
        conn.publish(channel, json.dumps(msg))

    def hSet(self, name: str, key: str, value: Union[str, dict], conn: redis.Redis = None):
        """哈希写入"""
        conn = self.conn if self.conn else conn
        conn.hset(name, key, json.dumps(value) if isinstance(value, dict) else value)

    def hGet(self, name: str, key: str, conn: redis.Redis = None) -> Union[str, dict]:
        """哈希读取"""
        conn = self.conn if self.conn else conn
        data = conn.hget(name, key)
        return json.loads(data) if data else {}

    def hGetAll(self, name: str, conn: redis.Redis = None) -> dict:
        """读取所有"""
        conn = self.conn if self.conn else conn
        data = conn.hgetall(name)
        # print(type(data), data)
        return data
        # return dict(zip(
        #     map(lambda x: x if isinstance(x, str) else x.decode(), data.keys()),
        #     map(lambda x: json.loads(x if isinstance(x, str) else x.decode()), data.values())
        # ))

    def hDel(self, name: str, key: str = None, conn: redis.Redis = None):
        """哈希删除"""
        conn = self.conn if self.conn else conn
        if key:
            conn.hdel(name, key)
        else:
            conn.hdel(name)

    def set(self, key: str, value: Union[str, dict], timeout: int = None, conn: redis.Redis = None):
        """写入"""
        conn = self.conn if self.conn else conn
        conn.set(key, json.dumps(value) if isinstance(value, dict) else value, ex=timeout)

    def get(self, key: str, conn: redis.Redis = None) -> Union[str, dict, None]:
        """读取"""
        conn = self.conn if self.conn else conn
        data = conn.get(key)
        if "{" in data:
            return json.loads(data)
        else:
            return data

    def delete(self, key: str, conn: redis.Redis = None):
        """删除"""
        conn = self.conn if self.conn else conn
        conn.delete(key)


class MyRedis:

    def __init__(self, db: int = 0):
        self.pool = redis.ConnectionPool(
            max_connections=100,
            host="127.0.0.1",
            port=6379,
            db=db,
            password="8y7bZzQr3",
            decode_responses=True
        )

    def conn2redis(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)

    def open(self, conn: bool = False) -> MyRedisFunction:
        if conn:
            return MyRedisFunction(self.conn2redis())
        else:
            return MyRedisFunction()


if __name__ == '__main__':
    pass
