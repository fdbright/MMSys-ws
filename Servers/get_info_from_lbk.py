# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/7 16:34

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List

import os
import schedule
import pandas as pd
from aiohttp import ClientSession
from tornado.gen import sleep
from tornado.ioloop import IOLoop

from Config import Configure
from Utils import MyAioredis, MyDatetime, MyAioSubprocess
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
        self.last_coin_data: dict = {}
        self.this_coin_data: dict = {}
        self.tick_data: dict = {}
        self.account_data: dict = {}
        self.account_info: dict = {}
        self.contract_data: dict = {}

        # loop
        self.loop = IOLoop.current()
        self.first_time: bool = True

        self.save_path = "/home/ec2-user/MMSys-ws/Servers/price_data.csv"

    @staticmethod
    def add_time(val: dict) -> dict:
        dt = MyDatetime.today()
        val["upgrade_time"] = MyDatetime.dt2ts(dt, thousand=True)
        val["upgrade_time_dt"] = MyDatetime.dt2str(dt)
        return val

    async def init_api(self):
        self.api = LbkRestApi(ClientSession(trust_env=True))

    async def get_info_from_mysql(self):
        db.connect(reuse_if_open=True)
        self.accounts = OrmMarket.search.fromAccountTb.all(exchange=self.exchange, decode=True)
        db.close()

    async def on_coin(self):
        conn = await self.redis_pool.open(conn=True)
        db.connect(reuse_if_open=True)
        try:
            self.this_coin_data: dict = OrmMarket.search.fromCoinsTb.all4redis(exchange=self.exchange)
            if not self.first_time:
                if self.this_coin_data != self.last_coin_data:
                    await self.on_contract()
            else:
                self.first_time = False
            self.last_coin_data = self.this_coin_data
            await conn.hSet(name=self.name, key="lbk_db", value=self.add_time(self.this_coin_data))
        except Exception as e:
            log.warning(f"coin, err: {e}")
        else:
            self.this_coin_data = {}
            log.info("on_coin")
        finally:
            db.close()
            await conn.close()
            del conn

    async def on_tick(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            data = await self.api.query_tick()
            self.tick_data = data["ticker"]
            await conn.hSet(name=self.name, key="lbk_price", value=self.add_time(self.tick_data))
        except Exception as e:
            log.warning(f"tick, err: {e}")
        else:
            del data
            self.tick_data = {}
            log.info("on_tick")
        finally:
            await conn.close()
            del conn

    async def on_contract(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            data = await self.api.query_contract()
            self.contract_data = data["contract_dict"]
            await conn.hSet(name=self.name, key="contract_data", value=self.add_time(self.contract_data))
        except Exception as e:
            log.warning(f"contract, err: {e}")
        else:
            del data
            self.contract_data = {}
            log.info("on_contract")
        finally:
            await conn.close()
            del conn

    async def on_account(self):
        while True:
            conn = await self.redis_pool.open(conn=True)
            await self.get_info_from_mysql()
            try:
                for account in self.accounts:
                    try:
                        self.account_data[account.account] = {}
                        self.api.api_key = account.apiKey
                        self.api.secret_key = account.secretKey
                        data = await self.api.query_account_info()
                        for val in data.get("account_lst", []):
                            self.account_data[account.account][val["symbol"]] = val
                    except Exception as e:
                        log.warning(f"account: {account}, err: {e}")
                    else:
                        del data
                    finally:
                        await sleep(0.2)
            except Exception as e:
                log.warning(f"account, err: {e}")
            else:
                log.info("on_account")
            finally:
                await conn.close()
                del conn
            await sleep(5)

    async def set_redis(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            pass
        except Exception as e:
            log.warning(f"set_redis, err: {e}")
        else:
            pass
        finally:
            await conn.close()
            del conn

    async def save_account(self, hour: str):
        conn = await self.redis_pool.open(conn=True)
        try:
            await conn.hSet(name=self.name, key=f"account_data_{hour}", value=self.add_time(self.account_data))
        except Exception as e:
            log.warning(f"save_account, err: {e}")
        else:
            log.info(f"save_account: {hour}")
        finally:
            await conn.close()
            del conn

    async def send_mail(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            if os.path.exists(self.save_path):
                os.remove(self.save_path)
            data = await conn.hGet(name=self.name, key="lbk_price")
            df = pd.DataFrame([{"symbol": k, "price": v} for k, v in data.items()])
            df.to_csv(self.save_path)
            # print(df)
            msg = {
                "receivers": ["erzhong.qi@lbk.one"],
                # "receivers": ["hai.shi@Lbk.one"],
                "title": "每日推送",
                "content": "",
                "filename": "price_data",
                "filepath": self.save_path
            }
            await conn.publish(channel=Configure.REDIS.send_mail_channel, msg=msg)
        except Exception as e:
            log.warning(f"send_mail, err: {e}")
        else:
            del data, df, msg
            log.info("send_mail")
        finally:
            await conn.close()
            del conn

    async def on_first(self):
        await self.init_api()
        await self.on_coin()
        await self.on_tick()
        await self.on_contract()

    async def on_timer(self):
        schedule.every(interval=2).minutes.do(lambda: self.loop.add_callback(self.on_coin))
        schedule.every(interval=5).seconds.do(lambda: self.loop.add_callback(self.on_tick))
        schedule.every(interval=5).seconds.do(lambda: self.loop.add_callback(self.set_redis))
        schedule.every(interval=30).minutes.do(lambda: self.loop.add_callback(self.on_contract))

        # +8hour
        schedule.every().days.at("17:00").do(lambda: self.loop.add_callback(lambda: self.save_account(hour="01")))
        schedule.every().days.at("01:00").do(lambda: self.loop.add_callback(lambda: self.save_account(hour="09")))
        schedule.every().days.at("09:00").do(lambda: self.loop.add_callback(lambda: self.save_account(hour="17")))

        schedule.every().days.at("03:20").do(lambda: self.loop.add_callback(self.send_mail))
        while True:
            schedule.run_pending()
            await sleep(1)

    def run(self):
        self.loop.run_sync(self.on_first)
        self.loop.add_callback(self.on_timer)
        self.loop.add_callback(self.on_account)
        self.loop.start()


if __name__ == '__main__':
    GetInfoFromLBK().run()
