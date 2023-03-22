# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 16:32

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from tornado.options import options

from Database import db
# from Utils import MyAioRedisFunction
from Objects import ItemMethod, UserObj, OperateObj
from Models import OrmUser, OrmMarket
from Models import LbkRestApi


class MyActionTemplate:

    def __init__(self, after_request, current_user: UserObj = None):

        self.redis_pool = options.redis_pool
        self.redis_conn = None
        self.current_user = current_user
        self.after_request = after_request

    async def do_job(self, obj, item):
        self.redis_conn = await self.redis_pool.open(conn=True)
        item = obj(**item)
        db.connect(reuse_if_open=True)
        if item.method == ItemMethod.GET:
            await self.get(item)
        elif item.method == ItemMethod.POST:
            await self.post(item)
        elif item.method == ItemMethod.PUT:
            await self.put(item)
        elif item.method == ItemMethod.DELETE:
            await self.delete(item)
        else:
            pass
        db.close()
        await self.redis_conn.close()

    def get_rest_api_by_exchange(self, exchange: str, symbol: str):
        info: dict = OrmMarket.search.fromCoinsTb.forOrder(exchange, symbol, decode=True)
        # log.info(info)
        if exchange == "lbk":
            return LbkRestApi(self.current_user.http_client, info["apiKey"], info["secretKey"])
        else:
            return None

    @staticmethod
    def add_operation(operation: OperateObj):
        OrmUser.create.toOperateTb.one(operation)

    async def get(self, item):
        pass

    async def post(self, item):
        pass

    async def put(self, item):
        pass

    async def delete(self, item):
        pass


if __name__ == '__main__':
    pass
