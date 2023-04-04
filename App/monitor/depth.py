# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 21:48

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import pandas as pd
from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate


@dataclass
class DepthItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    symbol: str = None
    exchange: str = "lbk"
    limit: int = 50


class Depth(MyActionTemplate):

    @staticmethod
    def __init4depth(data: dict):
        if data:
            bid = pd.DataFrame(data.get("bids", []))
            ask = pd.DataFrame(data.get("asks", []))
            bid[3] = bid[2].cumsum()
            ask[3] = ask[2].cumsum()
            bl = [list(row[1].to_dict().values()) for row in bid.iterrows()]
            al = [list(row[1].to_dict().values()) for row in ask.iterrows()][::-1]
            res = [bl, al]
        else:
            res = None
        return res

    async def get(self, item: DepthItem):
        """查询深度"""
        info: dict = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-DB", key=f"depth_data_{item.symbol.lower()}")
        # log.info(str(info))
        data = self.__init4depth(info)
        self.after_request(code=1 if data else -1, msg="查询深度", action=item, data=data)

    async def post(self, item: DepthItem):
        """查询深度"""
        if self.current_user.monOrder:
            api = self.get_rest_api_by_exchange(item.exchange, item.symbol)
            if api:
                data = await api.query_depth(symbol=item.symbol, limit=item.limit)
                await self.redis_conn.hSet(
                    name=f"{item.exchange.upper()}-DB",
                    key=f"depth_data_{item.symbol.lower()}",
                    value=data
                )
                data = self.__init4depth(data)
            else:
                data = None
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="查询深度", action=item, data=data)


if __name__ == '__main__':
    pass
