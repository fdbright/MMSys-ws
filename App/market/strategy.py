# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:49

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate
from Models import OrmMarket
from Objects import CoinObj


@dataclass
class StrategyItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    symbol: str = None
    exchange: str = "lbk"
    profit_rate: float = None
    step_gap: float = None
    order_amount: int = None
    order_nums: int = None


class Strategy(MyActionTemplate):

    async def get(self, item: StrategyItem):
        """查询策略状态"""
        if self.current_user.monStrategy:
            status = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-STG-DB", key=f"fts_status_{item.symbol}")
            data = {
                "type": "strategy",
                "symbol": item.symbol,
                "status": status.get("status", "stopped")
            }
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="查询策略状态", action=item, data=data)

    async def post(self, item: StrategyItem):
        """启动策略"""
        if self.current_user.monStrategy:
            coin_data: CoinObj = OrmMarket.search.fromCoinsTb.one(exchange=item.exchange, symbol=item.symbol, to_dict=False)
            if coin_data.isUsing:
                data = False
            else:
                conf: dict = {
                    "symbol": item.symbol,
                    "isUsing": True,
                }
                if item.profit_rate:
                    conf["profit_rate"] = float(item.profit_rate)
                if item.step_gap:
                    conf["step_gap"] = float(item.step_gap)
                if item.order_amount:
                    conf["order_amount"] = int(item.order_amount)
                if item.order_nums:
                    conf["order_nums"] = int(item.order_nums)
                data = OrmMarket.update.toCoinsTb.one(item.exchange, coin=conf)
            if data:
                await self.update2redis(exchange=item.exchange)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="启动策略", action=item, data=data)

    async def delete(self, item: StrategyItem):
        """关闭策略"""
        if self.current_user.monStrategy:
            coin_data: CoinObj = OrmMarket.search.fromCoinsTb.one(exchange=item.exchange, symbol=item.symbol, to_dict=False)
            if not coin_data.isUsing:
                data = False
            else:
                conf: dict = {
                    "symbol": item.symbol,
                    "isUsing": False,
                }
                data = OrmMarket.update.toCoinsTb.one(item.exchange, coin=conf)
            if data:
                await self.update2redis(exchange=item.exchange)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="关闭策略", action=item, data=data)


if __name__ == '__main__':
    pass
