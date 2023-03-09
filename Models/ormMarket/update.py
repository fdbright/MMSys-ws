# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from Database import db, ABM, AccountModels, CBM, CoinModels

from Config import Configure
from Utils.myEncoder import MyEncoder
from Utils import ExDecorator, MyDatetime


class ToAccountTb:

    @ExDecorator(event="更新账户")
    @db.atomic()
    def one(self, exchange: str, account: dict) -> bool:
        account_name: str = account.pop("account")
        sk = account.get("secretKey", None)
        if sk:
            account["secretKey"] = MyEncoder.byDES(Configure.SECRET_KEY).encode(sk)
        model: ABM = AccountModels[exchange.lower()]
        model.update(
            account
        ).where(
            model.account == account_name
        ).execute()
        return True


class ToCoinsTb:

    @ExDecorator(event="更新币对")
    @db.atomic()
    def one(self, exchange: str, coin: dict) -> bool:
        symbol = coin.pop("symbol")
        coin["updateTime"] = MyDatetime.today()
        model: CBM = CoinModels[exchange.lower()]
        model.update(
            coin
        ).where(
            model.symbol == symbol.lower()
        ).execute()
        return True


class Update:

    toCoinsTb = ToCoinsTb()
    toAccountTb = ToAccountTb()


if __name__ == '__main__':
    pass
