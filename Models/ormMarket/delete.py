# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import List

from Database import db, ABM, AccountModels, CBM, CoinModels

from Utils import ExDecorator


class FromAccountTb:

    @ExDecorator(event="删除账户")
    @db.atomic()
    def one(self, exchange: str, account: str) -> bool:
        model: ABM = AccountModels[exchange.lower()]
        model.delete().where(
            model.account == account
        ).execute()
        return True

    @ExDecorator(event="批量删除账户")
    @db.atomic()
    def batch(self, exchange: str, account: List[str]) -> bool:
        model: ABM = AccountModels[exchange.lower()]
        model.delete().where(
            model.account.in_(map(lambda x: x.lower, account))
        ).execute()
        return True

    @ExDecorator(event="删除全部账户")
    @db.atomic()
    def all(self, exchange: str) -> bool:
        model: ABM = AccountModels[exchange.lower()]
        model.drop_table()
        model.create_table()
        return True


class FromCoinsTb:

    @ExDecorator(event="删除币对")
    @db.atomic()
    def one(self, exchange: str, coin: str) -> bool:
        model: CBM = CoinModels[exchange.lower()]
        model.delete().where(
            model.symbol == coin.lower()
        ).execute()
        return True

    @ExDecorator(event="批量删除币对")
    @db.atomic()
    def batch(self, exchange: str, coin: List[str]) -> bool:
        model: CBM = CoinModels[exchange.lower()]
        model.delete().where(
            model.symbol.in_(map(lambda x: x.lower(), coin))
        ).execute()
        return True

    @ExDecorator(event="删除全部账户")
    @db.atomic()
    def all(self, exchange: str) -> bool:
        model: CBM = CoinModels[exchange.lower()]
        model.drop_table()
        model.create_table()
        return True


class Delete:

    fromCoinsTb = FromCoinsTb()
    fromAccountTb = FromAccountTb()


if __name__ == '__main__':
    pass
