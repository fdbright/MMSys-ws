# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/15 20:17

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import os
import ujson
from datetime import timedelta
from aiohttp import ClientSession
from sshtunnel import SSHTunnelForwarder
from tornado.gen import sleep
from tornado.queues import Queue
from tornado.ioloop import IOLoop, PeriodicCallback

from Config import Configure
from Utils import MyAioredis, MyAioSubprocess
from Utils.myEncoder import MyEncoder
from Models import LbkRestApi


class MonitorSTG:

    def __init__(self, exchange: str, server_id: int = 133, default_server: int = 133):

        self.exchange = exchange.lower()
        self.server_id = server_id
        self.default_server = default_server

        self.start_cmd = "nohup /home/ec2-user/anaconda3/envs/lbk-tornado/bin/python " \
                         "../Strategy/followTickTemplate.py " \
                         "--symbol={symbol} " \
                         "--exchange={exchange} " \
                         "--server_id={server_id} " \
                         "--step_gap={step_gap} " \
                         "--order_amount={order_amount} " \
                         "--order_nums={order_nums} " \
                         "--profit_rate={profit_rate} " \
                         "> /dev/null 2>&1 &"

        self.stop_cmd = "sudo ps -ef|grep followTickTemplate" \
                        "|grep {symbol}|grep {exchange}|grep {server_id}"

        self.count_cmd = "ps -ef | grep followTickTemplate.py | grep -v grep | wc -l"

        self.db_data: dict = {}
        self.todo = Queue()

        self.running_stg: list = []

        # api
        self.api: LbkRestApi = None

        # redis this
        self.redis_pool_this = MyAioredis(0)
        self.name: str = f"{self.exchange.upper()}-DB"
        self.name_stg: str = f"{self.exchange.upper()}-STG-DB"
        self.stg_count: int = 0

        self.server: SSHTunnelForwarder = self.ssh4redis()
        if self.server_id != self.default_server:
            self.server.start()

        # redis 201
        self.redis_pool_that = MyAioredis(0)
        self.channel = Configure.REDIS.stg_ws_channel.format(exchange=self.exchange.upper(), server_id=self.server_id)

        self.fp = os.path.join(Configure.LOG_PATH, "monitor_stg.log")
        # log.add(self.fp, retention="2 days", encoding="utf-8")

        # loop
        self.loop = IOLoop.current()

    async def init_api(self):
        self.api = LbkRestApi(ClientSession(trust_env=True))

    @staticmethod
    def ssh4redis():
        return SSHTunnelForwarder(
            ("13.229.166.133", 22),
            ssh_pkey="/home/ec2-user/.ssh/id_rsa88",
            ssh_username="ec2-user",
            ssh_password="shyuan121",
            local_bind_address=("0.0.0.0", 6379),
            remote_bind_address=('0.0.0.0', 6379),
        )

    async def get_info_from_redis(self):
        conn = await self.redis_pool_this.open(conn=True)
        self.db_data = await conn.hGet(name=self.name, key=f"{self.exchange}_db")
        await conn.close()
        del conn

    async def clone_redis(self):
        redis_this = await self.redis_pool_this.open(conn=True)
        redis_that = await self.redis_pool_that.open(conn=True)

        cmc_data = await redis_that.hGetAll(name="CMC-DB")
        for key, value in cmc_data.items():
            redis_this.hSet(name="CMC-DB", key=key, value=value)
        del cmc_data

        dex_data = await redis_that.hGetAll(name="DEX-DB")
        for key, value in dex_data.items():
            await redis_this.hSet(name="DEX-DB", key=key, value=value)
        del dex_data

        cex_data = await redis_that.hGet(name=self.name, key=f"{self.exchange}_price")
        await redis_this.hSet(name=self.name, key=f"{self.exchange}_price", value=cex_data)
        del cex_data

        stg_data = await redis_this.hGetAll(name=self.name_stg)
        for key, value in stg_data.items():
            await redis_that.hSet(name=self.name_stg, key=key, value=value)
        del stg_data

        await redis_that.close()
        await redis_this.close()
        del redis_that, redis_this

    async def sub2redis(self):
        conn = await self.redis_pool_this.open(conn=True)
        pub = await conn.subscribe(channel=self.channel)
        while True:
            item: list = await pub.parse_response(block=True)
            print(type(item), item)
            if item[0] != "message":
                continue
            data = ujson.loads(item[-1])
            await self.todo.put(data)

    async def route(self):
        while True:
            item: dict = await self.todo.get()
            if item["todo"] == "start":
                await self.start(item)
            else:
                await self.stop(item)

    async def start(self, item: dict):
        symbol = item["symbol"]
        if symbol in self.running_stg:
            return
        conf: dict = item["conf"]
        cmd: str = self.start_cmd.format(
            symbol=symbol, exchange=self.exchange, server_id=self.server_id,
            step_gap=conf["step_gap"],
            order_amount=conf["order_amount"],
            order_nums=conf["order_nums"],
            profit_rate=conf["profit_rate"]
        )
        print(cmd)
        conn = await self.redis_pool_this.open(conn=True)
        await conn.hSet(name=self.name_stg, key=f"fts_status_{symbol}", value={"status": "starting"})
        # await conn.publish(channel=Configure.REDIS.run_cmd_channel, msg={"cmd": cmd})
        await conn.close()
        await MyAioSubprocess(cmd)
        log.info(f"启动策略: {symbol}")
        self.running_stg.append(symbol)
        del symbol, conf, cmd, conn

    async def stop(self, item: dict):
        symbol = item["symbol"]
        cmd = self.stop_cmd.format(
            symbol=symbol, exchange=self.exchange, server_id=self.server_id
        ) + "|awk '{print $2}'|xargs kill"
        print(cmd)
        await MyAioSubprocess(cmd)
        conn = await self.redis_pool_this.open(conn=True)
        # await conn.publish(channel=Configure.REDIS.run_cmd_channel, msg={"cmd": cmd})
        await sleep(0.01)
        await conn.hDel(name=self.name_stg, key=f"fts_status_{symbol}")
        await conn.close()
        await self.cancel_orders(symbol)
        log.info(f"关闭策略: {symbol}")
        try:
            self.running_stg.remove(symbol)
        except ValueError:
            pass
        del symbol, cmd, conn

    async def cancel_orders(self, symbol: str):
        conf = self.db_data[symbol]
        self.api.api_key = conf["apiKey"]
        self.api.secret_key = MyEncoder.byDES(Configure.SECRET_KEY).decode(conf["secretKey"])
        conn = await self.redis_pool_this.open(conn=True)
        data = await conn.hGet(name=self.name_stg, key=f"order_ids_{symbol}")
        order_ids = data.get("orderIds", [])
        for order_id in order_ids:
            await self.api.cancel_order(symbol=symbol, order_id=order_id)
        await conn.hDel(name=self.name_stg, key=f"order_ids_{symbol}")
        await conn.close()
        log.info(f"策略撤单: {symbol}")
        del conf, conn, data, order_ids

    async def cal_stg_count(self):
        conn = await self.redis_pool_this.open(conn=True)
        self.stg_count = await MyAioSubprocess(self.count_cmd)
        await conn.hSet(name=self.name_stg, key=f"stg_count_{self.server_id}", value={"count": int(self.stg_count)})
        await conn.close()
        del conn

    def run(self):
        self.loop.run_sync(self.init_api)
        self.loop.run_sync(self.get_info_from_redis)

        if self.server_id != self.default_server:
            PeriodicCallback(callback=self.clone_redis, callback_time=timedelta(seconds=5), jitter=0.2).start()

        PeriodicCallback(callback=self.get_info_from_redis, callback_time=timedelta(minutes=1), jitter=0.2).start()
        PeriodicCallback(callback=self.cal_stg_count, callback_time=timedelta(seconds=1), jitter=0.2).start()
        self.loop.add_callback(self.route)
        self.loop.add_callback(self.sub2redis)

        self.loop.start()


if __name__ == '__main__':
    MonitorSTG(exchange="lbk", server_id=133, default_server=133).run()
