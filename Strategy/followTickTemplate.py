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
import schedule
import numpy as np
import pandas as pd
from tornado.gen import sleep
from tornado.queues import Queue
from tornado.ioloop import IOLoop
from tornado.options import define, options
from aiohttp import ClientSession

from Config import Configure, LBKUrl
from Models import LbkRestApi
from Objects import Conf, Status, OrderData
from Utils import MyAioredisV2, MyDatetime
from Utils import WebsocketClient
from Utils.myEncoder import MyEncoder


class Cal4STG:

    def __init__(self, conf: Conf):
        self.conf = conf

    def _cal_orderbook(self, bid_ask, price_tick, this_price, trade_type="bid"):
        """计算订单本"""
        try:
            if price_tick != -1 and this_price != -1:
                self.conf.step_gap = max([self.conf.step_gap, pow(10, -price_tick) / this_price])
                self.conf.profit_rate = max([self.conf.profit_rate, pow(10, -price_tick) / this_price])
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

    def _cal_volume(self, coin_balance, base_balance, this_price, volume_tick, trade_type="bid") -> List[float]:
        """计算每档下单的usdt"""
        res = []
        # 检查账户余额
        if base_balance < (coin_balance * this_price):
            ava = base_balance
        else:
            ava = coin_balance * this_price
        if ava < self.conf.order_amount:
            self.conf.order_amount = round(ava * random.uniform(0.5, 0.9))
        del ava
        mid = int(self.conf.order_amount / self.conf.order_nums)
        for _ in range(self.conf.order_nums):
            amount = round(random.uniform(0.5, 1.5) * mid, 2)
            if amount <= 10:
                amount = round(random.uniform(1, 1.5) * 10, 2)
            res.append(round(amount / this_price, volume_tick))
            del amount
        del mid
        if trade_type == "bid":
            return sorted(res, reverse=True)
        else:
            return sorted(res)

    def cal_orderbook_volume(self, price, price_tick, volume_tick, this_price, coin_balance, base_balance) -> dict:
        ob = {}
        ob_bid = self._cal_orderbook(price, price_tick, this_price, trade_type="bid")
        ob_ask = self._cal_orderbook(price, price_tick, this_price, trade_type="ask")
        vl_bid = self._cal_volume(coin_balance, base_balance, this_price, volume_tick, trade_type="bid")
        vl_ask = self._cal_volume(coin_balance, base_balance, this_price, volume_tick, trade_type="ask")
        for k, price in ob_bid.items():
            ob[k] = {"price": price, "volume": vl_bid[k - 1]}
        for k, price in ob_ask.items():
            ob[0 - k] = {"price": price, "volume": vl_ask[k - 1]}
        del ob_bid, ob_ask, vl_bid, vl_ask
        return ob

    def cal_deviation(self, this_price, last_price, last_orderbook) -> list:
        """计算新的订单本偏移量"""
        to_change = []
        # num = 0
        if this_price < last_price:
            for i in range(1, self.conf.order_nums + 1):
                if this_price > last_orderbook[i]["price"]:
                    # num = i
                    break
                to_change.append(i)
        else:
            for i in range(1, self.conf.order_nums + 1):
                if this_price < last_orderbook[0 - i]["price"]:
                    # num = 0 - i
                    break
                to_change.append(0 - i)
        return sorted(to_change, reverse=True)


class FollowTickTemplate(WebsocketClient):

    def __init__(self):
        super().__init__()
        self.server: str = options.server
        self.symbol: str = options.symbol.lower()
        self.f_coin, self.l_coin = self.symbol.upper().split("_")
        self.account: str = ""
        self.exchange: str = options.exchange.lower()

        # loop
        self.loop = IOLoop.current()

        # log
        self.fp = os.path.join(Configure.LOG_PATH, "stg", f"stg_{self.symbol}.log")
        # log.add(self.fp, retention="2 days", encoding="utf-8")

        # redis
        self.redis_pool_db0 = MyAioredisV2(db=0)
        self.redis_pool_db1 = MyAioredisV2(db=1)

        self.name = f"{self.exchange.upper()}-DB"
        self.name_stg = f"{self.exchange.upper()}-STG-DB"
        self.key: str = f"{self.exchange}_db"

        # stg_constants
        self.time_count: int = 0
        self.hr1_sec: int = 50 * 60
        self.hr2_sec: int = 2 * 60 * 60
        self.hr8_sec: int = 8 * 60 * 60

        self.custom: str = "FTS"
        self.order_todo = Queue()

        self.empty_coin: bool = False   # 币数量不足, 10014
        self.empty_base: bool = False   # U数量不足, 10016

        self.status_value: dict = {
            "status": "running",
            "start_time": "",
            "upgrade_time": "",
            "upgrade_time_dt": "",
            "server": self.server,
            "conf": {}
        }

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
            "4": Status.CANCELING,
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

        # cal_func
        self.cal_func = Cal4STG(conf=self.conf)

        # rest_api
        self.api = None

        # websocket
        self.wss_url: str = ""
        self.subscribe_key: str = ""
        self.is_connected: bool = False

        self.random_count: int = 0
        self.SIGN: bool = False         # 是否需要关闭策略

    async def init_by_exchange(self):
        self.session = ClientSession(trust_env=True)
        if self.exchange == "lbk":
            self.api = LbkRestApi(htp_client=self.session)
            self.wss_url = LBKUrl.HOST.trade_wss
        else:
            pass
        self.api.api_key = self.conf.apiKey
        self.api.secret_key = self.conf.secretKey
        log.info("根据交易所初始化 api")

    async def get_conf_from_redis(self):
        conn = await self.redis_pool_db0.open()
        try:
            data = await conn.hget(name=self.name, key=self.key)
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

            self.cal_func.conf = self.conf

            self.status_value["conf"] = self.conf.to_dict()
        await conn.close()
        del conn, data
        log.info(f"获取 币对配置信息: {self.conf}")

    async def get_tick_from_redis(self):
        conn = await self.redis_pool_db0.open()
        try:
            data = await conn.hget(name=self.name, key="contract_data")
            self.order_conf = data.get(self.symbol, {})
            self.price_tick = int(self.order_conf.get("priceTick", -1))
            self.min_volume = float(self.order_conf.get("minVol", -1))
            self.volume_tick = int(self.order_conf.get("amountTick", -1))
        except Exception as e:
            log.error(f"获取 contract_data 失败: {self.symbol}, {e}")
        await conn.close()
        del conn, data
        log.info(f"获取 contract_data: {self.order_conf}")

    async def get_price_from_redis(self):
        conn = await self.redis_pool_db0.open()
        try:
            data = await conn.hget(name=self.name, key=f"{self.exchange}_price")
            self.cex_price = float(data.get(self.symbol, -1))
            data = await conn.hget(name="CMC-DB", key=self.symbol)
            self.cmc_price = float(data.get("price", -1))
            data = await conn.hget(name="DEX-DB", key=self.symbol)
            self.dex_price = round(float(data.get("price", -1)), self.price_tick)
        except Exception as e:
            log.error(f"获取 price 失败: {self.symbol}, {e}")
        try:
            data = await conn.hget(name=self.name, key="account_data")
            account_info = data.get(self.account, {})
        except Exception as e:
            log.error(f"获取 account_info 失败: {self.account}, {e}")
        else:
            self.coin_balance = float(account_info.get(self.f_coin, {}).get("free", -1))
            self.base_balance = float(account_info.get(self.l_coin, {}).get("free", -1))
        await conn.close()
        del conn, data
        log.info(f"获取 price_data, cex: {self.cex_price}, cmc: {self.cmc_price}, dex: {self.dex_price}")
        log.info(f"is_connected: {self.is_connected}")

    async def check_params(self):
        if self.cmc_price == -1 and self.dex_price == -1:
            log.warning("缺少价格参数, 停止策略")
            await self.stop_stg(send_msg=False)

    async def check_last_open_orders(self):
        log.info("检查是否有上次策略遗留挂单")
        resp: dict = await self.api.query_open_orders(symbol=self.symbol)
        # log.info(f"检查是否有上次策略遗留挂单: {resp}")
        order_lst: List[dict] = resp.get("order_lst", [])
        if isinstance(order_lst, list):
            for order in order_lst:
                custom_id: str = order["custom_id"]
                if custom_id.startswith(self.custom):
                    await self.cancel_order(order_id=order["order_id"])
                    log.info(f"上次策略遗留挂单, 执行撤单, custom_id: {custom_id}")
                del custom_id
        del resp, order_lst

    async def cancel_order(self, custom_id: str = None, order_id: str = None):
        if custom_id:
            try:
                order_id = self.order_uuid2data.get(custom_id).order_id
            except:
                return
        resp = await self.api.cancel_order(symbol=self.symbol, order_id=order_id)
        log.info(f"cancel_order: {resp}")
        if resp.get("result", False):
            try:
                self.current_order_ids.remove(order_id)
            except ValueError:
                pass
        del resp

    async def create_order(self, item: OrderData):
        self.order_uuid2data[item.customer_id] = item
        resp = await self.api.create_order(
            symbol=self.symbol,
            _type=item.type,
            price=item.price,
            amount=item.amount,
            custom_id=item.customer_id,
            conf=self.order_conf
        )
        log.info(f"create_order: {resp}")
        # error_code = resp.get("error", None)
        # if error_code == 10014:
        #     self.empty_coin = True
        # elif error_code == 10016:
        #     self.empty_base = True
        if resp.get("result", False):
            self.current_order_ids.append(resp.get("order_id"))
        del resp

    async def order_route(self):
        async for item in self.order_todo:  # type: Union[str, OrderData]
            if isinstance(item, str):
                await self.cancel_order(custom_id=item)
            else:
                if self.SIGN:
                    continue
                await self.create_order(item=item)
                await sleep(1)

    async def stop_stg(self, send_msg: bool = True):
        conn = await self.redis_pool_db0.open()
        if send_msg and self.conf.team == "jx":
            await conn.publish(
                channel=Configure.REDIS.send_mail_channel,
                message={
                    "title": f"策略异常推送: {self.symbol.upper()}",
                    "content": f"""
                    <p>最近2小时成交额超限({self.trade_limit})</p>
                    <p>请人工介入</p>
                    """,
                    "receivers": [
                        "junxiang@lbk.one", "bingui.qin@lbk.one", "zhiwei.chen@lbk.one", "chao.lu@lbk.one",
                        "tianhua.lu@lbk.one", "pengfei.fan@lbk.one", "yue.li@lbk.one",
                    ]
                }
            )
        await conn.publish(
            channel=f"{self.exchange.upper()}_STG_WS_DB",
            message={"todo": "warning", "symbol": self.symbol}
        )
        await conn.close()
        del conn

    async def check_trade_size_from_rest(self):
        ft = MyDatetime.timestamp() - 60 + self.hr8_sec
        st = ft - self.hr2_sec
        data: dict = await self.api.query_trans_history(
            symbol=self.symbol, start_time=str(st), final_time=str(ft), limit=1000
        )
        trans_lst: list = data.get("trans_lst", [])
        if isinstance(trans_lst, str):
            log.info(f"最近 2hour 成交查询: {trans_lst}")
            return
        else:
            bid, ask = 0, 0
            for trade in trans_lst:  # type: dict
                if trade["type"] == "sell":
                    ask += trade["quoteQty"]
                else:
                    bid += trade["quoteQty"]
            # trade_amount = bid - ask
            trade_amount = bid
            del bid, ask
        log.info(f"最近 2hour 成交额: {trade_amount}")
        if trade_amount > self.trade_limit:
            self.SIGN = True
            if self.order_uuid2data:
                await self.api.cancel_all_orders(symbol=self.symbol)
            await self.stop_stg()
            log.info(f"最近 2hour 成交额大于 {self.trade_limit}, 当前: {trade_amount}, 暂停策略")
        del ft, st, data, trans_lst, trade_amount

    async def check_trade_size_from_redis(self):
        try:
            conn = await self.redis_pool_db1.open()
            data: dict = await conn.hget(f"{self.exchange.upper()}-TRADE-{self.symbol}", key="trade_size")
            bid: float = data.get("bid_size", 0)
            # ask: float = data.get("bid_size", 0)
            log.info(f"最近 2hour 成交额: {bid}")
            if bid > self.trade_limit:
                self.SIGN = True
                if self.order_uuid2data:
                    await self.api.cancel_all_orders(symbol=self.symbol)
                await self.stop_stg()
                log.info(f"最近 2hour 成交额大于 {self.trade_limit}, 当前: {bid}, 暂停策略")
            del bid
        except Exception as e:
            log.warning(f"check_trade_size_from_redis, err: {e}")

    async def on_current_orders(self):
        conn = await self.redis_pool_db0.open()
        await conn.hset(name=self.name_stg, key=f"order_ids_{self.symbol}", value={"orderIds": self.current_order_ids})
        await conn.close()
        del conn

    async def on_status(self, first_time: bool = False):
        if not self.is_connected:
            return
        conn = await self.redis_pool_db0.open()
        now = MyDatetime.today()
        if first_time:
            self.status_value["start_time"] = MyDatetime.dt2ts(now, thousand=True)
        self.status_value["upgrade_time"] = MyDatetime.dt2ts(now, thousand=True)
        self.status_value["upgrade_time_dt"] = MyDatetime.dt2str(now)
        await conn.hset(name=self.name_stg, key=f"fts_status_{self.symbol}", value=self.status_value)
        await conn.close()
        del conn, now
        log.info(f"更新策略状态: {self.status_value['upgrade_time_dt']}")

    async def refresh_sub_key(self):
        await self.api.refresh_subscribeKey(self.subscribe_key)

    async def change_orders(self):
        for odd in self.order_gear2data:  # type: OrderData
            self.order_uuid2data.pop(odd.customer_id, None)
            await self.order_todo.put(odd.customer_id)
            log.info(f"价格波动, 执行撤单, 档位: {odd.gear}")
            # await sleep(0.1)
            val = self.this_orderbook[odd.gear]
            odd.price = val["price"]
            odd.amount = val["amount"]
            await self.order_todo.put(odd)
            log.info(f"价格波动, 执行挂单, 档位 {odd.gear}")
            await sleep(0.1)

    async def relay_orders(self):
        """重新铺单"""
        current_length = len(self.current_order_ids)
        log.info(f"订单检查, 策略单量: {self.conf.order_nums * 2}, 当前单量: {current_length}")
        if self.conf.order_nums * 2 - current_length >= 5:
            log.info(f"订单丢失, 重启策略")
            conn = await self.redis_pool_db0.open()
            await conn.publish(
                channel=f"{self.exchange.upper()}_STG_WS_DB",
                message={"todo": "restart", "symbol": self.symbol}
            )
        del current_length

    def before_laying_orders(self):
        if not self.is_connected:
            return
        if not self.coin_balance:
            return
        if self.base_balance <= 700:
            self.conf.profit_rate *= 2
        elif self.base_balance <= 300:
            self.conf.profit_rate *= 4
        self.cal_func.conf = self.conf
        if not self.price_tick:
            return
        self.thisPrice = self.dex_price if self.dex_price not in [-1, 0] else self.cmc_price

    async def laying_orders_1st(self):
        """首次执行, 并赋值lastPrice"""
        self.before_laying_orders()
        log.info(f"{self.symbol.upper()}, 首次启动, 执行铺单")
        self.lastPrice = self.thisPrice
        self.this_orderbook = self.cal_func.cal_orderbook_volume(
            price=self.thisPrice,
            price_tick=self.price_tick,
            volume_tick=self.volume_tick,
            this_price=self.thisPrice,
            coin_balance=self.coin_balance,
            base_balance=self.base_balance
        )
        log.info(f"首次订单本: {self.this_orderbook}")
        for gear, v in sorted(self.this_orderbook.items()):  # 从内向外挂单
            trade_type = "buy" if gear > 0 else "sell"
            odd = OrderData(
                symbol=self.symbol,
                type=trade_type,
                price=v["price"],
                amount=v["volume"],
                customer_id=self.api.make_custom_id(custom=self.custom),
                gear=gear
            )
            self.order_gear2data[gear] = odd
            await self.order_todo.put(odd)
        self.last_orderbook = self.this_orderbook.copy()
        self.this_orderbook = {}

    async def laying_orders_2sec(self):
        """非首次执行"""
        self.before_laying_orders()
        if self.thisPrice == self.lastPrice:  # 若价格无变化，则不进行处理
            log.info(f"{self.symbol.upper()}, 价格暂无变化")
            return
        else:
            log.info(f"价格出现波动, 上次: {self.lastPrice}, 本次: {self.thisPrice}")
            self.this_orderbook = self.cal_func.cal_orderbook_volume(
                price=self.thisPrice,
                price_tick=self.price_tick,
                volume_tick=self.volume_tick,
                this_price=self.thisPrice,
                coin_balance=self.coin_balance,
                base_balance=self.base_balance
            )
            to_change = self.cal_func.cal_deviation(
                this_price=self.thisPrice,
                last_price=self.lastPrice,
                last_orderbook=self.this_orderbook
            )
            if to_change:
                log.info(f"价格波动较大, 执行挂撤")
                await self.change_orders()
        self.last_orderbook = self.this_orderbook.copy()
        self.this_orderbook = {}
        self.lastPrice = self.thisPrice

    async def random_orders(self):
        if not self.is_connected:
            return
        if self.random_count < 4:
            self.random_count += 1
            log.info(f"跳过随机撤单: {self.random_count} 次")
            return
        try:
            bid_gear, ask_gear = random.randint(1, self.conf.order_nums), -random.randint(1, self.conf.order_nums)
            odd_bid: OrderData = self.order_gear2data[bid_gear]
            odd_ask: OrderData = self.order_gear2data[ask_gear]

            self.temp_uuid[odd_bid.order_id] = bid_gear
            await self.order_todo.put(odd_bid.customer_id)
            log.info(f"定期随机挂撤, 档位: {bid_gear}, {odd_bid}")

            self.temp_uuid[odd_ask.order_id] = ask_gear
            await self.order_todo.put(odd_ask.customer_id)
            log.info(f"定期随机挂撤, 档位: {ask_gear}, {odd_ask}")
        except Exception as e:
            log.error(f"定期随机挂撤, 异常: {e}")

    async def on_order(self, data: dict):
        customer_id = data.get("customerID", "")
        if not customer_id.startswith(self.custom):
            del customer_id
            return
        order_data = self.order_uuid2data.get(customer_id, None)
        if not order_data:
            del order_data, customer_id
            return
        order_data.order_id = data["uuid"]
        order_data.customer_id = customer_id
        order_data.direction = data["type"]
        order_data.price = float(data["orderPrice"])
        order_data.amount = float(data["orderAmt"])
        order_data.traded = float(data["accAmt"]) * float(data["avgPrice"])
        order_data.status = self.order_status[str(data["orderStatus"])]
        order_data.datetime = int(data["updateTime"])

        # 更新订单本
        self.order_uuid2data[order_data.customer_id] = order_data
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
                order_data.customer_id = self.api.make_custom_id(custom=self.custom)
                await self.order_todo.put(order_data)
                log.info(f"补单: {order_data}")
            log.info(f"全部成交单: {order_data.type}, 原单: {order_data}")

        if order_data.status == Status.CANCELLED:
            # 策略执行的随机撤单
            if order_data.order_id in self.temp_uuid.keys():
                order_data.customer_id = self.api.make_custom_id(custom=self.custom)
                await self.order_todo.put(order_data)
                try:
                    del self.temp_uuid[order_data.order_id]
                except KeyError:
                    pass
                log.info(f"随机撤单: {order_data.type}, 原单: {order_data}")
            # 策略执行的主动撤单
            else:
                log.info(f"主动撤单: {order_data.type}, 原单: {order_data}")

        # 缓存订单记录
        conn = await self.redis_pool_db0.open()
        await conn.publish(channel="TradeCacheLBK", message=order_data.to_dict())
        await conn.close()
        await self.on_status()

        del conn, customer_id

    async def on_ping(self, data: dict):
        log.info(f"ping: {data}")
        await self.send_packet({"action": "pong", "pong": data["ping"]})

    async def on_packet(self, item: dict):
        # log.info(f"packet: {item}")
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

    async def on_connected(self):
        await self.send_packet({
            "action": "subscribe",
            "subscribe": "orderUpdate",
            "subscribeKey": self.subscribe_key,
            "pair": self.symbol
        })

    async def on_timer(self):
        # register
        schedule.every().hours.at(":00").do(lambda: self.loop.add_callback(self.get_tick_from_redis))
        schedule.every().minutes.at(":00").do(lambda: self.loop.add_callback(self.check_trade_size_from_rest))
        schedule.every().minutes.at(":00").do(lambda: self.loop.add_callback(self.check_trade_size_from_redis))
        schedule.every().minutes.at(":00").do(lambda: self.loop.add_callback(self.on_status))
        schedule.every(interval=5).seconds.do(lambda: self.loop.add_callback(self.get_price_from_redis))
        schedule.every(interval=1).seconds.do(lambda: self.loop.add_callback(self.on_current_orders))
        schedule.every(interval=10).seconds.do(lambda: self.loop.add_callback(self.laying_orders_2sec))
        schedule.every(interval=15).seconds.do(lambda: self.loop.add_callback(self.random_orders))
        schedule.every(interval=25).minutes.do(lambda: self.loop.add_callback(self.refresh_sub_key))
        schedule.every(interval=5).minutes.do(lambda: self.loop.add_callback(self.relay_orders))
        # start
        while True:
            if not self.is_connected:
                log.info("等待websocket连接")
                await sleep(1)
                continue
            schedule.run_pending()
            await sleep(1)

    async def initialize(self):
        await self.get_conf_from_redis()            # 获取配置信息, 一次性
        await self.init_by_exchange()               # 初始化API, 一次性
        await sleep(0.5)
        await self.check_last_open_orders()         # 检查上次残留订单, 一次性
        await self.check_trade_size_from_rest()     # 检查最近2hour成交额, 1min/次
        await self.check_trade_size_from_redis()    # 同上
        await self.check_params()                 # 检查参数

        # subscribe_key
        log.info("连接 websocket")
        data = await self.api.query_subscribeKey()
        log.info(f"subscribe_key: {data}")
        self.subscribe_key = data.get("key", None)
        del data

    async def on_first(self):
        while True:
            if not self.is_connected:
                log.info("等待websocket连接")
                await sleep(1)
                continue
            log.info("首次执行")
            await self.on_status(first_time=True)       # 设置策略状态, 1min/次
            await self.get_tick_from_redis()            # 获取精度数据, 1hour/次
            await self.get_price_from_redis()           # 获取最新价格, 5sec/次
            await self.laying_orders_1st()              # 铺单
            break

    def run(self):
        log.info("\n\n\n\n\n\n")
        log.info(f"启动策略: {MyDatetime.dt2str(MyDatetime.add8hr())}")
        self.loop.run_sync(self.initialize)
        self.loop.add_callback(self.on_first)
        self.loop.add_callback(self.on_timer)
        self.loop.add_callback(self.order_route)
        self.loop.add_callback(lambda: self.subscribe(self.wss_url))
        self.loop.start()


if __name__ == '__main__':
    define(name="server", type=str, default="main")
    define(name="symbol", type=str, default="artm_usdt")
    define(name="exchange", type=str, default="lbk")

    options.parse_command_line()

    FollowTickTemplate().run()
