# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 22:03

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from gevent import monkey
monkey.patch_all()
import nest_asyncio
nest_asyncio.apply()

from loguru import logger as log

import json
import gevent
import asyncio
from tornado.httpclient import HTTPRequest
from tornado.websocket import websocket_connect

from Utils import MyRedis
from Objects import DepthReturn
from Config import Configure, LBKUrl


class LbkWssData:

    def __init__(self):
        self.exchange: str = "lbk"
        self.redis_pool = MyRedis(db=0)
        self.redis = self.redis_pool.open(conn=False)

        # redis
        self.redis_name = "LBK-DB"
        self.depth_data_key = "depth_data_{symbol}"

        self.sub_dict: dict = {}
        self.channel: str = Configure.REDIS.wss_channel_lbk
        self.req = HTTPRequest(LBKUrl.HOST.data_wss)
        self.conn = None
        self.event_loop = asyncio.get_event_loop()

    async def sub2redis(self):
        conn = self.redis_pool.conn2redis()
        pub = self.redis.subscribe(self.channel, conn=conn)
        while True:
            item: list = pub.parse_response(block=True)
            print(type(item), item)
            if item[0] != "message":
                continue
            data: dict = json.loads(item[-1])
            pair: str = data["pair"]
            action: str = data["action"]
            channel: str = data["subscribe"]
            key: tuple = (pair, channel)
            client_count = self.sub_dict.get(key, 0)
            if action == "subscribe":
                if client_count == 0:
                    self.sub_dict[key] = 1
                    await self.conn.write_message(data)
                else:
                    self.sub_dict[key] += 1
            else:
                if client_count == 0:
                    pass
                elif client_count == 1:
                    self.sub_dict[key] = 0
                    await self.conn.write_message(data)
                else:
                    self.sub_dict[key] -= 1

    async def on_ping(self, data: dict):
        await self.conn.write_message({"action": "pong", "pong": data["ping"]})

    @staticmethod
    def __init4depth(row: list) -> list:
        r1, r2 = float(row[0]), float(row[1])
        return [r1, r2, r1 * r2]

    async def on_depth(self, data: dict):
        conn = self.redis_pool.conn2redis()
        pair: str = data["pair"]
        depth: dict = data["depth"]
        dr = DepthReturn(
            exchange=self.exchange,
            asks=list(map(self.__init4depth, depth["asks"])),
            bids=list(map(self.__init4depth, depth["bids"]))
        )
        self.redis.hSet(
            name=self.redis_name,
            key=self.depth_data_key.format(symbol=pair),
            value=dr.to_dict(),
            conn=conn
        )
        conn.close()

    async def on_account(self, data: dict):
        pass

    async def on_order(self, data: dict):
        pass

    async def on_trade(self, data: dict):
        pass

    async def subscribe(self):
        self.conn = await websocket_connect(self.req)
        while True:
            data = await self.conn.read_message()
            item: dict = json.loads(data)
            # print("msg:", type(item), item)
            if item.get("action", None) == "ping":
                await self.on_ping(item)
            _type: str = item.get("type", None)
            if _type == "depth":
                await self.on_depth(item)
            elif _type == "trade":
                await self.on_trade(item)
            elif _type == "orderUpdate":
                await self.on_order(item)
            elif _type == "assetUpdate":
                await self.on_account(item)
            else:
                pass

    def start_wss(self):
        self.event_loop.run_until_complete(self.subscribe())

    def start_redis(self):
        self.event_loop.run_until_complete(self.sub2redis())

    def run(self):
        g1 = gevent.spawn(self.start_wss)
        g2 = gevent.spawn(self.start_redis)

        gevent.joinall([g1, g2])


if __name__ == '__main__':
    LbkWssData().run()
