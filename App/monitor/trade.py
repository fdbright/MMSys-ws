# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:38

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate


@dataclass
class TradeItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    symbol: str = None
    exchange: str = "lbk"
    start_time: str = None  # 时间戳
    final_time: str = None  # 时间戳
    limit: int = 100


class Trade(MyActionTemplate):

    async def get(self, item: TradeItem):
        """查询历史成交记录"""
        if self.current_user.monOrder:
            api = self.get_rest_api_by_exchange(item.exchange, item.symbol)
            if api:
                info: dict = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-DB", key="contract_data")
                tick: dict = info.get(item.symbol, {})
                data = await api.query_trans_history(
                    symbol=item.symbol,
                    start_time=item.start_time,
                    final_time=item.final_time,
                    limit=item.limit,
                    price_tick=tick.get("priceTick", 18),
                    volume_tick=tick.get("amountTick", 2),
                )
            else:
                data = None
        else:
            data = None
        if data:
            if "error" in data.keys():
                code = -1
            else:
                code = 1
        else:
            code = -1
        self.after_request(code=code, msg="查询历史成交记录", action=item.channel + f".{item.action}", data=data)


if __name__ == '__main__':
    pass
