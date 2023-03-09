# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 01:12

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

# from gevent import monkey
# monkey.patch_all()
# import nest_asyncio
# nest_asyncio.apply()

from loguru import logger as log

from typing import List, Dict

import json
# import gevent
import asyncio
from datetime import timedelta
from dataclasses import dataclass
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import PeriodicCallback

from Models import LbkRestApi
from Utils import MyRedis
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
        self.redis_pool = MyRedis(db=0)
        self.redis = self.redis_pool.open(conn=False)
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

        # self.event_loop = asyncio.get_event_loop()

    def start_sub(self):
        # self.event_loop.run_until_complete(self.sub2redis())
        pass

    def run(self):
        # g1 = gevent.spawn(self.start_sub)
        # gevent.joinall([g1])
        asyncio.run(self.sub2redis())

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
        conn = self.redis_pool.conn2redis()
        pub = self.redis.subscribe(Configure.REDIS.htp_channel_lbk, conn=conn)
        while True:
            item: list = pub.parse_response(block=True)
            # print(type(item), item)
            if item[0] != "message":
                continue
            data: dict = json.loads(item[-1])
            await self.handle(item=data)

    async def init_query(self, account: str, symbol: str):
        conn = self.redis_pool.conn2redis()
        await asyncio.gather(
            self.on_depth(conn, symbol),
            self.on_trade(conn, account, symbol),
            self.on_order(conn, account, symbol),
            self.on_account(conn, account)
        )
        conn.close()

    def on_timer(self, account: str, symbol: str):
        event_loop: List[PeriodicCallback] = []
        conn = self.redis_pool.conn2redis()
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
        conn.close()
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
        self.redis.hSet(
            name=self.redis_name,
            key=f"trade_his_{account}_{symbol}",
            value=data,
            conn=conn
        )

    async def on_order(self, conn, account: str, symbol: str):
        """查询当前挂单"""
        data = await self.api.query_open_orders(symbol)
        self.redis.hSet(
            name=self.redis_name,
            key=f"open_orders_{account}_{symbol}",
            value=data,
            conn=conn
        )

    async def on_account(self, conn, account: str):
        """查询账户余额"""
        data = await self.api.query_account_info()
        self.redis.hSet(
            name=self.redis_name,
            key=f"account_data_{account}",
            value=data,
            conn=conn
        )

    async def on_depth(self, conn, symbol: str):
        """查询深度信息"""
        data = await self.api.query_depth(symbol)
        self.redis.hSet(
            name=self.redis_name,
            key=f"depth_data_{symbol}",
            value=data,
            conn=conn
        )


if __name__ == '__main__':
    LbkHtpData().run()

