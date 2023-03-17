# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/15 20:17

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import os
import time
import json
import asyncio
from queue import Queue
from datetime import timedelta
from threading import Thread
from aiohttp import ClientSession
from sshtunnel import SSHTunnelForwarder
from tornado.ioloop import IOLoop, PeriodicCallback

from Config import Configure
from Utils import MyRedis, MySubprocess, start_event_loop
from Utils.myEncoder import MyEncoder
from Models import LbkRestApi


class MonitorSTG:

    def __init__(self, exchange: str, server_id: int = 148):

        self.exchange = exchange.lower()
        self.server_id = server_id

        self.start_cmd = "nohup ~/anaconda3/envs/lbk-tornado/bin/python " \
                         "../Strategy/followTickTemplate.py " \
                         "{symbol} {exchange} {server_id} {step_gap} {order_amount} {order_nums} {profit_rate} " \
                         ">/dev/null 2>&1 &"
        self.stop_cmd = "sudo ps -ef|grep followTickTemplate" \
                        "|grep {symbol}|grep {exchange}|grep {server_id}"

        self.count_cmd = "ps -ef | grep ./followTickTemplate.py | grep -v grep | wc -l"

        self.db_data: dict = {}
        self.todo = Queue()

        self.running_stg: list = []

        # api
        self.api: LbkRestApi = None

        # redis this
        self.redis_pool_this = MyRedis(0)
        self.name: str = f"{self.exchange.upper()}-DB"
        self.name_stg: str = f"{self.exchange.upper()}-STG-DB"
        self.stg_count: int = 0

        self.server: SSHTunnelForwarder = self.ssh4redis()
        if self.server_id != 148:
            self.server.start()

        # redis 201
        self.redis_pool_that = MyRedis(0)
        self.channel = Configure.REDIS.stg_ws_channel.format(exchange=self.exchange.upper(), server_id=self.server_id)

        self.fp = os.path.join(Configure.LOG_PATH, "monitor_stg.log")
        log.add(self.fp, retention="2 days", encoding="utf-8")

        # loop
        self.loop4clone = asyncio.new_event_loop()
        self.loop4sub = asyncio.new_event_loop()
        self.loop4api = asyncio.new_event_loop()
        self.loop4route = asyncio.new_event_loop()

    async def init_api(self):
        self.api = LbkRestApi(ClientSession(trust_env=True, loop=self.loop4api))

    @staticmethod
    def ssh4redis():
        return SSHTunnelForwarder(
            ("13.250.110.201", 22),
            ssh_pkey="/home/ec2-user/.ssh/id_rsa88",
            ssh_username="ec2-user",
            ssh_password="shyuan121",
            local_bind_address=("0.0.0.0", 6379),
            remote_bind_address=('0.0.0.0', 6379),
        )

    def get_info_from_redis(self):
        redis = self.redis_pool_this.open(conn=True)
        self.db_data = redis.hGet(name=self.name, key=f"{self.exchange}_db")
        redis.close()
        del redis

    async def clone_redis(self):
        redis_this = self.redis_pool_this.open(conn=True)
        redis_that = self.redis_pool_that.open(conn=True)

        cmc_data = redis_that.hGetAll(name="CMC-DB")
        for key, value in cmc_data.items():
            redis_this.hSet(name="CMC-DB", key=key, value=value)
        del cmc_data

        dex_data = redis_that.hGetAll(name="DEX-DB")
        for key, value in dex_data.items():
            redis_this.hSet(name="DEX-DB", key=key, value=value)
        del dex_data

        cex_data = redis_that.hGet(name=self.name, key=f"{self.exchange}_price")
        redis_this.hSet(name=self.name, key=f"{self.exchange}_price", value=cex_data)
        del cex_data

        stg_data = redis_this.hGetAll(name=self.name_stg)
        for key, value in stg_data.items():
            redis_that.hSet(name=self.name_stg, key=key, value=value)
        del stg_data

        redis_that.close()
        redis_this.close()
        del redis_that, redis_this

    def sub2redis(self):
        redis = self.redis_pool_this.open(conn=True)
        pub = redis.subscribe(channel=self.channel)
        while True:
            item: list = pub.parse_response(block=True)
            print(type(item), item)
            if item[0] != "message":
                continue
            data = json.loads(item[-1])
            self.todo.put(data)

    async def route(self):
        while True:
            item: dict = self.todo.get(block=True)
            if item["todo"] == "start":
                await self.start(item)
            else:
                await self.stop(item)
            time.sleep(0.01)

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
        redis = self.redis_pool_this.open(conn=True)
        redis.hSet(name=self.name_stg, key=f"fts_status_{symbol}", value={"status": "starting"})
        redis.close()
        MySubprocess(cmd=cmd)
        log.info(f"启动策略: {symbol}")
        self.running_stg.append(symbol)
        del symbol, conf, cmd, redis

    async def stop(self, item: dict):
        symbol = item["symbol"]
        cmd = self.stop_cmd.format(
            symbol=symbol, exchange=self.exchange, server_id=self.server_id
        ) + "|awk '{print $2}'|xargs kill"
        MySubprocess(cmd=cmd)
        self.add_event_api(self.cancel_orders(symbol))
        redis = self.redis_pool_this.open(conn=True)
        redis.hSet(name=self.name_stg, key=f"fts_status_{symbol}", value={"status": "stopped"})
        redis.close()
        log.info(f"关闭策略: {symbol}")
        try:
            self.running_stg.remove(symbol)
        except ValueError:
            pass
        del symbol, cmd, redis

    async def cancel_orders(self, symbol: str):
        conf = self.db_data[symbol]
        self.api.api_key = conf["apiKey"]
        self.api.secret_key = MyEncoder.byDES(Configure.SECRET_KEY).decode(conf["secretKey"])
        redis = self.redis_pool_this.open(conn=True)
        order_ids = redis.hGet(name=self.name_stg, key=f"order_ids_{symbol}").get("orderIds", [])
        for order_id in order_ids:
            await self.api.cancel_order(symbol=symbol, order_id=order_id)
        redis.hDel(name=self.name_stg, key=f"order_ids_{symbol}")
        redis.close()
        log.info(f"策略撤单: {symbol}")
        del conf, redis, order_ids

    def cal_stg_count(self):
        redis = self.redis_pool_this.open(conn=True)
        self.stg_count = int(MySubprocess(self.count_cmd).replace("\n", ""))
        redis.hSet(name=self.name_stg, key=f"stg_count_{self.server_id}", value={"count": self.stg_count})
        redis.close()
        del redis

    def add_event_api(self, coro: asyncio.coroutine):
        asyncio.run_coroutine_threadsafe(coro, self.loop4api)

    def run(self):
        start_event_loop(self.loop4api)
        self.add_event_api(self.init_api())

        Thread(target=self.sub2redis).start()
        Thread(target=lambda: self.loop4route.run_until_complete(self.route())).start()

        if self.server_id != 148:
            PeriodicCallback(callback=self.clone_redis, callback_time=timedelta(seconds=5), jitter=0.2).start()

        self.get_info_from_redis()
        PeriodicCallback(callback=self.get_info_from_redis, callback_time=timedelta(minutes=1), jitter=0.2).start()
        PeriodicCallback(callback=self.cal_stg_count, callback_time=timedelta(seconds=1), jitter=0.2).start()
        IOLoop.current().start()


if __name__ == '__main__':
    MonitorSTG(exchange="lbk", server_id=148).run()
