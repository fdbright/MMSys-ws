# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/7 15:28

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import datetime
import pandas as pd
from requests import Session
from sqlalchemy import create_engine
from Utils import MyRedis, MyDatetime


class GetInfoFromCMC:

    def __init__(self):

        # mysql
        self.db = "mysql+pymysql://root:lbank369@127.0.0.1:3306/mm_sys?charset=utf8"

        # redis
        self.redis_pool = MyRedis(db=0)
        self.name = "CMC-DB"
        self.key = "cmc_price"
        self.channel = "CMC-WS-DB"

        # symbol
        self.symbols: dict = {}
        self.symbols_name: dict = {}

        # cmc
        self.path = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"

        self.headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": "bfc03c3f-a3ff-4463-9a6d-214dfbb59534",
        }
        self.params = {
            "symbol": "",
            "convert": "",
            "aux": "num_market_pairs",
            "skip_invalid": True,
        }
        self.cmc_coin_dict: dict = {}

        # resp
        self.session = Session()
        self.session.headers.update(self.headers)

    def get_data_from_mysql(self):
        result = {}
        eg = create_engine(self.db)
        df = pd.read_sql("SELECT symbol, f_coin, full_name, if1m FROM coins_lbk;", eg)
        df["if1m"] = df["if1m"].apply(lambda x: True if x == 1 else False)
        dt = df.to_dict(orient="records")
        symbols, symbols_name = [], {}
        for v in dt:
            symbol = v.pop("symbol")
            symbols.append(symbol)
            symbols_name[symbol] = v
        temp_dict = {}
        for v in symbols:
            pair, base = v.split("_")
            if base not in temp_dict.keys():
                temp_dict[base] = []
            temp_dict[base].append(symbols_name[v]["f_coin"])
        temp_list = []
        for k, pairs in temp_dict.items():
            # pairs.append(k)
            if k not in result.keys():
                result[k] = []
            for i, v in enumerate(pairs):
                if len(temp_list) < 120:
                    temp_list.append(v)
                else:
                    result[k].append(",".join(temp_list))
                    temp_list = []
            if temp_list:
                result[k].append(",".join(temp_list))
        self.symbols = result
        self.symbols_name = symbols_name

    @staticmethod
    def formatDt2ts(dt: str) -> int:
        return datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp() if dt else 0

    def get_resp(self, symbol, convert):
        self.params["symbol"] = symbol
        self.params["convert"] = convert
        return self.session.get(self.path, params=self.params).json()

    def get_cmc_price(self):
        # self.cmc_coin_dict = {}
        mid: dict = {}
        for k, pairs in self.symbols.items():
            for v in pairs:
                resp = self.get_resp(symbol=v, convert=k)
                # print(resp)
                data: dict = resp["data"]
                mid.update(data)
        for symbol, value in self.symbols_name.items():
            l_coin = symbol.split("_")[-1].upper()
            info = mid.get(value["f_coin"], [{}])
            if len(info) > 1:
                for ss in info:
                    if ss["name"] == value.get("full_name", ""):
                        info = [ss]
                        break
            if info:
                quote = info[0].get("quote", {}).get(l_coin, {})
            else:
                quote = {}
            price = quote.get("price", -1)
            if value.get("if1m", False):
                price = price * 1000000
            last_updated = self.formatDt2ts(quote.get("last_updated", None))
            self.cmc_coin_dict[symbol] = {
                "price": price,
                "last_updated": last_updated
            }
        self.cmc_coin_dict["usdt"] = {
            "price": 1,
            "last_updated": -1
        }

    def set_redis(self):
        redis = self.redis_pool.open(conn=True)
        all_data = {}
        for symbol, v in self.cmc_coin_dict.items():
            value = {
                "price": v["price"],
                "coinDepth": -1,
                "wbnbDepth": -1,
                "timestamp": v["last_updated"],
            }
            all_data[symbol] = value
            redis.hSet(name=self.name, key=symbol, value=value)
        dt = MyDatetime.today()
        all_data["upgrade_time"] = MyDatetime.dt2ts(dt, thousand=True)
        all_data["upgrade_time_dt"] = MyDatetime.dt2str(dt)
        redis.hSet(name=self.name, key=self.key, value=all_data)
        redis.close()

    def main(self):
        self.get_data_from_mysql()
        self.get_cmc_price()
        self.set_redis()


if __name__ == '__main__':
    from tornado.ioloop import PeriodicCallback, IOLoop

    cmc = GetInfoFromCMC()
    cmc.main()
    PeriodicCallback(
        callback=cmc.main,
        callback_time=datetime.timedelta(minutes=15),
        jitter=0.2
    ).start()
    IOLoop.instance().start()
