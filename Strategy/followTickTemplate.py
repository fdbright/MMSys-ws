# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/18 22:19
# 盘口跟随策略

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List, Dict, Union

import os
import random
import numpy as np
import pandas as pd
from dataclasses import dataclass
from tornado.gen import sleep
from tornado.queues import Queue
from tornado.options import define, options
from aiohttp import ClientSession

from Config import Configure, LBKUrl
from Models import LbkRestApi
from Utils import MyAioredis, MyDatetime, FreeDataclass, FrozenDataclass
from Utils import MyEngine, WebsocketClient
from Utils.myEncoder import MyEncoder


@dataclass
class Conf(FreeDataclass):
    apiKey: str = ""
    secretKey: str = ""
    account: str = ""
    team: str = ""
    symbol: str = ""
    step_gap: float = -1        # 步长
    order_amount: int = -1      # 挂单量
    order_nums: int = -1        # 档位
    profit_rate: float = -1     # 点差


@dataclass(frozen=True)
class Status(FrozenDataclass):
    NODEAL: str = "0"
    PARTIAL: str = "1"
    ALLDEAL: str = "2"
    CANCELLED: str = "3"


@dataclass
class OrderData(FreeDataclass):
    symbol: str
    order_id: str = ""
    customer_id: str = ""
    type: str = ""
    direction: str = ""
    price: float = -1
    amount: float = -1
    traded: float = -1
    status: Status = Status.NODEAL
    datetime: int = None
    gear: int = None                # 订单档位


class FollowTickTemplate(MyEngine, WebsocketClient):

    def __init__(self):
        super().__init__()
        self.symbol: str = options.symbol.lower()
        self.f_coin, self.l_coin = self.symbol.upper().split("_")
        self.account: str = ""
        self.exchange: str = options.exchange.lower()
        self.server: str = options.server

        # log
        self.fp = os.path.join(Configure.LOG_PATH, "stg", f"stg_{self.symbol}.log")
        log.add(self.fp, retention="2 days", encoding="utf-8")

        # stg
        self.custom: str = "FTS"
        self.first_time: bool = True
        self.order_todo = Queue()

        self.status_value: dict = {
            "status": "running",
            "start_time": "",
            "upgrade_time": "",
            "upgrade_time_dt": "",
            "server": self.server,
            "conf": {}
        }

        self.time_count: int = 0
        self.hr1_sec: int = 50 * 60
        self.hr2_sec: int = 2 * 60 * 60

        self.temp_uuid: dict = {}
        self.coin_balance: float = -1  # 币余额
        self.base_balance: float = -1  # U余额
        self.order_uuid2data: Dict[str, OrderData] = {}
        self.order_gear2data: Dict[int, OrderData] = {}

        self.current_order_ids: List[str] = []

        self.order_status: dict = {
            "-1": Status.CANCELLED,
            "0": Status.NODEAL,
            "1": Status.PARTIAL,
            "2": Status.ALLDEAL,
            "4": Status.CANCELLED,
        }

        self.conf: Conf = None
        self.trade_limit: int = 1000
        self.bid_trade_qty: Dict[str, float] = {}   # 买成交总额
        self.ask_trade_qty: Dict[str, float] = {}   # 卖成交总额
        self.cex_price: float = -1
        self.dex_price: float = -1
        self.cmc_price: float = -1
        self.order_price: float = -1

        self.thisPrice: float = -1      # 本次价格
        self.lastPrice: float = -1      # 上次价格
        self.this_orderbook: dict = {}
        self.last_orderbook: dict = {}

        self.order_conf: dict = {}
        self.price_tick: int = -1       # 价格精度
        self.min_volume: float = -1     # 最低下单数量
        self.volume_tick: int = -1      # 数量精度

        # redis
        self.redis_pool: MyAioredis = options.redis_pool
        self.name = f"{self.exchange.upper()}-DB"
        self.name_stg = f"{self.exchange.upper()}-STG-DB"
        self.key = "lbk_db"
        self.key_stg = f"{self.symbol}_fts_status"

        # rest_api
        self.api = None

        # websocket
        self.wss_url: str = ""
        self.subscribe_key: str = ""
        self.is_connected: bool = False

        self.SIGN: bool = False     # 是否暂停策略

    async def init_by_exchange(self):
        if self.exchange == "lbk":
            self.api = LbkRestApi(htp_client=ClientSession(trust_env=True))
            self.wss_url = LBKUrl.HOST.trade_wss
        else:
            pass
        self.api.api_key = self.conf.apiKey
        self.api.secret_key = self.conf.secretKey
        log.info("根据交易所初始化 api")

    async def get_conf_from_redis(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            data = await conn.hGet(name=self.name, key=self.key)
            self.conf = Conf(**data.get(self.symbol, {}))
            self.account = self.conf.account
        except Exception as e:
            log.error(f"获取 币对配置信息 失败: {self.symbol}, {e}")
        else:
            self.conf.secretKey = MyEncoder.byDES(Configure.SECRET_KEY).decode(self.conf.secretKey)

            self.conf.step_gap = float(self.conf.step_gap)              # 步长
            self.conf.order_amount = int(self.conf.order_amount / 2)    # 挂单量
            self.conf.order_nums = int(self.conf.order_nums)            # 档位
            self.conf.profit_rate = float(self.conf.profit_rate / 2)    # 点差

            self.status_value["conf"] = self.conf.to_dict()
        await conn.close()
        del conn, data
        log.info(f"获取 币对配置信息: {self.conf}")

    async def check_open_orders(self):
        log.info("检查是否有上次策略遗留挂单")
        resp: dict = await self.api.query_open_orders(symbol=self.symbol)
        order_lst: List[dict] = resp.get("order_lst", [])
        for order in order_lst:
            custom_id: str = order["custom_id"]
            if custom_id.startswith(self.custom):
                order_id = order["order_id"]
                if order["order_id"] not in self.current_order_ids:
                    await self.api.cancel_order(symbol=self.symbol, order_id=order_id)
                    log.info(f"上次策略遗留挂单, 执行撤单, custom_id: {custom_id}, order_id: {order_id}")
                del order_id
            del custom_id
        del resp, order_lst

    async def get_tick_from_redis(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            data = await conn.hGet(name=self.name, key="contract_data")
            self.order_conf = data.get(self.symbol, {})
            self.price_tick = int(self.order_conf.get("priceTick", -1))
            self.min_volume = float(self.order_conf.get("minVol", -1))
            self.volume_tick = int(self.order_conf.get("amountTick", -1))
        except Exception as e:
            log.error(f"获取 contract_data 失败: {self.symbol}, {e}")
        await conn.close()
        del conn, data
        log.info("获取 contract_data")

    async def get_price_from_redis(self):
        conn = await self.redis_pool.open(conn=True)
        try:
            data = await conn.hGet(name=self.name, key=f"{self.exchange}_price")
            self.cex_price = float(data.get(self.symbol, -1))
            data = await conn.hGet(name="CMC-DB", key=self.symbol)
            self.cmc_price = float(data.get("price", -1))
            data = await conn.hGet(name="DEX-DB", key=self.symbol)
            self.dex_price = round(float(data.get("price", -1)), self.price_tick)
        except Exception as e:
            log.error(f"获取 price 失败: {self.symbol}, {e}")
        try:
            data = await conn.hGet(name=self.name, key="account_data")
            account_info = data.get(self.account, {})
        except Exception as e:
            log.error(f"获取 account_info 失败: {self.account}, {e}")
        else:
            self.coin_balance = float(account_info.get(self.f_coin, {}).get("free", -1))
            self.base_balance = float(account_info.get(self.l_coin, {}).get("free", -1))
        await conn.close()
        del conn, data
        log.info("获取 price_data")

    async def cancel_order(self, custom_id: str):
        order_data = self.order_uuid2data.pop(custom_id)
        resp = await self.api.cancel_order(symbol=self.symbol, order_id=order_data.order_id)
        if resp.get("result", False):
            try:
                self.current_order_ids.remove(order_data.order_id)
            except ValueError:
                pass
        del order_data, resp

    async def create_order(self, item: OrderData):
        custom_id = self.api.make_custom_id(custom=self.custom)
        self.order_uuid2data[custom_id] = item
        resp = await self.api.create_order(
            symbol=self.symbol,
            _type=item.type,
            price=item.price,
            amount=item.amount,
            custom_id=custom_id,
            conf=self.order_conf
        )
        if resp.get("result", False):
            self.current_order_ids.append(resp.get("order_id"))
        del custom_id, resp

    async def keep_handle_orders(self):
        while True:
            item: Union[str, OrderData] = await self.order_todo.get()
            if isinstance(item, str):
                await self.add_task(self.cancel_order, args=(item,))
            else:
                await self.add_task(self.create_order, args=(item,))

    async def check_trade_amount(self):
        ft = MyDatetime.timestamp() - 60
        st = ft - self.hr2_sec
        data = await self.api.query_trans_history(symbol=self.symbol, start_time=str(st), final_time=str(ft))
        try:
            bid, ask = 0, 0
            for trade in data["trans_lst"]:
                if trade["type"] == "sell":
                    ask += trade["quoteQty"]
                else:
                    bid += trade["quoteQty"]
            trade_amount = bid - ask
        except Exception:
            trade_amount = 0
        finally:
            del bid, ask
        if trade_amount > self.trade_limit:
            self.SIGN = True
            if self.order_uuid2data:
                self.order_uuid2data = {}
                self.order_gear2data = {}
                await self.api.cancel_all_orders(symbol=self.symbol)
            log.info(f"最近 2hour 成交额大于 {self.trade_limit}: {trade_amount}, 暂停策略")
        else:
            if self.SIGN:
                self.SIGN = False
                self.time_count = 1
                self.first_time = True
                log.info(f"最近 2hour 成交额小于 {self.trade_limit}: {trade_amount}, 重启策略")
        del ft, st, data, trade_amount

    def cal_volume(self, trade_type="bid") -> List[float]:
        """计算每档下单的usdt"""
        res = []
        # 检查账户余额
        if self.base_balance < (self.coin_balance * self.thisPrice):
            ava = self.base_balance
        else:
            ava = self.coin_balance * self.thisPrice
        if ava < self.conf.order_amount:
            self.conf.order_amount = round(ava * random.uniform(0.5, 0.9))
        del ava
        mid = int(self.conf.order_amount / self.conf.order_nums)
        for _ in range(self.conf.order_nums):
            amount = round(random.uniform(0.5, 1.5) * mid, 2)
            if amount <= 10:
                amount = round(random.uniform(1, 1.5) * 10, 2)
            res.append(round(amount / self.thisPrice, self.volume_tick))
            del amount
        del mid
        if trade_type == "bid":
            return sorted(res, reverse=True)
        else:
            return sorted(res)

    def cal_orderbook(self, bid_ask, trade_type="bid"):
        """计算订单本"""
        try:
            if self.price_tick != -1 and self.thisPrice != -1:
                self.conf.step_gap = max([self.conf.step_gap, pow(10, -self.price_tick) / self.thisPrice])
                self.conf.profit_rate = max([self.conf.profit_rate, pow(10, -self.price_tick) / self.thisPrice])
            else:
                return
            if trade_type == "bid":
                ba = bid_ask * (1 - self.conf.profit_rate)
                ba_price = np.linspace(ba * (1 - self.conf.step_gap * self.conf.order_nums), ba, self.conf.order_nums)
                ba_price = sorted(ba_price, reverse=True)
            else:
                ba = bid_ask * (1 + self.conf.profit_rate)
                ba_price = np.linspace(ba * (1 + self.conf.step_gap * self.conf.order_nums), ba, self.conf.order_nums)
                ba_price = sorted(ba_price)
            del ba
            return pd.Series(ba_price, index=range(1, self.conf.order_nums + 1)).to_dict()
        except Exception as e:
            print(f"计算订单本出错: {e}")

    def cal_deviation(self) -> list:
        """计算新的订单本偏移量"""
        to_change = []
        # num = 0
        if self.thisPrice < self.lastPrice:
            for i in range(1, self.conf.order_nums + 1):
                if self.thisPrice > self.last_orderbook[i]["price"]:
                    # num = i
                    break
                to_change.append(i)
        else:
            for i in range(1, self.conf.order_nums + 1):
                if self.thisPrice < self.last_orderbook[0 - i]["price"]:
                    # num = 0 - i
                    break
                to_change.append(0 - i)
        return sorted(to_change, reverse=True)

    def cal_O_V(self, price) -> dict:
        ob = {}
        ob_bid = self.cal_orderbook(bid_ask=price, trade_type="bid")
        ob_ask = self.cal_orderbook(bid_ask=price, trade_type="ask")
        vl_bid = self.cal_volume(trade_type="bid")
        vl_ask = self.cal_volume(trade_type="ask")
        for k, price in ob_bid.items():
            ob[k] = {"price": price, "volume": vl_bid[k - 1]}
        for k, price in ob_ask.items():
            ob[0 - k] = {"price": price, "volume": vl_ask[k - 1]}
        del ob_bid, ob_ask, vl_bid, vl_ask
        return ob

    async def cal_change_orders(self, to_change):
        if to_change[-1] > 0:
            num = max(to_change)
        else:
            num = min(to_change)
        temp = {}
        for k, v in self.order_gear2data.items():
            if k > 0 and k + num <= self.conf.order_nums:
                temp[k + num] = v
            if k < 0 and k - num >= -self.conf.order_nums:
                temp[k - num] = v
        for k in to_change:
            odd: OrderData = self.order_gear2data[k]
            await self.order_todo.put(odd.order_id)
            log.info(f"价格波动, 执行撤单, 档位: {k}")

            if k > 0:
                k1 = k - (self.conf.order_nums + 1)
            else:
                k1 = (self.conf.order_nums + 1) + k
            odd: OrderData = self.order_gear2data[k1]
            await self.order_todo.put(odd.order_id)
            log.info(f"价格波动, 执行撤单, 档位 {k1}")

            k2 = 0 - k
            trade_type = "buy" if k2 > 0 else "sell"
            new_orr = OrderData(
                symbol=self.symbol,
                type=trade_type,
                price=self.this_orderbook[k2]["price"],
                amount=self.this_orderbook[k2]["volume"],
                gear=k2
            )
            await self.order_todo.put(new_orr)
            temp[k2] = new_orr
            log.info(f"价格波动, 执行挂单, 档位 {k2}")

            if k2 > 0:
                k3 = k2 - (self.conf.order_nums + 1)
                trade_type = "sell"
            else:
                k3 = (self.conf.order_nums + 1) + k2
                trade_type = "buy"
            new_orr = OrderData(
                symbol=self.symbol,
                type=trade_type,
                price=self.this_orderbook[k3]["price"],
                amount=self.this_orderbook[k3]["volume"],
                gear=k3
            )
            await self.order_todo.put(new_orr)
            temp[k3] = new_orr
            log.info(f"价格波动, 执行挂单, 档位 {k3}")
        # 更新order_dict
        self.order_gear2data = temp.copy()
        del num, temp

    async def on_current_orders(self):
        conn = await self.redis_pool.open(conn=True)
        await conn.hSet(name=self.name_stg, key=f"order_ids_{self.symbol}", value={"orderIds": self.current_order_ids})
        await conn.close()
        del conn

    async def on_status(self, first_time: bool = False):
        conn = await self.redis_pool.open(conn=True)
        now = MyDatetime.today()
        if first_time:
            self.status_value["start_time"] = MyDatetime.dt2ts(now, thousand=True)
        self.status_value["upgrade_time"] = MyDatetime.dt2ts(now, thousand=True)
        self.status_value["upgrade_time_dt"] = MyDatetime.dt2str(now)
        await conn.hSet(name=self.name_stg, key=f"fts_status_{self.symbol}", value=self.status_value)
        await conn.close()
        del conn, now

    async def on_timer(self):
        log.info(f"ws_status: {self.is_connected}")
        if not self.is_connected:
            return
        self.time_count += 1

        # 首次执行, 更新状态
        if self.time_count == 1:
            await self.on_status(first_time=True)
            await self.get_tick_from_redis()
            await self.get_price_from_redis()

        if self.time_count % self.hr1_sec == 0:
            await self.api.refresh_subscribeKey(self.subscribe_key)

        if self.time_count % 30 == 0:
            await self.check_trade_amount()
        if self.SIGN:
            return

        # 更新 order_ids, 1sec
        await self.on_current_orders()

        # 更新 状态, 1min
        if self.time_count % 60 == 0:
            await self.on_status()

        # 更新 ticks, 5 min
        if self.time_count % 300 == 0:
            await self.get_tick_from_redis()

        # 更新 price, avg, 5sec
        if self.time_count % 5 == 0:
            await self.get_price_from_redis()

        # 第一次, 10sec
        if self.time_count == 1 or self.time_count % 10 == 0:
            if not self.coin_balance:
                return
            if self.base_balance <= 700:
                self.conf.profit_rate *= 2
            elif self.base_balance <= 300:
                self.conf.profit_rate *= 4
            if not self.price_tick:
                return
            self.thisPrice = self.dex_price if self.dex_price not in [-1, 0] else self.cmc_price
            if self.thisPrice == -1:
                return

            # 首次执行, 继续进行, 并赋值上次价格
            if self.first_time:
                log.info(f"{self.symbol.upper()}, 首次启动, 执行铺单")
                self.first_time = False
                self.lastPrice = self.thisPrice
                self.this_orderbook = self.cal_O_V(price=self.thisPrice)
                log.info(f"首次订单本: {self.this_orderbook}")
                for k, v in self.this_orderbook.items():  # 从内向外挂单
                    trade_type = "buy" if k > 0 else "sell"
                    od = OrderData(
                        symbol=self.symbol,
                        type=trade_type,
                        price=v["price"],
                        amount=v["volume"],
                        gear=k
                    )
                    self.order_gear2data[k] = od
                    await self.order_todo.put(od)
            # 非首次执行
            else:
                if self.thisPrice == self.lastPrice:  # 若价格无变化，则不进行处理
                    log.info(f"{self.symbol.upper()}, 价格暂无变化")
                    return
                else:
                    log.info(f"价格出现波动, 上次: {self.lastPrice}, 本次: {self.thisPrice}")
                    self.this_orderbook = self.cal_O_V(price=self.thisPrice)
                    to_change = self.cal_deviation()
                    if to_change:
                        log.info(f"价格波动较大, 执行挂撤")
                        await self.cal_change_orders(to_change)
                    else:
                        pra = (self.this_orderbook[1]["price"] - self.order_gear2data[1].price) // self.conf.profit_rate
                        log.info(f"价格波动较大, {pra}")
                        if pra == 0:
                            log.info(f"{self.symbol.upper()}, 价格波动较小, 不进行操作")
                        else:
                            if pra > 0:
                                this_change = [i for i in range(1, round(pra) + 1)]
                            else:
                                this_change = [-i for i in range(round(abs(pra)), 0, -1)]
                            await self.cal_change_orders(this_change)
            self.last_orderbook = self.this_orderbook.copy()
            self.this_orderbook = {}
            self.lastPrice = self.thisPrice

        # 定期随机挂撤, 15sec
        if self.time_count % 15 == 0:
            k_bid, k_ask = random.randint(-10, -1), random.randint(1, 10)
            odd_bid: OrderData = self.order_gear2data.get(k_bid, None)
            odd_ask: OrderData = self.order_gear2data.get(k_ask, None)
            if odd_bid and isinstance(odd_bid, OrderData):
                self.temp_uuid[odd_bid.order_id] = k_bid
                await self.order_todo.put(odd_bid.order_id)
                log.info(f"定期随机挂撤, 档位: {k_bid}, {odd_bid}")
            if odd_ask and isinstance(odd_ask, OrderData):
                self.temp_uuid[odd_ask.order_id] = k_ask
                await self.order_todo.put(odd_ask.order_id)
                log.info(f"定期随机挂撤, 档位: {k_ask}, {odd_ask}")

    async def on_order(self, data: dict):
        customer_id = data.get("customerID", "")
        if customer_id.startswith(self.custom):
            order_data = self.order_uuid2data.get(customer_id, None)
            if not order_data:
                return
            order_data.order_id = data["uuid"]
            order_data.customer_id = customer_id
            order_data.direction = data["type"]
            order_data.price = float(data["orderPrice"])
            order_data.amount = float(data["orderAmt"])
            order_data.traded = float(data["accAmt"]) * float(data["avgPrice"])
            order_data.status = self.order_status[str(data["orderStatus"])]
            order_data.datetime = int(data["updateTime"])
            self.order_uuid2data[order_data.order_id] = order_data
            self.order_gear2data[order_data.gear] = order_data

            # 完全成交单, 进行补单
            if order_data.status == Status.ALLDEAL:
                to_order = False
                if order_data.type == "buy":
                    if self.base_balance > (order_data.price * order_data.amount):
                        to_order = True
                else:
                    if self.coin_balance > order_data.amount:
                        to_order = True
                if to_order:
                    await self.order_todo.put(order_data)
                    self.order_gear2data[order_data.gear] = order_data
                    log.info(f"补单: {order_data}")
                log.info(f"全部成交单: {order_data.type}, 原单: {order_data}")

            # 策略执行的随机撤单
            if order_data.status == Status.CANCELLED:
                if order_data.order_id in self.temp_uuid.keys():
                    await self.order_todo.put(order_data)
                    try:
                        del self.temp_uuid[order_data.order_id]
                    except KeyError:
                        pass

        del customer_id

    async def on_packet(self, item: dict):
        log.info(f"packet: {item}")
        if item.get("action", None) == "ping":
            await self.on_ping(item)
            return
        if item.get("status", None) == "error":
            await self.on_connected()
            return
        _type: str = item.get("type", None)
        if _type == "orderUpdate":
            await self.on_order(item["orderUpdate"])
        else:
            pass
        del _type

    async def on_ping(self, data: dict):
        await self.send_packet({"action": "pong", "pong": data["ping"]})

    async def on_connected(self):
        await self.send_packet({
            "action": "subscribe",
            "subscribe": "orderUpdate",
            "subscribeKey": self.subscribe_key,
            "pair": self.symbol
        })
        await self.api.refresh_subscribeKey(self.subscribe_key)

    async def initialize(self):
        await self.get_conf_from_redis()    # 获取币对&策略配置
        await self.init_by_exchange()       # 初始化Api
        await sleep(0.5)
        await self.check_open_orders()      # 撤销上次策略遗留挂单
        # subscribe_key
        data = await self.api.query_subscribeKey()
        log.info(f"subscribe_key: {data}")
        self.subscribe_key = data.get("key", None)
        del data
        await self.get_tick_from_redis()
        await self.get_price_from_redis()

    def run(self):
        self.loop.run_sync(self.initialize)
        self.loop.add_callback(self.keep_handle_orders)
        self.loop.add_callback(lambda: self.subscribe(self.wss_url))
        self.start(interval=1)


if __name__ == '__main__':
    define(name="symbol", type=str, default="apollo_usdt")
    define(name="exchange", type=str, default="lbk")
    define(name="server", type=str, default="main")

    define(name="redis_pool", default=MyAioredis(0))

    options.parse_command_line()

    FollowTickTemplate().run()
