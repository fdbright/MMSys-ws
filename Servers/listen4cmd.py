# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/18 12:49

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import ujson
from tornado.queues import Queue
from tornado.ioloop import IOLoop
# from tornado.process import Subprocess

from Config import Configure
from Utils import MyAioredis, MyAioSubprocess


class ListenCmd:

    def __init__(self):
        self._queue = Queue()

        # redis
        self.redis_pool = MyAioredis(0)

        # loop
        self.loop = IOLoop.current()

    async def sub4redis(self):
        conn = await self.redis_pool.open(conn=True)
        pub = await conn.subscribe(channel=Configure.REDIS.run_cmd_channel)
        while True:
            data: list = await pub.parse_response(block=True)
            print(type(data), data)
            if data[0] != "message":
                continue
            await self._queue.put(ujson.loads(data[-1]))

    async def run_cmd(self):
        while True:
            item: dict = await self._queue.get()
            data = await MyAioSubprocess(item["cmd"])
            print(data)

    def run(self):
        self.loop.add_callback(self.run_cmd)
        self.loop.add_callback(self.sub4redis)
        self.loop.start()


if __name__ == '__main__':
    ListenCmd().run()
