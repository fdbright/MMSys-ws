# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 01:12

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import List, Dict

import ujson
from datetime import timedelta
from dataclasses import dataclass
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop, PeriodicCallback

from Models import LbkRestApi
from Utils import MyAioredis
from Config import Configure


@dataclass
class Status:
    symbol: str
    account: str
    counts: int = 1
    event_pool: list = None


class LbkHtpData:

    def __init__(self):
        self.exchange: str = "lbk"
        self.redis_pool = MyAioredis(db=0)
        self.htp_client = AsyncHTTPClient()
        self.api = LbkRestApi(self.htp_client)

        # redis
        self.redis_name = "LBK-DB"
        self.trade_key = "trade_his_{}_{}"
        self.depth_key = "depth_data_{}"
        self.order_key = "open_orders_{}_{}"
        self.account_key = "account_data_{}"

        # 正在币运行数据源
        self.running_symbol: Dict[str, Status] = {}

        # loop
        self.loop = IOLoop.current()

    def start_sub(self):
        pass

    def run(self):
        pass

    async def handle(self, item: dict):
        todo: str = item["todo"]
        symbol: str = item["symbol"]
        account: str = item["account"]
        self.api.api_key = item["api_key"]
        self.api.secret_key = item["secret_key"]
        if todo == "to_start":
            if symbol in self.running_symbol.keys():
                self.running_symbol[symbol].account += 1
            else:
                await self.init_query(account, symbol)
                event_pool = self.on_timer(account, symbol)
                self.running_symbol[symbol] = Status(symbol, account, event_pool=event_pool)
        else:
            status = self.running_symbol.get(symbol, None)
            if status:
                if status.counts == 1:
                    self.stop_event(status.event_pool)
                    del self.running_symbol[symbol]
                else:
                    self.running_symbol[symbol].counts -= 1
            else:
                pass

    async def sub2redis(self):
        conn = await self.redis_pool.open(conn=True)
        pub = await conn.subscribe(Configure.REDIS.htp_channel_lbk)
        while True:
            item: list = pub.parse_response(block=True)
            # print(type(item), item)
            if item[0] != "message":
                continue
            data: dict = ujson.loads(item[-1])
            await self.handle(item=data)

    async def init_query(self, account: str, symbol: str):
        conn = await self.redis_pool.open(conn=True)
        await asyncio.gather(
            self.on_depth(conn, symbol),
            self.on_trade(conn, account, symbol),
            self.on_order(conn, account, symbol),
            self.on_account(conn, account)
        )
        await conn.close()

    async def on_timer(self, account: str, symbol: str):
        event_loop: List[PeriodicCallback] = []
        conn = await self.redis_pool.open(conn=True)
        # 定时查询最近成交
        event_loop.append(PeriodicCallback(
            callback=lambda: self.on_trade(conn, account, symbol),
            callback_time=timedelta(seconds=10), jitter=0.2
        ))
        # 定时查询当前挂单
        event_loop.append(PeriodicCallback(
            callback=lambda: self.on_order(conn, account, symbol),
            callback_time=timedelta(seconds=2), jitter=0.2
        ))
        # 定时查询账户余额
        event_loop.append(PeriodicCallback(
            callback=lambda: self.on_account(conn, account),
            callback_time=timedelta(seconds=5), jitter=0.2
        ))
        await conn.close()
        self.start_event(event_loop)
        return event_loop

    @staticmethod
    def start_event(event_loop: List[PeriodicCallback]):
        for p in event_loop:
            p.start()

    @staticmethod
    def stop_event(event_loop: List[PeriodicCallback]):
        for p in event_loop:
            p.stop()

    async def on_trade(self, conn, account: str, symbol: str):
        """查询历史成交"""
        data = await self.api.query_trans_history(symbol)
        await conn.hSet(
            name=self.redis_name,
            key=f"trade_his_{account}_{symbol}",
            value=data,
        )

    async def on_order(self, conn, account: str, symbol: str):
        """查询当前挂单"""
        data = await self.api.query_open_orders(symbol)
        await conn.hSet(
            name=self.redis_name,
            key=f"open_orders_{account}_{symbol}",
            value=data,
        )

    async def on_account(self, conn, account: str):
        """查询账户余额"""
        data = await self.api.query_account_info()
        await conn.hSet(
            name=self.redis_name,
            key=f"account_data_{account}",
            value=data,
        )

    async def on_depth(self, conn, symbol: str):
        """查询深度信息"""
        data = await self.api.query_depth(symbol)
        await conn.hSet(
            name=self.redis_name,
            key=f"depth_data_{symbol}",
            value=data,
        )


if __name__ == '__main__':
    LbkHtpData().run()

