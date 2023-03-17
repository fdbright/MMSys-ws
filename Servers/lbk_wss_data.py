# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/14 17:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

import nest_asyncio
nest_asyncio.apply()

from loguru import logger as log

import time
import json
import asyncio
from aiohttp.http_websocket import WSMessage
from aiohttp import ClientSession, ClientWebSocketResponse

from Utils import MyRedis, start_event_loop
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

        self._session: ClientSession = None
        self._ws: ClientWebSocketResponse = None

        self.loop4sub2redis = asyncio.new_event_loop()
        self.loop4sub2wss = asyncio.new_event_loop()

    def sub2redis(self):
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
                    self.add_event_wss(self.write_message(data))
                else:
                    self.sub_dict[key] += 1
            else:
                if client_count == 0:
                    pass
                elif client_count == 1:
                    self.sub_dict[key] = 0
                    self.add_event_wss(self.write_message(data))
                else:
                    self.sub_dict[key] -= 1

    async def write_message(self, data: dict):
        await self._ws.send_str(json.dumps(data))

    async def sub2wss(self):
        self._session: ClientSession = ClientSession()
        while True:
            try:
                self._ws = await self._session.ws_connect(url=LBKUrl.HOST.data_wss, ssl=False)
                async for msg in self._ws:  # type: WSMessage
                    try:
                        item: dict = msg.json()
                    except json.decoder.JSONDecodeError:
                        log.warning(f"websocket data: {msg.data}")
                    else:
                        print(item)
                        await self.on_packet(item)
            except Exception as e:
                log.warning(f"websocket 异常: {e}, 即将重连")
                time.sleep(5)

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
        await self.write_message(data={"action": "pong", "pong": data["ping"]})

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

    def add_event_wss(self, coro: asyncio.coroutine):
        asyncio.run_coroutine_threadsafe(coro, self.loop4sub2wss)

    def run(self):
        start_event_loop(self.loop4sub2wss)
        self.add_event_wss(self.sub2wss())
        self.sub2redis()


if __name__ == '__main__':
    LbkWssData().run()
