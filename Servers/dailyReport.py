# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/27 21:58
# 定时发送日报

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List, Dict

import nest_asyncio
nest_asyncio.apply()

import os
import asyncio
import openpyxl
import datetime
from tornado.httpclient import AsyncHTTPClient

from Config import Configure
from Utils import MyRedis, MyEmail, MyDatetime
from Database import db
from Models import LbkRestApi, OrmMarket
from Objects import AccountObj


class DailyReport:

    def __init__(self, exchange: str):
        self.exchange = exchange.upper()

        self.tempFile = Configure.DAILY_REPORT_PATH         # 模板文件
        self.template = Configure.TEMPLATE_PATH             # 模板路径
        self.saveFile = "表单更新{}.xlsx"                    # 待发送文件

        self.sk: str = Configure.SECRET_KEY

        # redis
        self.redis_pool = MyRedis(db=0)

        self.api = LbkRestApi(htp_client=AsyncHTTPClient())

        self.accounts: List[AccountObj] = []
        self.accounts_data: Dict[str, dict] = {}
        
        # dex_price
        self.cmc_price: dict = {}
        self.pancake_price: dict = {}

        self.me = MyEmail(Configure.EMAIL.host, Configure.EMAIL.user, Configure.EMAIL.password)
        self.receivers: list = ["hai.shi@Lbk.one"]
        # self.receivers: list = [
        #     "junxiang@lbk.one", "zhiwei.chen@lbk.one", "rujie.wei@lbk.one", "chao.lu@lbk.one", "bingui.qin@lbk.one"
        # ]

        self.account_dict: dict = {}

    def get_data_from_redis(self):
        redis = self.redis_pool.open(conn=True)
        self.cmc_price = redis.hGet(name="CMC-DB", key="cmc_price")
        redis.close()

    def get_data_from_mysql(self):
        db.connect(reuse_if_open=True)
        self.accounts = OrmMarket.search.fromAccountTb.byTeam(exchange=self.exchange, team="jx", decode=True)
        db.close()

    async def get_account_data(self):
        log.info("查询账户余额 开始")
        for account in self.accounts:
            self.api.api_key = account.apiKey
            self.api.secret_key = account.secretKey
            data = await self.api.query_account_info()
            # print(account.account, data)
            for row in data.get("account_lst", []):
                if account.account not in self.accounts_data.keys():
                    self.accounts_data[account.account] = {}
                symbol = row.pop("symbol")
                self.accounts_data[account.account][symbol] = row
        log.info("查询账户余额 结束")

    def write2excel(self, fp: str):
        wb = openpyxl.load_workbook(filename=self.tempFile, read_only=False)
        ws = wb["Sheet1"]
        rows = ws.rows
        temp, to_write = {}, {}
        # print(self.accounts_data)
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
                to_write[f"D{index}"] = float(self.accounts_data.get(account, {}).get(pair.upper(), {}).get("balance", 0))
                to_write[f"G{index}"] = dp if dp != -1 else 0
            except Exception as e:
                log.warning(f"excel 异常: {e}")
        # print(to_write)
        for k, v in to_write.items():
            ws[k] = v
        wb.save(fp)
        wb.close()
        log.info(f"写入日报: {fp}")

    def send_excel(self, fp: str, fn: str):
        self.me.init_msg(self.receivers, sub_title="账户余额情况推送")
        self.me.add_file(filepath=fp, filename=fn)
        self.me.send_mail()

    async def main(self):
        log.info("start")
        fn = self.saveFile.format(MyDatetime.add8hr().strftime("%Y-%m-%d %H:%M"))
        fp = os.path.join(self.template, fn)
        self.get_data_from_redis()
        self.get_data_from_mysql()
        await self.get_account_data()
        self.write2excel(fp=fp)
        self.send_excel(fp=fp, fn=fn)
        os.remove(fp)
        self.accounts_data = {}
        log.info("finish")


if __name__ == '__main__':
    from tornado.ioloop import PeriodicCallback, IOLoop

    dt = datetime.timedelta(minutes=30)
    dr = DailyReport(exchange="lbk")

    # """
    while True:
        now = datetime.datetime.now()
        if now.minute in [00, 30]:
            break
    # """

    asyncio.run(dr.main())
    PeriodicCallback(
        callback=dr.main,
        callback_time=dt,
        jitter=0.2
    ).start()
    IOLoop.instance().start()
