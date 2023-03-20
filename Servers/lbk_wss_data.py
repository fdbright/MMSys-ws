# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/14 17:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import Dict

import ujson
from aiohttp import ClientSession
from tornado.ioloop import IOLoop

from Utils import MyAioredis, WebsocketClient
from Objects import DepthReturn
from Config import Configure, LBKUrl


class LbkWssData(WebsocketClient):

    def __init__(self):
        super().__init__()
        self.exchange: str = "lbk"

        # loop
        self.loop = IOLoop.current()

        # redis
        self.redis_pool = MyAioredis(db=0)
        self.redis_name = "LBK-DB"
        self.depth_data_key = "depth_data_{symbol}"

        self.sub_dict: Dict[tuple, int] = {}
        self.channel: str = Configure.REDIS.wss_channel_lbk

        # wss
        self.session = ClientSession(trust_env=True)

    async def sub2redis(self):
        conn = await self.redis_pool.open(conn=True)
        pub = await conn.subscribe(self.channel)
        while True:
            item: list = await pub.parse_response(block=True)
            # print(type(item), item)
            if item[0] != "message":
                continue
            data: dict = ujson.loads(item[-1])
            pair: str = data["pair"]
            action: str = data["action"]
            channel: str = data["subscribe"]
            key: tuple = (pair, channel)
            client_count = self.sub_dict.get(key, 0)
            if action == "subscribe":
                if client_count == 0:
                    self.sub_dict[key] = 1
                    await self.send_packet(data)
                else:
                    self.sub_dict[key] += 1
            else:
                if client_count == 0:
                    pass
                elif client_count == 1:
                    self.sub_dict[key] = 0
                    await self.send_packet(data)
                    await conn.hDel(name=self.redis_name, key=self.depth_data_key.format(symbol=pair))
                else:
                    self.sub_dict[key] -= 1

    async def on_packet(self, data: dict):
        if data.get("action", None) == "ping":
            await self.on_ping(data)
            return
        _type: str = data.get("type", None)
        if _type == "depth":
            await self.on_depth(data)
        else:
            pass

    async def on_ping(self, data: dict):
        await self.send_packet(data={"action": "pong", "pong": data["ping"]})

    @staticmethod
    def __init4depth(row: list) -> list:
        r1, r2 = float(row[0]), float(row[1])
        return [r1, r2, r1 * r2]

    async def on_depth(self, data: dict):
        conn = await self.redis_pool.open(conn=True)
        pair: str = data["pair"]
        depth: dict = data["depth"]
        dr = DepthReturn(
            exchange=self.exchange,
            asks=list(map(self.__init4depth, depth["asks"])),
            bids=list(map(self.__init4depth, depth["bids"]))
        )
        await conn.hSet(
            name=self.redis_name,
            key=self.depth_data_key.format(symbol=pair),
            value=dr.to_dict(),
        )
        await conn.close()

    def run(self):
        self.loop.add_callback(lambda: self.subscribe(url=LBKUrl.HOST.data_wss))
        self.loop.add_callback(self.sub2redis)
        self.loop.start()


if __name__ == '__main__':
    LbkWssData().run()
