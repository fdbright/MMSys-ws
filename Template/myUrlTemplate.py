# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 21:24

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from dataclasses import dataclass
from Utils import FrozenDataclass


@dataclass(frozen=True)
class MyUrlTemplate(FrozenDataclass):

    QUERY_TIME: str = ""

    QUERY_CURRENT_PAIRS: str = ""
    QUERY_NETWORK: str = ""

    QUERY_USERINFO: str = ""
    QUERY_USERINFO_ACCOUNT: str = ""

    CREATE_ORDER: str = ""
    CREATE_BATCH_ORDERS: str = ""

    CANCEL_ORDER: str = ""
    CANCEL_ORDER_BY_SYMBOL: str = ""

    QUERY_OPEN_ORDERS: str = ""

    QUERY_TRANSACTION_ORDERS: str = ""

    QUERY_SUB_KEY: str = ""
    QUERY_REFRESH_SUB_KEY: str = ""

    CREATE_WITHDRAW: str = ""
    CANCEL_WITHDRAW: str = ""
    QUERY_WITHDRAW_HISTORY: str = ""

    QUERY_DEPOSIT_ADDRESS: str = ""
    QUERY_DEPOSIT_HISTORY: str = ""


if __name__ == '__main__':
    pass
