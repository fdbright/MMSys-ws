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
from Config import Configure


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
            strategy_data: dict = await self.redis_conn.hGet(
                name=Configure.REDIS.stg_db.format(exchange=item.exchange.upper()),
                key=f"fts_status_{item.symbol}"
            )
            status = strategy_data.get("status", "stopped")
            data = {
                "type": "strategy",
                "symbol": item.symbol,
                "status": status
            }
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="查询策略状态", action=item.channel, data=data)

    async def post(self, item: StrategyItem):
        """启动策略"""
        if self.current_user.monStrategy:
            data = await self.redis_conn.hGet(
                name=Configure.REDIS.stg_db.format(exchange=item.exchange.upper()),
                key=f"fts_status_{item.symbol}"
            )
            status = data.get("status", None)
            if status in ["running", "starting"]:
                data = False
            else:
                info: dict = OrmMarket.search.fromCoinsTb.forStg(item.exchange, item.symbol, decode=True)
                conf: dict = {
                    "profit_rate": item.profit_rate if item.profit_rate else info["profit_rate"],
                    "step_gap": item.step_gap if item.step_gap else info["step_gap"],
                    "order_amount": item.order_amount if item.order_amount else info["order_amount"],
                    "order_nums": item.order_nums if item.order_nums else info["order_nums"]
                }
                fts_count = await self.redis_conn.hGet(
                    name=Configure.REDIS.stg_db.format(exchange=item.exchange.upper()),
                    key=f"stg_count_133"
                )
                if int(fts_count.get("count", 0)) <= 120:
                    server_id = "133"
                else:
                    server_id = "56"
                kwargs = {
                    "todo": "start",
                    "symbol": item.symbol,
                    "account": info["account"],
                    "exchange": item.exchange,
                    "conf": conf,
                    "team": info["team"],
                    "server_id": server_id,
                }
                log.info(Configure.REDIS.stg_ws_channel.format(exchange=item.exchange.upper(), server_id=server_id))
                await self.redis_conn.publish(
                    channel=Configure.REDIS.stg_ws_channel.format(exchange=item.exchange.upper(), server_id=server_id),
                    msg=kwargs
                )
                data = True
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="启动策略", action=item.channel, data=data)

    async def delete(self, item: StrategyItem):
        """关闭策略"""
        if self.current_user.monStrategy:
            info: dict = OrmMarket.search.fromCoinsTb.forStg(item.exchange, item.symbol, decode=True)
            account = info["account"]
            data = await self.redis_conn.hGet(
                name=Configure.REDIS.stg_db.format(exchange=item.exchange.upper()),
                key=f"fts_status_{item.symbol}"
            )
            server_id = data.get("server_id", "133")
            kwargs = {
                "todo": "stop",
                "symbol": item.symbol,
                "account": account,
                "exchange": item.exchange,
                "team": info["team"],
                "server_id": server_id
            }
            await self.redis_conn.publish(
                channel=Configure.REDIS.stg_ws_channel.format(exchange=item.exchange.upper(), server_id=server_id),
                msg=kwargs
            )
            data = True
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="关闭策略", action=item.channel, data=data)


if __name__ == '__main__':
    pass
