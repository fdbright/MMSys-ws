# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/24 17:34

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from dataclasses import dataclass
from Utils import FreeDataclass, FrozenDataclass


@dataclass
class CoinsMonitor(FreeDataclass):

    symbol: str             # 币对
    bids: list              # 买盘
    asks: list              # 卖盘
    trades_his: dict        # 历史成交记录
    open_orders: dict       # 当前挂单
    account_info: dict      # 账户余额
    priceDistance: dict     # dexPrice|cexPrice|distance
    strategyStatus: str     # 策略状态


@dataclass
class MsgItem(FreeDataclass):

    action: str             # "close" | "subscribe" | "unsubscribe" ｜ "REST"
    token_id: str = None


@dataclass(frozen=True)
class ItemMethod(FrozenDataclass):
    GET: str = "GET"
    POST: str = "POST"
    PUT: str = "PUT"
    DELETE: str = "DELETE"


if __name__ == '__main__':
    pass
