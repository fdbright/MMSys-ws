# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/23 16:28

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from dataclasses import dataclass
from tornado.ioloop import PeriodicCallback

from Utils import FreeDataclass, FrozenDataclass


@dataclass
class Conf(FreeDataclass):
    apiKey: str = ""
    secretKey: str = ""
    account: str = ""
    team: str = ""
    symbol: str = ""
    isUsing: bool = False
    step_gap: float = -1        # 步长
    order_amount: int = -1      # 挂单量
    order_nums: int = -1        # 档位
    profit_rate: float = -1     # 点差


@dataclass(frozen=True)
class Status(FrozenDataclass):
    NODEAL: str = "0"
    PARTIAL: str = "1"
    ALLDEAL: str = "2"
    CANCELING: str = "3"
    CANCELLED: str = "4"


@dataclass
class OrderData(FreeDataclass):
    symbol: str
    order_id: str = ""
    customer_id: str = ""
    type: str = ""
    direction: str = ""
    price: float = -1
    amount: float = -1
    traded: float = -1
    status: Status = Status.NODEAL
    datetime: int = None
    gear: int = None                # 订单档位


@dataclass
class TimingTask(FreeDataclass):
    refresh_subscribeKey: PeriodicCallback = None
    tick_data: PeriodicCallback = None
    price_data: PeriodicCallback = None
    check_trade_by_rest: PeriodicCallback = None
    check_trade_by_redis: PeriodicCallback = None
    current_orders: PeriodicCallback = None
    keep_set_status: PeriodicCallback = None

    laying_orders: PeriodicCallback = None
    random_orders: PeriodicCallback = None


@dataclass
class TradeData(FreeDataclass):
    type: str
    traded: float = -1
    datetime: int = None


if __name__ == '__main__':
    pass
