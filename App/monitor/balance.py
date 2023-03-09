# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:43

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate


@dataclass
class BalanceItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    symbol: str = None
    exchange: str = "lbk"


class Balance(MyActionTemplate):

    async def get(self, item: BalanceItem):
        """查询账户余额"""
        # log.info(item)
        if self.current_user.monOrder:
            api = self.get_rest_api_by_exchange(item.exchange, item.symbol)
            if api:
                data = await api.query_account_info()
            else:
                data = None
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="查询账户余额", data=data)


if __name__ == '__main__':
    pass
