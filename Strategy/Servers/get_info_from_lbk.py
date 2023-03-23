# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/7 16:34

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List

import time
from datetime import timedelta
from aiohttp import ClientSession
from tornado.ioloop import PeriodicCallback, IOLoop

from Utils import MyAioredis, MyDatetime
from Objects import AccountObj
from Database import db
from Models import LbkRestApi, OrmMarket


class GetInfoFromLBK:

    def __init__(self):
        self.exchange: str = "lbk"

        # mysql
        self.db = "mysql+pymysql://root:lbank369@127.0.0.1:3306/mm_sys?charset=utf8"

        # redis
        self.redis_pool = MyAioredis(db=0)
        self.name = f"{self.exchange.upper()}-DB"

        # rest api
        self.api = None

        # lbk
        self.lbk_coin_dict: dict = {}

        # account
        self.accounts: List[AccountObj] = []

        # redis_data
        self.coin_data: dict = {}
        self.tick_data: dict = {}
        self.account_data: dict = {}
        self.account_info: dict = {}
        self.contract_data: dict = {}

        # loop
        self.loop = IOLoop.current()

    async def init_api(self):
        self.api = LbkRestApi(ClientSession(trust_env=True))

    async def get_info_from_mysql(self):
        db.connect(reuse_if_open=True)
        self.accounts = OrmMarket.search.fromAccountTb.all(exchange=self.exchange, decode=True)
        db.close()

    async def on_coin(self):
        db.connect(reuse_if_open=True)
        self.coin_data = OrmMarket.search.fromCoinsTb.all4redis(exchange=self.exchange)
        db.close()

    async def on_tick(self):
        data = await self.api.query_tick()
        self.tick_data = data["ticker"]

    async def on_tick2(self):
        while True:
            data = await self.api.query_tick()
            self.tick_data = data["ticker"]
            time.sleep(3)

    async def on_contract(self):
        data = await self.api.query_contract()
        self.contract_data = data["contract_dict"]

    async def on_account(self):
        await self.get_info_from_mysql()
        for account in self.accounts:
            self.account_data[account.account] = {}
            self.api.api_key = account.apiKey
            self.api.secret_key = account.secretKey
            data = await self.api.query_account_info()
            for val in data.get("account_lst", []):
                self.account_data[account.account][val["symbol"]] = val
            time.sleep(0.2)
        print(self.account_data)

    async def on_first(self):
        await self.init_api()
        await self.on_coin()
        await self.on_tick()
        await self.on_account()
        await self.on_contract()

    async def set_redis(self):
        conn = await self.redis_pool.open(conn=True)
        dt = MyDatetime.today()
        upgrade_time = MyDatetime.dt2ts(dt, thousand=True)
        upgrade_time_dt = MyDatetime.dt2str(dt)

        if self.coin_data:
            self.coin_data["upgrade_time"] = upgrade_time
            self.coin_data["upgrade_time_dt"] = upgrade_time_dt
            await conn.hSet(name=self.name, key="lbk_db", value=self.coin_data)
            self.coin_data = {}

        if self.tick_data:
            self.tick_data["upgrade_time"] = upgrade_time
            self.tick_data["upgrade_time_dt"] = upgrade_time_dt
            await conn.hSet(name=self.name, key="lbk_price", value=self.tick_data)
            self.tick_data = {}

        if self.contract_data:
            self.contract_data["upgrade_time"] = upgrade_time
            self.contract_data["upgrade_time_dt"] = upgrade_time_dt
            await conn.hSet(name=self.name, key="contract_data", value=self.contract_data)
            self.contract_data = {}

        if self.account_data:
            self.account_data["upgrade_time"] = upgrade_time
            self.account_data["upgrade_time_dt"] = upgrade_time_dt
            await conn.hSet(name=self.name, key="account_data", value=self.account_data)

        await conn.close()

    def main(self):
        self.loop.run_sync(self.on_first)
        PeriodicCallback(callback=self.set_redis, callback_time=timedelta(seconds=5), jitter=0.2).start()
        PeriodicCallback(callback=self.on_coin, callback_time=timedelta(hours=1), jitter=0.2).start()
        PeriodicCallback(callback=self.on_tick, callback_time=timedelta(seconds=5), jitter=0.2).start()
        PeriodicCallback(callback=self.on_account, callback_time=timedelta(minutes=5), jitter=0.2).start()
        PeriodicCallback(callback=self.on_contract, callback_time=timedelta(hours=1), jitter=0.2).start()
        self.loop.start()


if __name__ == '__main__':
    GetInfoFromLBK().main()
