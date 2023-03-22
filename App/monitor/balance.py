# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:43

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import ujson
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
                data = await api.query_account_info(to_dict=True)

                info = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-DB", key="contract_data")
                price_tick: int = int(info.get(item.symbol, {}).get("priceTick", 18))

                info = await self.redis_conn.hGet(name="CMC-DB", key="cmc_price")
                cmc_price = round(info.get(item.symbol, {}).get("price", -1), price_tick)

                info = await self.redis_conn.hGet(name="DEX-DB")
                dex_price = round(float(ujson.loads(info.get(item.symbol, "{}")).get("price", -1)), price_tick)

                info = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-DB", key=f"{item.exchange.lower()}_price")
                cex_price = float(info.get(item.symbol, -1))

                if cmc_price in [-1, 0] or not cmc_price:
                    data["volume"] = 0
                else:
                    data["volume"] = round(((cex_price - cmc_price) / cmc_price) * 100, 2)
                if dex_price not in [-1, 0]:
                    data["volume"] = round(((cex_price - dex_price) / dex_price) * 100, 2)
                data["cmc_price"] = cmc_price
                data["dex_price"] = dex_price
                data["cex_price"] = cex_price
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
        self.after_request(code=code, msg="查询账户余额", action=item.channel, data=data)


if __name__ == '__main__':
    pass
