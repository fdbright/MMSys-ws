# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/7 16:34

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import datetime
import pandas as pd
from sqlalchemy import create_engine
from tornado.httpclient import AsyncHTTPClient

from Utils import MyRedis, MyDatetime
from Models import LbkRestApi


class GetInfoFromLBK:

    def __init__(self):

        # mysql
        self.db = "mysql+pymysql://root:lbank369@127.0.0.1:3306/mm_sys?charset=utf8"

        # redis
        self.redis_pool = MyRedis(db=0)
        self.name = "LBK-DB"
        self.key = "lbk_price"

        # rest api
        self.api = LbkRestApi(htp_client=AsyncHTTPClient())

        # lbk
        self.lbk_coin_dict: dict = {}

        # symbol
        self.symbols: dict = {}

    def get_data_from_mysql(self):
        eg = create_engine(self.db)
        df = pd.read_sql("SELECT symbol, if1m FROM coins_lbk;", eg)
        self.symbols = df.to_dict(orient="records")

    async def get_price_from_lbk(self):
        data = await self.api.query_tick()
        # print(data)
        self.lbk_coin_dict = data["ticker"]
        self.set_redis()

    def set_redis(self):
        redis = self.redis_pool.open(conn=True)
        dt = MyDatetime.today()
        self.lbk_coin_dict["upgrade_time"] = MyDatetime.dt2ts(dt, thousand=True)
        self.lbk_coin_dict["upgrade_time_dt"] = MyDatetime.dt2str(dt)
        redis.hSet(name=self.name, key=self.key, value=self.lbk_coin_dict)
        redis.close()

    async def main(self):
        await self.get_price_from_lbk()
        self.set_redis()


if __name__ == '__main__':
    from tornado.ioloop import PeriodicCallback, IOLoop

    lbk = GetInfoFromLBK()
    lbk.main()
    PeriodicCallback(
        callback=lbk.main,
        callback_time=datetime.timedelta(seconds=5),
        jitter=0.2
    ).start()
    IOLoop.instance().start()
