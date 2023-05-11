# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023.05.03 19:43

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List

import schedule
from ujson import loads
from random import randint
from tornado.gen import sleep
from tornado.ioloop import IOLoop
from aiohttp import ClientSession, ClientResponse

from Config import get_header
from Utils import MyAioredisV2, MyDatetime
from Database import db
from Models import OrmMarket
from Objects import CoinObj


class DexSpider:

    def __init__(self):
        super().__init__()

        self.loop = IOLoop.current()

        self.redis_pool = MyAioredisV2(db=0)
        self.name = "DEX-DB"
        self.key = "dex_price"

        self.session = None

        self.url = "https://www.dextools.io/shared/search/pair?query=all"
        self.url = "https://www.dextools.io/shared/analytics/pairs?limit=51&interval=24h&page=1&chain=fantom"

        self.headers_length: int = 17

        self.coins: List[CoinObj] = []
        self.dex_price: dict = {}
        self.sign: bool = False

    def get_data_from_mysql(self):
        db.connect(reuse_if_open=True)
        self.coins = OrmMarket.search.fromCoinsTb.all(exchange="lbk", to_dict=False)
        db.close()

    async def get_response(self, url: str) -> dict:
        cr: ClientResponse = await self.session.get(
            url=url,
            headers=get_header(index=randint(0, 16)),
            # proxy="http://127.0.0.1:7890",
        )
        try:
            resp: str = await cr.text()
            try:
                resp: dict = loads(resp)
            except TypeError:
                resp: dict = {}
        except Exception as e:
            log.error(f"请求失败, url: {cr.url}, err: {e}")
            resp: dict = {}
        res: dict = {}
        for val in resp.get("results", [{}]):
            token = val.get("id", {}).get("token", "")
            if not token:
                continue
            dex_price = {
                "symbol": val.get("symbol", ""),
                "type": val.get("symbolRef", ""),
                "liquidity": val.get("metrics", {}).get("liquidity", -1),
                "price": float(val.get("price", -1) or -1)
            }
            if token in res.keys():
                res[token].append(dex_price)
            else:
                res[token] = [dex_price]
        return res

    async def polling(self):
        """轮询"""
        while True:
            self.get_data_from_mysql()
            conn = await self.redis_pool.open()
            resp = await self.get_response(url=self.url)
            print(len(resp))
            print(resp)
            for index, coin in enumerate(self.coins):
                try:
                    if coin.f_coin_addr in ["主网代币", "合约升级中"]:
                        self.dex_price[coin.symbol] = {"type": coin.f_coin_addr, "price": -1}
                        continue
                    dex_price = resp.get(coin.f_coin_addr, None)
                    self.dex_price[coin.symbol] = dex_price
                    await conn.hset(name=self.name, key=coin.symbol, value=dex_price)
                except Exception as e:
                    log.warning(f"异常, symbol: {coin.symbol}, addr: {coin.f_coin_addr}, err: {e}")
                else:
                    log.info(f"symbol: {coin.symbol}, dex_price: {dex_price}, addr: {coin.f_coin_addr}")
                # finally:
                #     await sleep(3)
            await conn.close()
            del conn
            self.sign = True
            # await sleep(2)
            exit()

    async def set_redis(self):
        conn = await self.redis_pool.open()
        dt = MyDatetime.today()
        if self.sign:
            self.dex_price["upgrade_time"] = MyDatetime.dt2ts(dt, thousand=True)
            self.dex_price["upgrade_time_dt"] = MyDatetime.dt2str(dt)
            await conn.hset(name=self.name, key=self.key, value=self.dex_price)
        await conn.close()
        del conn, dt

    async def on_first(self):
        self.session = ClientSession(trust_env=True)
        self.get_data_from_mysql()

    async def on_timer(self):
        pass
        # schedule.every(interval=10).seconds.do(lambda: self.loop.add_callback(self.set_redis))
        # while True:
        #     schedule.run_pending()
        #     await sleep(1)

    def run(self):
        self.loop.run_sync(self.on_first)
        self.loop.add_callback(self.polling)
        self.loop.add_callback(self.on_timer)
        self.loop.start()


if __name__ == '__main__':
    DexSpider().run()
