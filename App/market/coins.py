# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:01

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import List

import ujson
from dataclasses import dataclass

from Utils import FreeDataclass
from Config import Configure
from Webs import MyActionTemplate
from Models import OrmMarket
from Objects import CoinObj, CoinPriceObj


@dataclass
class CoinsItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    symbol: str = None
    exchange: str = "lbk"
    new_coin: dict = None


class Coins(MyActionTemplate):

    async def get(self, item: CoinsItem):
        """获取所有币对数据"""
        if self.current_user.monSearch:
            if self.current_user.team == "":
                coins: List[CoinObj] = OrmMarket.search.fromCoinsTb.all(item.exchange)
            else:
                coins: List[CoinObj] = OrmMarket.search.fromCoinsTb.byTeam(item.exchange, self.current_user.team)
            cex_price_dict: dict = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-DB", key=f"{item.exchange.lower()}_price")
            cmc_price_dict: dict = await self.redis_conn.hGet(name="CMC-DB", key="cmc_price")
            # dex_price_dict: dict = await self.redis_conn.hGet(name="DEX-DB")
            dex_price_dict: dict = await self.redis_conn.hGet(name="DEX-DB", key="dex_price")
            contract_data: dict = await self.redis_conn.hGet(name=f"{item.exchange.upper()}-DB", key="contract_data")
            data = []
            for coin in coins:
                price_tick = int(contract_data.get(coin.symbol, {}).get("priceTick", 18))
                cmc_price = round(float(cmc_price_dict.get(coin.symbol, {}).get("price", -1)), price_tick)
                dex_price = round(float(dex_price_dict.get(coin.symbol, {}).get("price", -1)), price_tick)
                cex_price = float(cex_price_dict.get(coin.symbol, -1))
                # log.info(f"dex_price: {dex_price}, cmc_price: {cmc_price}")
                if cmc_price in [-1, 0] or not cmc_price:
                    volume = 0
                else:
                    volume = round(((cex_price - cmc_price) / cmc_price) * 100, 2)
                if dex_price not in [-1, 0]:
                    volume = round(((cex_price - dex_price) / dex_price) * 100, 2)
                strategy_data: dict = await self.redis_conn.hGet(
                    name=Configure.REDIS.stg_db.format(exchange=item.exchange.upper()),
                    key=f"fts_status_{coin.symbol}"
                )
                data.append(CoinPriceObj(
                    symbol=coin.symbol,
                    exchange=item.exchange,
                    account=coin.account,
                    cex_price=cex_price,
                    cmc_price=cmc_price,
                    dex_price=dex_price,
                    volume=volume,
                    flag=True if abs(volume) >= 5 else False,
                    strategy_status=strategy_data.get("status", "stopped")
                    # strategy_status="running" if coin.isUsing else "stopped"
                ).to_dict())
            data = sorted(data, key=lambda x: x["symbol"])
            if data:
                await self.update2redis(exchange=item.exchange)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="获取所有币对数据", action=item, data=data)

    async def post(self, item: CoinsItem):
        """新增币对"""
        if self.current_user.monCreate:
            if isinstance(item.new_coin, list):
                data = OrmMarket.create.toCoinsTb.batch(item.exchange, [CoinObj(**val) for val in item.new_coin])
            else:
                data = OrmMarket.create.toCoinsTb.one(item.exchange, CoinObj(**item.new_coin))
            if data:
                await self.update2redis(exchange=item.exchange)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="新增币对", action=item, data=data)

    async def put(self, item: CoinsItem):
        """修改币对"""
        if self.current_user.monUpdate:
            data = OrmMarket.update.toCoinsTb.one(item.exchange, item.new_coin)
            if data:
                await self.update2redis(exchange=item.exchange)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="修改币对", action=item, data=data)

    async def delete(self, item: CoinsItem):
        """删除币对"""
        if self.current_user.monDelete:
            data = OrmMarket.delete.fromCoinsTb.one(item.exchange, item.symbol)
            if data:
                await self.update2redis(exchange=item.exchange)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="删除币对", action=item, data=data)


if __name__ == '__main__':
    pass
