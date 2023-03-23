# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/21 12:42

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
from Utils import MyAioredis, MyAioSubprocess, MyDatetime
from Utils.myEncoder import MyEncoder
from Models import LbkRestApi


class MonitorSTG:

    def __init__(self, exchange: str, server: str = "main"):

        self.exchange = exchange.lower()
        self.server = server
        self.default_server: str = "main"

        # loop
        self.loop = IOLoop.current()

        self.update_cmd: str = "sudo supervisorctl update"
        self.restart_cmd: str = "sudo supervisorctl restart ZFT_STG:{symbol}"
        self.start_cmd: str = "sudo supervisorctl start ZFT_STG:{symbol}"
        self.stop_cmd: str = "sudo supervisorctl stop ZFT_STG:{symbol}"

        self.running_cmd = "sudo supervisorctl status ZFT_STG:* |grep RUNNING|awk '{print $1}'"
        self.count_running_cmd = "sudo supervisorctl status ZFT_STG:* |grep RUNNING| wc -l"
        self.count_stopped_cmd = "sudo supervisorctl status ZFT_STG:* |grep STOPPED| wc -l"
        self.count_all_cmd = "sudo supervisorctl status ZFT_STG:* | wc -l"
        self.symbol_all_cmd = "sudo supervisorctl status ZFT_STG:* |awk '{print $1}'"

        self.path: str = "/etc/supervisor/conf.d/FT_STG.conf"
        self.title: str = "[group:ZFT_STG]\n" \
                          "programs="
        self.model: str = "[program:{symbol}]\n" \
                          "directory=/home/ec2-user/MMSys-ws/Strategy\n" \
                          "command=/home/ec2-user/anaconda3/envs/lbk-tornado/bin/python followTickTemplate.py --symbol={symbol} --server=main\n" \
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
                          "stdout_logfile_backups = 20\n"

        self.api = None
        self.todo = Queue()

        # mysql
        self.db_data: dict = {}

        # redis this
        self.redis_pool_this = MyAioredis(0)
        self.name: str = f"{self.exchange.upper()}-DB"
        self.name_stg: str = f"{self.exchange.upper()}-STG-DB"
        self.stg_count: int = 0
        self.channel = Configure.REDIS.stg_ws_channel.format(exchange=self.exchange.upper(), server=self.server)

        # ssh
        self.ssh: SSHTunnelForwarder = self.ssh4redis()
        if self.server != self.default_server:
            self.ssh.start()
            # redis that
            self.redis_pool_that = MyAioredis(0)

        self.fp = os.path.join(Configure.LOG_PATH, "stg_action.log")
        log.add(self.fp, retention="2 days", encoding="utf-8")

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

    async def init_by_exchange(self):
        if self.exchange == "lbk":
            self.api = LbkRestApi(ClientSession(trust_env=True))
        else:
            pass

    async def get_info_from_redis(self):
        conn = await self.redis_pool_this.open(conn=True)
        self.db_data = await conn.hGet(name=self.name, key=f"{self.exchange}_db")
        self.db_data.pop("upgrade_time", None)
        self.db_data.pop("upgrade_time_dt", None)
        await conn.close()
        del conn

    async def cal_stg_count(self):
        conn = await self.redis_pool_this.open(conn=True)
        self.stg_count = await MyAioSubprocess(self.count_running_cmd)
        await conn.hSet(name=self.name_stg, key=f"stg_count_{self.server}", value={"count": int(self.stg_count)})
        await conn.close()
        del conn

    async def check_symbols(self):
        await self.get_info_from_redis()
        data = await MyAioSubprocess(self.symbol_all_cmd)
        using_symbol = [v[8:] for v in data.split("\n")]
        sign = False
        for symbol in self.db_data.keys():
            if symbol not in using_symbol:
                sign = True
                break
        if sign:
            title: list = []
            model: str = ""
            for symbol, conf in self.db_data.items():
                title.append(symbol)
                model += "\n" + self.model.format(symbol=symbol)
            title: str = self.title + ",".join(title)
            res = title + "\n" + model
            with open(self.path, "w") as f:
                f.write(res)
            await MyAioSubprocess(self.update_cmd)

    async def get_running_stg(self) -> list:
        data = await MyAioSubprocess(self.running_cmd)
        if data == "":
            return []
        return [v[8:] for v in data.split("\n")]

    async def check_if_stop(self):
        conn = await self.redis_pool_this.open(conn=True)
        symbols = await self.get_running_stg()
        for symbol in symbols:
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
        del conn, symbols

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
            # log.info(f"{type(item)}, {item}")
            symbol: str = item["symbol"]
            conn = await self.redis_pool_this.open(conn=True)
            todo = item["todo"]
            if todo == "start":
                if self.server != self.default_server:
                    await sleep(2)
                await conn.hSet(name=self.name_stg, key=f"fts_status_{symbol}", value={"status": "starting"})
                await MyAioSubprocess(self.start_cmd.format(symbol=symbol))
                log.info(f"启动策略: {symbol}")
            elif todo == "stop":
                await MyAioSubprocess(self.stop_cmd.format(symbol=symbol))
                await conn.hDel(name=self.name_stg, key=f"fts_status_{symbol}")
                await self.cancel_orders(symbol, conn)
                log.info(f"关闭策略: {symbol}")
            else:
                status = await MyAioSubprocess(cmd="sudo supervisorctl status ZFT_STG:" + symbol + "|awk '{print $2}'")
                if status == "STOPPED":
                    continue
                await MyAioSubprocess(self.restart_cmd.format(symbol=symbol))
                log.info(f"重启策略: {symbol}")
            await conn.close()
            del item, symbol, conn, todo

    async def get_order_ids(self, conn, symbol) -> list:
        data = await conn.hGet(name=self.name_stg, key=f"order_ids_{symbol}")
        return data.get("orderIds", [])

    async def cancel_orders(self, symbol: str, conn):
        conf = self.db_data[symbol]
        self.api.api_key = conf["apiKey"]
        self.api.secret_key = MyEncoder.byDES(Configure.SECRET_KEY).decode(conf["secretKey"])
        order_ids = await self.get_order_ids(conn, symbol=symbol)
        for order_id in order_ids:
            await self.api.cancel_order(symbol=symbol, order_id=order_id)
        await conn.hDel(name=self.name_stg, key=f"order_ids_{symbol}")
        log.info(f"策略撤单: {symbol}")
        del conf, order_ids

    def run(self):
        log.info(f"启动策略监控 {MyDatetime.dt2str(MyDatetime.add8hr())}")
        self.loop.run_sync(self.init_by_exchange)
        self.loop.run_sync(self.get_info_from_redis)
        self.loop.run_sync(self.check_if_stop)
        self.loop.run_sync(self.check_symbols)

        if self.server != self.default_server:
            PeriodicCallback(callback=self.clone_redis, callback_time=timedelta(seconds=1), jitter=0.2).start()

        PeriodicCallback(callback=self.check_if_stop, callback_time=timedelta(minutes=5), jitter=0.2).start()
        PeriodicCallback(callback=self.check_symbols, callback_time=timedelta(seconds=30), jitter=0.2).start()
        PeriodicCallback(callback=self.get_info_from_redis, callback_time=timedelta(minutes=1), jitter=0.2).start()
        PeriodicCallback(callback=self.cal_stg_count, callback_time=timedelta(seconds=1), jitter=0.2).start()
        self.loop.add_callback(self.route)
        self.loop.add_callback(self.sub2redis)

        self.loop.start()


if __name__ == '__main__':
    MonitorSTG(exchange="lbk", server="main").run()
