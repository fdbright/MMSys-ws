# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/22 22:20

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from dataclasses import dataclass

from Utils import FreeDataclass


@dataclass
class Account(FreeDataclass):
    account: str
    apiKey: str = ""
    secretKey: str = ""
    team: str = ""


@dataclass
class Coin(FreeDataclass):
    symbol: str
    f_coin: str
    full_name: str
    f_coin_addr: str
    addr_type: str

    account: str
    profit_rate: float
    step_gap: float
    order_amount: int
    order_nums: int

    if1m: bool = False
    team: str = ""
    isUsing: bool = True
    createTime: str = None
    updateTime: str = None


@dataclass
class CoinPrice(FreeDataclass):
    symbol: str
    exchange: str
    account: str
    cex_price: float
    cmc_price: float
    dex_price: float
    volume: float
    flag: bool
    strategy_status: str


if __name__ == '__main__':
    pass
