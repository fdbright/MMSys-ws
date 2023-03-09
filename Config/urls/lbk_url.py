# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 21:14

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from dataclasses import dataclass
# from Template import MyUrlTemplate
from Utils import FrozenDataclass


@dataclass(frozen=True)
class LbkHost(FrozenDataclass):
    # rest: str = "http://10.10.10.96:99/v2/"
    rest: str = "https://www.lbkex.net/v2/"
    trade_wss: str = "wss://www.lbkex.net/ws/V2/"
    data_wss: str = "wss://www.lbkex.net/ws/V2/"


@dataclass(frozen=True)
class LbkApi(FrozenDataclass):
    QUERY_TIME = "timestamp.do"

    QUERY_TICK = "ticker.do"
    QUERY_CONTRACT = "accuracy.do"
    QUERY_CURRENT_PAIRS = "currencyPairs.do"
    QUERY_NETWORK = "supplement/user_info.do"

    QUERY_DEPTH = "supplement/incrDepth.do"

    # QUERY_USERINFO = "user_info.do"
    QUERY_USERINFO_ACCOUNT = "supplement/user_info_account.do"

    CREATE_ORDER = "create_order.do"
    CREATE_BATCH_ORDERS = "batch_create_order.do"

    # CANCEL_ORDER = "cancel_order.do"
    CANCEL_ORDER = "supplement/cancel_order.do"
    CANCEL_ORDER_BY_SYMBOL = "supplement/cancel_order_by_symbol.do"

    # QUERY_OPEN_ORDERS = "orders_info_no_deal.do"
    QUERY_OPEN_ORDERS = "supplement/orders_info_no_deal.do"

    QUERY_TRANSACTION_ORDERS = "supplement/transaction_history.do"

    QUERY_SUB_KEY = "subscribe/get_key.do"
    QUERY_REFRESH_SUB_KEY = "subscribe/refresh_key.do"
    CLOSE_SUB_KEY = "subscribe/destroy_key.do"

    CREATE_WITHDRAW = "supplement/withdraw.do"
    CANCEL_WITHDRAW = "withdrawCancel.do"
    QUERY_WITHDRAW_HISTORY = "supplement/withdraws.do"

    QUERY_DEPOSIT_ADDRESS = "get_deposit_address.do"
    QUERY_DEPOSIT_HISTORY = "supplement/deposit_history.do"


@dataclass(frozen=True)
class LBKUrl(FrozenDataclass):

    HOST: LbkHost = LbkHost
    API: LbkApi = LbkApi


if __name__ == '__main__':
    pass

