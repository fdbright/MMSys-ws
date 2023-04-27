# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/4/25 18:44

import sys

import ujson

sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import os
from aiohttp import ClientSession
from tornado.gen import sleep
from tornado.queues import Queue
from tornado.ioloop import IOLoop

from Database import db
from Config import Configure
from Utils import MyAioredis, MyAioSubprocess
from Utils.myEncoder import MyEncoder
from Models import LbkRestApi, OrmMarket


class MonitorSTG:

    def __init__(self, exchange: str, server: str = "main"):

        self.exchange = exchange.lower()
        self.server = server
        self.default_server: str = "main"

        # loop
        self.loop = IOLoop.current()
        self.todo = Queue()

        # redis this
        self.redis_pool = MyAioredis(0)
        self.name: str = f"{self.exchange.upper()}-DB"
        self.name_stg: str = f"{self.exchange.upper()}-STG-DB"
        # self.name_stg: str = f"{self.exchange.upper()}-STG-WS-DB-{self.default_server}"
        self.stg_count: int = 0
        self.channel = Configure.REDIS.stg_ws_channel.format(exchange=self.exchange.upper(), server=self.server)

        # constants
        self.api = None
        self.db_data: dict = {}
        self.stop_cmd: str = "sudo supervisorctl stop ZFT_STG:{symbol}"
        self.start_cmd: str = "sudo supervisorctl start ZFT_STG:{symbol}"
        self.restart_cmd: str = "sudo supervisorctl restart ZFT_STG:{symbol}"

        # config
        self.config_fp: str = "/etc/supervisor/conf.d/FT_STG.conf"
        self.title: str = "[group:ZFT_STG]\n" \
                          "programs="
        self.value: str = "[program:{symbol}]\n" \
                          "directory=/home/ec2-user/MMSys-ws/Strategy\n" \
                          "command=/home/ec2-user/anaconda3/envs/lbk-tornado/bin/python followTickTemplate.py --server=main --symbol={symbol}\n" \
                          "autostart=false\n" \
                          "autorestart=unexpected\n" \
                          "startretries=3\n" \
                          "startsecs=1\n" \
                          "priority=999\n" \
                          "stderr_logfile=/dev/null\n" \
                          "stdout_logfile=/dev/null\n" \
                          "stopasgroup=true\n" \
                          "killasgroup=true\n" \
                          "user = root\n" \
                          "redirect_stderr = true\n" \
                          "asgfjfghfc_maxbytes = 20M\n" \
                          "stdout_logfile_backups = 20"

        self.fp = os.path.join(Configure.LOG_PATH, "stg_action.log")
        # log.add(self.fp, retention="2 days", encoding="utf-8")

    async def init_by_exchange(self):
        if self.exchange == "lbk":
            self.api = LbkRestApi(ClientSession(trust_env=True))
        else:
            pass

    async def get_data_from_redis(self):
        conn = await self.redis_pool.open(conn=True)
        self.db_data = await conn.hGet(name=self.name, key=f"{self.exchange}_db")
        self.db_data.pop("upgrade_time", None)
        self.db_data.pop("upgrade_time_dt", None)
        await conn.close()
        del conn

    @staticmethod
    async def get_stg_status() -> dict:
        data = await MyAioSubprocess(cmd="sudo supervisorctl status ZFT_STG:*|awk '{print $1,$2}'")
        if data == "":
            return {}
        res = {}
        for row in data.strip().split("\n"):
            symbol, status = row.split(" ")
            res[symbol.replace("ZFT_STG:", "").strip()] = status.strip()
        return res

    async def cancel_orders(self, symbol: str, conn):
        conf = self.db_data[symbol]
        self.api.api_key = conf["apiKey"]
        self.api.secret_key = MyEncoder.byDES(Configure.SECRET_KEY).decode(conf["secretKey"])
        order_ids = await conn.hGet(name=self.name_stg, key=f"order_ids_{symbol}")
        order_ids = order_ids.get("orderIds", [])
        for order_id in order_ids:
            await self.api.cancel_order(symbol=symbol, order_id=order_id)
        await conn.hDel(name=self.name_stg, key=f"order_ids_{symbol}")
        log.info(f"策略撤单: {symbol}")
        del conf, order_ids

    async def upgrade_conf(self, current_status: dict):
        all_symbols: set = set(self.db_data.keys())
        now_symbols: set = set(current_status.keys())
        if all_symbols == now_symbols:
            return
        new_title: list = []
        new_value: list = []
        for symbol in sorted(all_symbols):
            new_title.append(symbol)
            new_value.append(self.value.format(symbol=symbol))
        title = self.title + ",".join(new_title)
        value = "\n\n".join(new_value)
        with open(self.config_fp, "w") as f:
            f.write(title + "\n\n" + value)
        await MyAioSubprocess(cmd="sudo supervisorctl update")
        del all_symbols, now_symbols, new_title, new_value, title, value

    async def check_if_stop(self):
        conn = await self.redis_pool.open(conn=True)
        status: dict = await self.get_stg_status()
        for symbol, sts in status:
            if sts != "RUNNING":
                continue
            log.info(f"策略状态检查-更新时间: {symbol}")
            status_dict: dict = await conn.hGet(name=self.name_stg, key=f"fts_status_{symbol}")
            last_update_time: int = int(status_dict.get("upgrade_time", "-1"))
            if last_update_time == -1:
                continue
            if int(self.loop.time() * 1000) - last_update_time > 150000:
                await self.todo.put({"todo": "restart", "symbol": symbol})
                log.info(f"策略异常-更新时间, 执行重启: {symbol}")
                continue
        await conn.close()
        del conn, status

    async def handle(self):
        async for item in self.todo:  # type: dict
            symbol: str = item["symbol"]
            conn = await self.redis_pool.open(conn=True)
            todo = item["todo"]
            if todo == "start":
                if self.server != self.default_server:
                    await sleep(2)
                status = await MyAioSubprocess(cmd="sudo supervisorctl status ZFT_STG:" + symbol + "|awk '{print $2}'")
                if status not in ["RUNNING", "STARTING"]:
                    await MyAioSubprocess(cmd=self.start_cmd.format(symbol=symbol))
                log.info(f"启动策略: {symbol}")
            elif todo == "stop":
                await MyAioSubprocess(cmd=self.stop_cmd.format(symbol=symbol))
                await conn.hDel(name=self.name_stg, key=f"fts_status_{symbol}")
                await self.cancel_orders(symbol, conn)
                log.info(f"关闭策略: {symbol}")
            elif todo == "warning":
                db.connect(reuse_if_open=True)
                OrmMarket.update.toCoinsTb.one(exchange=self.exchange, coin={"symbol": symbol, "isUsing": False})
                data = OrmMarket.search.fromCoinsTb.all4redis(exchange=self.exchange)
                if data:
                    await conn.hSet(name=f"{self.exchange.upper()}-DB", key=f"{self.exchange.lower()}_db", value=data)
                await MyAioSubprocess(cmd=self.stop_cmd.format(symbol=symbol))
                db.close()
            else:  # restart
                status = await MyAioSubprocess(cmd="sudo supervisorctl status ZFT_STG:" + symbol + "|awk '{print $2}'")
                if status != "STOPPED":
                    await MyAioSubprocess(cmd=self.restart_cmd.format(symbol=symbol))
                log.info(f"重启策略: {symbol}")
            await conn.close()
            del item, symbol, conn
            if todo == "stop":
                continue
            await sleep(4)

    async def monitor(self):
        while True:
            await self.get_data_from_redis()
            status = await self.get_stg_status()
            conn = await self.redis_pool.open(conn=True)
            for symbol, item in self.db_data.items():
                if item["isUsing"]:
                    if status.get(symbol, None) in ["RUNNING", "STARTING"]:
                        continue
                    await conn.hSet(name=self.name_stg, key=f"fts_status_{symbol}", value={"status": "starting"})
                    await self.todo.put({"todo": "start", "symbol": symbol})
                else:
                    if status.get(symbol, None) == "STOPPED":
                        await conn.hDel(name=self.name_stg, key=f"fts_status_{symbol}")
                        continue
                    await self.todo.put({"todo": "stop", "symbol": symbol})
            await self.upgrade_conf(current_status=status)
            await conn.close()
            del conn
            await sleep(1)

    def on_subscribe(self, data: dict):
        self.todo.put(ujson.loads(data["data"]))

    async def subscribe(self):
        conn = await self.redis_pool.open(conn=True)
        pub = await conn.subscribe(channel=f"{self.exchange.upper()}_STG_WS_DB")
        while True:
            item: list = await pub.parse_response(block=True)
            print(type(item), item)
            if item[0] != "message":
                continue
            await self.todo.put(ujson.loads(item[-1]))

    async def on_first(self):
        await self.init_by_exchange()
        await self.get_data_from_redis()

        if not os.path.exists(self.config_fp):
            with open(self.config_fp, "w"):
                pass

    def run(self):
        self.loop.run_sync(self.on_first)
        self.loop.add_callback(self.handle)
        self.loop.add_callback(self.monitor)
        self.loop.add_callback(self.subscribe)
        self.loop.start()


if __name__ == '__main__':
    MonitorSTG(exchange="lbk").run()
