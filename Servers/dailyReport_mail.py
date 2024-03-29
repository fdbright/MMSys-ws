# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/27 21:58
# 定时发送日报

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List, Dict

import os
import schedule
import openpyxl
import datetime
from tornado.gen import sleep
from tornado.ioloop import IOLoop, PeriodicCallback

from Config import Configure
from Utils import MyAioredis, MyDatetime
from Objects import AccountObj


class DailyReport:

    def __init__(self, exchange: str):
        self.exchange = exchange.upper()

        # loop
        self.loop = IOLoop.current()

        self.tempFile = Configure.DAILY_REPORT_PATH         # 模板文件
        self.template = Configure.TEMPLATE_PATH             # 模板路径
        self.saveFile = "表单更新{}.xlsx"                    # 待发送文件

        self.sk: str = Configure.SECRET_KEY

        # redis
        self.redis_pool = MyAioredis(db=0)

        self.accounts: List[AccountObj] = []

        # dex_price
        self.cmc_price: dict = {}
        self.pancake_price: dict = {}

        # self.me = MyEmail(Configure.EMAIL.host, Configure.EMAIL.user, Configure.EMAIL.password)
        # self.receivers: list = ["hai.shi@Lbk.one"]
        self.receivers: list = [
            "junxiang@lbk.one", "zhiwei.chen@lbk.one", "rujie.wei@lbk.one", "chao.lu@lbk.one", "bingui.qin@lbk.one",
            "tianhua.lu@lbk.one", "pengfei.fan@lbk.one", "yue.li@lbk.one",
            # "hai.shi@Lbk.one"
        ]

        self.account_dict: Dict[str, dict] = {}

    async def get_data_from_redis(self):
        conn = await self.redis_pool.open(conn=True)
        self.cmc_price = await conn.hGet(name="CMC-DB", key="cmc_price")
        self.account_dict = await conn.hGet(name="LBK-DB", key="account_data")
        await conn.close()
        del conn

    def write2excel(self, fp: str):
        wb = openpyxl.load_workbook(filename=self.tempFile, read_only=False)
        ws = wb["Sheet1"]
        rows = ws.rows
        temp, to_write = {}, {}
        for index, row in enumerate(rows, 1):
            try:
                if index <= 1:
                    continue
                account = row[0].value if row[0].value else temp[index - 1]["account"]
                pair = row[1].value.lower()
                temp[index] = {
                    "account": account,
                    "pair": pair,
                }
                symbol = f"{pair}_usdt" if pair != "usdt" else "usdt"
                dp = float(self.cmc_price.get(symbol, {}).get("price", 0))
                to_write[f"D{index}"] = float(self.account_dict.get(account, {}).get(pair.upper(), {}).get("balance", 0))
                to_write[f"G{index}"] = dp if dp != -1 else 0
            except Exception as e:
                log.warning(f"excel 异常: {e}")
        # print(to_write)
        for k, v in to_write.items():
            ws[k] = v
        wb.save(fp)
        wb.close()
        log.info(f"写入日报: {fp}")

    async def task(self):
        log.info("start")
        conn = await self.redis_pool.open(conn=True)
        fn = self.saveFile.format(MyDatetime.add8hr().strftime("%Y-%m-%d %H:%M"))
        fp = os.path.join(self.template, fn)
        self.write2excel(fp=fp)
        await conn.publish(channel="SendEmail", msg={
            "receivers": self.receivers,
            "title": "账户余额情况推送",
            "content": "",
            "filename": fn,
            "filepath": fp,
            "delete": True
        })
        log.info("finish")

    def on_task(self):
        self.loop.add_callback(self.task)

    async def on_timer(self):
        schedule.every().hours.at(":00").do(self.on_task)
        schedule.every().hours.at(":30").do(self.on_task)
        while True:
            schedule.run_pending()
            await sleep(1)

    def run(self):
        self.loop.run_sync(self.get_data_from_redis)
        PeriodicCallback(self.get_data_from_redis, callback_time=datetime.timedelta(seconds=30)).start()
        self.loop.add_callback(self.on_timer)
        self.loop.start()


if __name__ == '__main__':
    DailyReport(exchange="lbk").run()
