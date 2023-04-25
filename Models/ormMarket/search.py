# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import List, Union

from Database import ABM, AccountModels, CBM, CoinModels

from Config import Configure

from Objects import CoinObj, AccountObj
from Utils.myEncoder import MyEncoder
from Utils import ExDecorator, MyDatetime


class FromAccountTb:

    @staticmethod
    def __initData(data: dict, decode: bool = False, to_dict: bool = False) -> Union[dict, AccountObj]:
        data.pop("id")
        if decode:
            data["secretKey"] = MyEncoder.byDES(Configure.SECRET_KEY).decode(data["secretKey"])
        if to_dict:
            return data
        else:
            return AccountObj(**data)

    @ExDecorator(event="查找账户")
    def one(self, exchange: str, account: str, decode: bool = False, to_dict: bool = False) -> Union[dict, AccountObj]:
        model: ABM = AccountModels[exchange.lower()]
        query = model.select().where(
            model.account == account
        ).dicts().get()
        return self.__initData(query, decode, to_dict)

    @ExDecorator(event="查找所有账户")
    def all(self, exchange: str, decode: bool = False, to_dict: bool = False) -> List[Union[dict, AccountObj]]:
        model: ABM = AccountModels[exchange.lower()]
        query = model.select().order_by(
            model.account.asc()
        ).dicts().iterator()
        return list(map(lambda x: self.__initData(x, decode, to_dict), query))

    @ExDecorator(event="根据组别查找账户")
    def byTeam(self, exchange: str, team: str, decode: bool = False, to_dict: bool = False) -> list:
        model: ABM = AccountModels[exchange.lower()]
        query = model.select().where(
            model.team == team.lower()
        ).order_by(
            model.account.asc()
        ).dicts().iterator()
        return list(map(lambda x: self.__initData(x, decode, to_dict), query))


class FromCoinsTb:

    @staticmethod
    def __initData(data: dict, to_dict: bool = False) -> Union[dict, CoinObj]:
        data.pop("id")
        data["createTime"] = MyDatetime.dt2str(data["createTime"])
        data["updateTime"] = MyDatetime.dt2str(data["updateTime"])
        if to_dict:
            return data
        else:
            return CoinObj(**data)

    @ExDecorator(event="查找币对")
    def one(self, exchange: str, symbol: str, to_dict: bool = False) -> Union[dict, CoinObj]:
        model: CBM = CoinModels[exchange.lower()]
        query = model.select().where(
            model.symbol == symbol.lower()
        ).dicts().get()
        return self.__initData(query, to_dict)

    @ExDecorator(event="查找所有币对")
    def all(self, exchange: str, to_dict: bool = False) -> List[Union[dict, CoinObj]]:
        model: CBM = CoinModels[exchange.lower()]
        query = model.select().order_by(
            model.symbol.asc()
        ).dicts().iterator()
        return list(map(lambda x: self.__initData(x, to_dict), query))

    @ExDecorator(event="根据组别查找币对")
    def byTeam(self, exchange: str, team: str, to_dict: bool = False) -> List[Union[dict, CoinObj]]:
        model: CBM = CoinModels[exchange.lower()]
        query = model.select().where(
            model.team == team.lower()
        ).order_by(
            model.symbol.asc()
        ).dicts().iterator()
        return list(map(lambda x: self.__initData(x, to_dict), query))

    @ExDecorator(event="查询订单相关字段")
    def forOrder(self, exchange: str, symbol: str, decode: bool = False) -> dict:
        ac_model: ABM = AccountModels[exchange.lower()]
        co_model: CBM = CoinModels[exchange.lower()]
        query = co_model.select(
            ac_model.apiKey, ac_model.secretKey, ac_model.account
        ).join(
            ac_model, on=(co_model.account == ac_model.account)
        ).where(
            co_model.symbol == symbol.lower()
        ).dicts().get()
        if decode:
            query["secretKey"] = MyEncoder.byDES(Configure.SECRET_KEY).decode(query["secretKey"])
        return query

    @ExDecorator(event="查询策略相关字段")
    def forStg(self, exchange: str, symbol: str, decode: bool = False) -> dict:
        ac_model: ABM = AccountModels[exchange.lower()]
        co_model: CBM = CoinModels[exchange.lower()]
        query = co_model.select(
            ac_model.apiKey, ac_model.secretKey, ac_model.account, ac_model.team, co_model.isUsing,
            co_model.profit_rate, co_model.step_gap, co_model.order_amount, co_model.order_nums
        ).join(
            ac_model, on=(co_model.account == ac_model.account)
        ).where(
            co_model.symbol == symbol.lower()
        ).dicts().get()
        if decode:
            query["secretKey"] = MyEncoder.byDES(Configure.SECRET_KEY).decode(query["secretKey"])
        return query

    @ExDecorator(event="查询所有数据")
    def all4redis(self, exchange: str) -> dict:
        ac_model: ABM = AccountModels[exchange.lower()]
        co_model: CBM = CoinModels[exchange.lower()]
        query = co_model.select(
            ac_model.apiKey, ac_model.secretKey, ac_model.account, ac_model.team,
            co_model.symbol, co_model.isUsing,
            co_model.profit_rate, co_model.step_gap, co_model.order_amount, co_model.order_nums,
        ).join(
            ac_model, on=(co_model.account == ac_model.account)
        ).dicts().iterator()
        return {row["symbol"]: row for row in query}


class Search:

    fromCoinsTb = FromCoinsTb()
    fromAccountTb = FromAccountTb()


if __name__ == '__main__':
    pass
