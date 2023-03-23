# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/23 16:21

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import ujson
from datetime import timedelta
from tornado.queues import Queue
from tornado.options import define, options
from tornado.ioloop import IOLoop, PeriodicCallback

from Objects import Status, OrderData, TradeData
from Utils import MyAioredis, MyAioSubprocess


class TradeCache:

    def __init__(self):

        self.exchange: str = options.exchange.lower()

        # loop
        self.loop = IOLoop.current()
        self.add_queue = Queue()

        self.running_cmd = "sudo supervisorctl status ZFT_STG:* |grep RUNNING|awk '{print $1}'"

        # redis
        self.redis_pool = MyAioredis(1)
        self.channel = "TradeCacheLBK"

        self.name: str = self.exchange.upper() + "-TRADE-{symbol}"
        # self.key: str = "{exchange}-TRADE-{symbol}"
        self.trade_size_key: str = "trade_size"

        self.hr2_sec: int = 2 * 60 * 60 * 1000

    async def subscribe(self):
        conn = await self.redis_pool.open(conn=True)
        pub = await conn.subscribe(channel=self.channel)
        while True:
            item: list = await pub.parse_response(block=True)
            # print(type(item), item)
            if item[0] != "message":
                continue
            data: OrderData = OrderData(**ujson.loads(item[-1]))
            # print(data)
            await self.add_queue.put(data)

    async def route(self):
        while True:
            item: OrderData = await self.add_queue.get()
            if item.status == Status.NODEAL:
                await self.fresh(item)
            elif item.status == Status.PARTIAL:
                await self.refresh(item)
            elif item.status == Status.ALLDEAL:
                await self.refresh(item)
            elif item.status == Status.CANCELING:
                continue
            else:   # type: Status.CANCELLED
                await self.delete(item)

    @staticmethod
    def init_trade(item: OrderData, old_data: dict = None) -> TradeData:
        if old_data:
            return TradeData(
                traded=item.traded + old_data.get("traded", 0),
                datetime=item.datetime,
                type=item.type
            )
        return TradeData(traded=item.traded, datetime=item.datetime, type=item.type)

    async def fresh(self, item: OrderData):
        conn = await self.redis_pool.open(conn=True)
        await conn.hSet(
            name=self.name.format(symbol=item.symbol),
            key=item.customer_id,
            value=self.init_trade(item=item).to_dict()
        )
        await conn.close()
        del conn

    async def refresh(self, item: OrderData):
        conn = await self.redis_pool.open(conn=True)
        name = self.name.format(symbol=item.symbol)
        old_data: dict = await conn.hGet(name=name, key=item.customer_id)
        await conn.hSet(name=name, key=item.customer_id, value=self.init_trade(item=item, old_data=old_data).to_dict())
        await conn.close()
        del conn, name, old_data

    async def delete(self, item: OrderData):
        conn = await self.redis_pool.open(conn=True)
        name = self.name.format(symbol=item.symbol)
        if item.traded == 0:
            await conn.hDel(name=name, key=item.customer_id)
        else:
            old_data: dict = await conn.hGet(name=name, key=item.customer_id)
            await conn.hSet(name=name, key=item.customer_id, value=self.init_trade(item=item, old_data=old_data).to_dict())
        await conn.close()
        del conn, name, old_data

    async def cal_trade_size(self, conn, symbol):
        name: str = self.name.format(symbol=symbol)
        data: dict = await conn.hGet(name=name)
        if not data:
            del name, data
            return
        bid_size, ask_size = 0, 0
        for custom_id, value in data.items():  # type: str, str
            val: dict = ujson.loads(value)
            if self.loop.time() * 1000 - int(val["datetime"]) > self.hr2_sec:
                await conn.hDel(name=name, key=custom_id)
                continue
            if val["type"] == "buy":  # type: str
                bid_size += float(val["traded"])
            else:
                ask_size += float(val["traded"])
        if bid_size or ask_size:
            await conn.hSet(name=name, key=self.trade_size_key, value={"bid_size": bid_size, "ask_size": ask_size})
        del name, data, bid_size, ask_size

    async def on_timer(self):
        data = await MyAioSubprocess(self.running_cmd)
        if data == "":
            return []
        symbols = [v[8:] for v in data.split("\n")]
        conn = await self.redis_pool.open(conn=True)
        for symbol in symbols:
            await self.cal_trade_size(conn, symbol)
        await conn.close()
        del conn, symbol, data

    def run(self):
        self.loop.add_callback(self.route)
        self.loop.add_callback(self.subscribe)
        PeriodicCallback(self.on_timer, callback_time=timedelta(seconds=5), jitter=0.2).start()
        self.loop.start()


if __name__ == '__main__':
    define("exchange", default="lbk", type=str)
    options.parse_command_line()

    TradeCache().run()
