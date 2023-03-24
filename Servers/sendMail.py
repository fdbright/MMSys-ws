# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/22 23:52

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import ujson
from tornado.queues import Queue
from tornado.ioloop import IOLoop

from Config import Configure
from Utils import MyEmail, MyAioredis


class SendMail:

    def __init__(self):

        # loop
        self.loop = IOLoop.current()
        self._queue = Queue()
        self.redis_pool = MyAioredis(db=0)

        self.me = MyEmail(Configure.EMAIL.host, Configure.EMAIL.user, Configure.EMAIL.password)
        self.channel = Configure.REDIS.send_mail_channel

    async def subscribe(self):
        conn = await self.redis_pool.open(conn=True)
        pub = await conn.subscribe(channel=self.channel)
        while True:
            item: list = await pub.parse_response(block=True)
            # print(type(item), item)
            if item[0] != "message":
                continue
            await self._queue.put(ujson.loads(item[-1]))

    async def send_mail(self):
        while True:
            item: dict = await self._queue.get()
            self.me.init_msg(receivers=item["receivers"], sub_title=item["title"], sub_content=item["content"])
            self.me.send_mail()

    def run(self):
        self.loop.add_callback(self.send_mail)
        self.loop.add_callback(self.subscribe)

        self.loop.start()


if __name__ == '__main__':
    SendMail().run()

