# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/4/19 15:08

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List

import ujson
import schedule
import requests
import pandas as pd
from datetime import datetime, timedelta
from tornado.gen import sleep
from tornado.ioloop import IOLoop, PeriodicCallback

from Config import Configure
from Utils import MyAioredis
from Objects import AccountObj


class DailyReport:

    def __init__(self, exchange: str):
        self.exchange = exchange.upper()

        # loop
        self.loop = IOLoop().current()

        self.tempFile = Configure.DAILY_REPORT_PATH         # 模板文件

        self.sk: str = Configure.SECRET_KEY

        # redis
        self.redis_pool = MyAioredis(db=0)

        self.cex_price: dict = {}
        self.dex_price: dict = {}
        self.cmc_price: dict = {}

        self.account_data_last: dict = {}       # 期末余额
        self.account_data_init: dict = {}       # 期初余额

        # 班次映射
        self.work_time: dict = {
            "01": "17",
            "09": "01",
            "17": "09"
        }

        self.accounts: List[AccountObj] = []

        self.min_5_sec: int = 5 * 60
        self.st: float = 0

        self.hr01: str = ""
        self.hr09: str = ""
        self.hr17: str = ""

    @staticmethod
    def send_lark_msg(msg: dict):
        try:
            web_hock = "https://open.larksuite.com/open-apis/bot/v2/hook/8b856e46-29f3-401f-ba7d-ac3412dd39f9"
            header = {"Content-Type": "application/json"}
            data = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": msg
                    },
                }
            }
            res = requests.post(url=web_hock, headers=header, data=ujson.dumps(data))
            log.info(f"发送lark, 成功: {res.text}")
        except Exception as e:
            log.info(f"发送lark, 失败: {e}")

    async def get_data_from_redis(self):
        conn = await self.redis_pool.open(conn=True)
        self.cex_price = await conn.hGet(name="LBK-DB", key="lbk_price")
        self.cmc_price = await conn.hGet(name="CMC-DB", key="cmc_price")
        self.account_data_last = await conn.hGet(name="LBK-DB", key="account_data")
        await conn.close()
        del conn

    def get_data_from_excel(self):
        dt = pd.read_excel(self.tempFile).to_dict(orient="records")
        for index, row in enumerate(dt, 1):
            asset = row["资产"]
            balance = float(row["期初余额"])
            if index % 2 != 0:
                self.account_data_init[row["账户"]] = {
                    asset: balance
                }
            else:
                self.account_data_init[dt[index - 2]["账户"]][asset] = balance

    async def get_price_by_asset(self, conn, asset: str) -> float:
        symbol = f"{asset}_usdt".lower()
        value: dict = await conn.hGet(name="DEX-DB", key=symbol)
        price: float = float(value.get("price", -1))
        if price not in [0, -1]:
            return price
        price: float = float(self.cmc_price.get(symbol, {}).get(symbol, -1))
        if price not in [0, -1]:
            return price
        price: float = float(self.cex_price.get(symbol, -1))
        if price not in [0, -1]:
            return price
        return 0

    async def cal_exposure_offset_5min(self):
        """计算敞口偏移"""
        self.get_data_from_excel()
        msg: dict = {
            "title": f"5分钟敞口推送",
            "content": [],
        }
        content = []
        for account, value in self.account_data_init.items():
            l_coin: str = ""
            f_offset, l_offset = -1, -1
            for asset, balance in value.items():
                last_balance = float(self.account_data_last.get(account, {}).get(asset.upper(), {}).get("balance", -1))
                if asset.upper() == "USDT":
                    l_offset: float = last_balance - balance
                else:
                    l_coin = asset
            if not l_coin:
                continue
            if l_offset <= -100:
                content.append(
                    [
                        {
                            "tag": "text",
                            "text": l_coin.upper() + ": "
                        },
                        {
                            "tag": "a",
                            "text": str(round(l_offset, 2))
                        },
                    ]
                )
        if content:
            msg["content"] = sorted(content, key=lambda x: float(x[-1]["text"]), reverse=False)
        self.send_lark_msg(msg)
        del msg, content

    async def cal_exposure_offset_8hr(self):
        conn = await self.redis_pool.open(conn=True)
        current_hour: str = str((datetime.now() + timedelta(hours=8)).hour).zfill(2)
        msg: dict = {
            "title": f"班次推送: {current_hour}",
            "content": [[]],
        }
        account_data = await conn.hGet(name="LBK-DB", key=f"account_data_{self.work_time[current_hour]}")
        for account, value in sorted(account_data.items()):
            if account in ["upgrade_time", "upgrade_time_dt"]:
                continue
            l_coin: str = ""
            f_offset, l_offset = -1, -1
            for asset, balance in value.items():
                init_balance = float(balance.get("balance", -1))
                last_balance = float(self.account_data_last.get(account, {}).get(asset.upper(), {}).get("balance", -1))
                if asset.upper() == "USDT":
                    l_offset: float = last_balance - init_balance
                else:
                    l_coin = asset
                    price = await self.get_price_by_asset(conn, asset=asset)
                    f_offset: float = (last_balance - init_balance) * price
            offset: float = f_offset + l_offset
            if not l_coin:
                continue
            if len(msg["content"][-1]) < 10:
                msg["content"][-1].extend([
                    {
                        "tag": "text",
                        "text": l_coin.upper() + ": "
                    },
                    {
                        "tag": "a",
                        "text": str(round(offset, 2))
                    },
                    {
                        "tag": "text",
                        "text": "  |  "
                    }
                ])
            else:
                msg["content"].append([])
        self.send_lark_msg(msg)
        await conn.close()
        del conn, current_hour, msg, account_data

    def on_task_8hr(self):
        self.loop.add_callback(self.cal_exposure_offset_8hr)
    
    def on_task_5min(self):
        self.loop.add_callback(self.cal_exposure_offset_5min)

    async def on_timer(self):
        for minute in [str(i).zfill(2) for i in range(0, 60, 5)]:
            schedule.every().hours.at(f":{minute}").do(self.on_task_5min)
        schedule.every().day.at("01:00").do(self.on_task_8hr)
        schedule.every().day.at("09:00").do(self.on_task_8hr)
        schedule.every().day.at("17:00").do(self.on_task_8hr)
        while True:
            schedule.run_pending()
            await sleep(1)

    async def on_first(self):
        await self.get_data_from_redis()

    def run(self):
        self.loop.run_sync(self.on_first)
        self.loop.add_callback(self.on_timer)
        PeriodicCallback(self.get_data_from_redis, callback_time=timedelta(seconds=5), jitter=0.2).start()
        self.loop.start()


if __name__ == '__main__':
    DailyReport(exchange="lbk").run()
