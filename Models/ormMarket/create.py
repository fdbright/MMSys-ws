# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union, List

from Database import db, ABM, AccountModels, CBM, CoinModels

from Config import Configure
from Objects import AccountObj, CoinObj
from Utils.myEncoder import MyEncoder
from Utils import ExDecorator, MyDatetime


class ToAccountTb:

    @staticmethod
    def __initData(data: AccountObj) -> AccountObj:
        data.secretKey = MyEncoder.byDES(Configure.SECRET_KEY).encode(data.secretKey)
        return data

    @ExDecorator(event="新增账户")
    @db.atomic()
    def one(self, exchange: str, new_account: AccountObj) -> Union[int, bool]:
        model: ABM = AccountModels[exchange.lower()]
        uid = model.insert(
            self.__initData(new_account).to_dict()
        ).execute()
        return uid

    @ExDecorator(event="批量新增账户")
    @db.atomic()
    def batch(self, exchange: str, new_account: List[AccountObj]) -> Union[int, bool]:
        model: ABM = AccountModels[exchange.lower()]
        uid = model.insert_many(
            map(lambda x: self.__initData(x).to_dict(), new_account)
        ).execute()
        return uid


class ToCoinsTb:

    @staticmethod
    def __initData(data: CoinObj):
        data.team = data.team.lower()
        data.symbol = data.symbol.lower()
        data.createTime = data.updateTime = MyDatetime.today()
        return data

    @ExDecorator(event="新增币对")
    @db.atomic()
    def one(self, exchange: str, new_coin: CoinObj) -> Union[int, bool]:
        model: CBM = CoinModels[exchange.lower()]
        uid = model.insert(
            self.__initData(new_coin).to_dict()
        ).execute()
        return uid

    @ExDecorator(event="批量新增币对")
    @db.atomic()
    def batch(self, exchange: str, new_coin: List[CoinObj]) -> Union[int, bool]:
        model: CBM = CoinModels[exchange.lower()]
        uid = model.insert_many(
            map(lambda x: self.__initData(x).to_dict(), new_coin)
        ).execute()
        return uid


class Create:

    toCoinsTb = ToCoinsTb()
    toAccountTb = ToAccountTb()


if __name__ == '__main__':
    pass
