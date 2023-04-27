# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 21:06

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import Union, Tuple

import time
import hmac
import ujson
import random
import hashlib
import numpy as np
from _md5 import md5

from Utils import MyDatetime
from Config.urls import LBKUrl
from Template import MyApiTemplate
from Objects import (
    Request,
    ErrorCodeReturn, ServerTsReturn, TickReturn,
    ContractInfo, ContractReturn,
    DepthReturn,
    AccountInfo, AccountReturn,
    OrderInfo, OpenOrderReturn,
    CreateOrderReturn, CancelOrderReturn,
    TransInfo, TransHistoryReturn,
    SubscribeKeyReturn
)


class LbkRestApi(MyApiTemplate):

    def __init__(self, htp_client=None, api_key: str = None, secret_key: str = None):
        super().__init__()
        self.__exchange = "lbk"
        self.htp_client = htp_client
        self.api_key = api_key
        self.secret_key = secret_key

        self.order_count_limit: int = 5000    # 下单金额限制

        self.url = LBKUrl.API

        self.__headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "timestamp": "",
            "signature_method": "HmacSHA256",
            "echostr": "df28a1e9895052608c2a6897f13d5659"
        }

        self.__order_type: dict = {"buy": "buy", "sell": "sell"}
        self.__order_status: dict = {
            "-1": "已撤销", "0": "未成交", "1": "部分成交", "2": "完成成交", "3": "部分成交已撤销", "4": "撤单处理中"
        }

    def __sign(self, request: Request) -> Request:
        """生成签名"""
        ts = int(time.time() * 1000)
        params: dict = request.params.copy()
        params["echostr"] = "df28a1e9895052608c2a6897f13d5659"
        params["signature_method"] = "HmacSHA256"
        params["timestamp"] = str(ts)
        query: list = []
        for k, v in sorted(params.items()):
            query.append(k + "=" + str(v))
        query: str = '&'.join(query)
        md5_str: str = md5(query.encode("utf-8")).hexdigest().upper()
        signature: str = hmac.new(request.secretKey.encode(), md5_str.encode("utf-8"), hashlib.sha256).hexdigest()
        request.headers = self.__headers.copy()
        request.headers["timestamp"] = str(ts)
        request.params["sign"] = signature
        request.data = {}
        return request

    def __check_response(self, response: dict) -> Union[bool, ErrorCodeReturn]:
        if response and response["result"] in ["true", True]:
            res = True
        else:
            res = ErrorCodeReturn(
                exchange=self.__exchange,
                error=response.get("error_code", "发起请求失败")
            )
        return res

    async def __send_request(self, method: str, api: str, params: dict = None, sign: bool = False) -> Tuple[dict, Union[bool, ErrorCodeReturn]]:
        if params is not None:
            if sign:
                params["api_key"] = self.api_key
                req = Request(
                    method=method, host=LBKUrl.HOST.rest, api=api,
                    params=params, apiKey=self.api_key, secretKey=self.secret_key
                )
            else:
                req = Request(method=method, host=LBKUrl.HOST.rest, params=params, api=api)
        else:
            req = Request(method=method, host=LBKUrl.HOST.rest, api=api)
        if sign:
            req = self.__sign(req)
        resp: dict = await self.get_response(req)
        data = self.__check_response(resp)
        return resp, data

    async def query_timestamp(self) -> dict:
        resp, data = await self.__send_request(self.get, self.url.QUERY_TIME, sign=False)
        if data is True:
            data = ServerTsReturn(
                exchange=self.__exchange,
                timestamp=int(resp.get("data", -1))
            )
        return data.to_dict()

    async def query_tick(self, symbol: str = None) -> dict:
        params = {
            "symbol": symbol.lower() if symbol else "all"
        }
        resp, data = await self.__send_request(self.get, self.url.QUERY_TICK, params, sign=False)
        if data is True:
            data = TickReturn(
                exchange=self.__exchange
            )
            tick_data = resp["data"]
            if len(tick_data) == 1:
                data.all = False
                data.symbol = symbol
                data.latest = float(tick_data[0].get("ticker", {}).get("latest", -1))
            else:
                data.all = True
                data.ticker = {v["symbol"]: float(v.get("ticker", {}).get("latest", -1)) for v in tick_data}
        return data.to_dict()

    def __init4contract(self, row: dict) -> dict:
        return ContractInfo(
            symbol=row["symbol"].lower(),
            priceTick=int(row["priceAccuracy"]),
            amountTick=int(row["quantityAccuracy"]),
            minVol=float(row["minTranQua"])
        ).to_dict()

    async def query_contract(self) -> dict:
        resp, data = await self.__send_request(self.get, self.url.QUERY_CONTRACT, sign=False)
        if data is True:
            contract = list(map(self.__init4contract, resp["data"]))
            data = ContractReturn(
                exchange=self.__exchange,
                contract_dict={row["symbol"]: row for row in contract}
            )
        return data.to_dict()

    def __init4depth(self, row: list) -> list:
        r1, r2 = float(row[0]), float(row[1])
        return [r1, r2, r1 * r2]

    async def query_depth(self, symbol: str, limit: int = 100) -> dict:
        params = {
            "symbol": symbol.lower(),
            "limit": str(limit)
        }
        resp, data = await self.__send_request(self.get, self.url.QUERY_DEPTH, params, sign=False)
        if data is True:
            data = DepthReturn(
                exchange=self.__exchange,
                asks=list(map(self.__init4depth, resp["asks"])),
                bids=list(map(self.__init4depth, resp["bids"]))
            )
        return data.to_dict()

    def __init4account(self, row: dict) -> Union[dict, None]:
        symbol = row["asset"].upper()
        free = float(row["free"])
        frozen = float(row["locked"])
        balance = free + frozen
        if free == 0 and frozen == 0:
            return None
        return AccountInfo(symbol=symbol, free=free, frozen=frozen, balance=balance).to_dict()

    async def query_account_info(self, to_dict: bool = False) -> dict:
        resp, data = await self.__send_request(self.post, self.url.QUERY_USERINFO_ACCOUNT, {}, sign=True)
        # log.info(str(resp))
        if data is True:
            res = list(filter(lambda x: x, map(self.__init4account, resp.get("data", {}).get("balances", []))))
            if to_dict:
                res = {v["symbol"]: v for v in res}
            data = AccountReturn(
                exchange=self.__exchange,
                account_lst=res
            )
        return data.to_dict()

    def __init4orders(self, row: dict) -> dict:
        return OrderInfo(
            symbol=row["symbol"],
            type=row["type"],
            price=float(row["price"]),
            amount=float(row["origQty"]),
            deal_price=float(row["cummulativeQuoteQty"]) / (float(row["executedQty"]) or 1),
            deal_amount=float(row["executedQty"]),
            order_id=row["orderId"],
            custom_id=row.get("clientOrderId", ""),
            status=self.__order_status.get(str(row["status"])),
            create_time=MyDatetime.ts2str(row["time"], chz=True),
            update_time=MyDatetime.ts2str(row["updateTime"], chz=True)
        ).to_dict()

    async def query_open_orders(self, symbol: str = None, page: int = None, per_page: int = None) -> dict:
        params = {
            "symbol": symbol,
            "current_page": int(page) if page else 1,
            "page_length": int(per_page) if per_page else 200
        }
        resp, data = await self.__send_request(self.post, self.url.QUERY_OPEN_ORDERS, params, sign=True)
        if data is True:
            orders = resp.get("data", {}).get("orders", [])
            data = OpenOrderReturn(
                exchange=self.__exchange,
                order_lst=list(map(self.__init4orders, orders)) if orders else [],
            )
        return data.to_dict()

    async def create_order(self, symbol: str, _type: str, price: float, amount: float, custom_id: str, conf: dict) -> dict:
        ck = await self.check_order_conf(conf)
        if ck:
            price_tick, min_volume, volume_tick = ck
        else:
            return ErrorCodeReturn(exchange=self.__exchange, error="缺少精度参数").to_dict()
        # id_num = self.get_order_ids()
        price = round(price, price_tick)
        amount = round(amount, volume_tick)
        if amount < min_volume:
            return ErrorCodeReturn(exchange=self.__exchange, error="下单数量小于最小限制").to_dict()
        if price * amount > self.order_count_limit:
            return ErrorCodeReturn(exchange=self.__exchange, error="下单金额超过限制(5000)").to_dict()
        params = {
            "symbol": symbol,
            "type": self.__order_type[_type.lower()],
            "price": price,
            "amount": amount,
            "custom_id": custom_id
        }
        # print(params)
        resp, data = await self.__send_request(self.post, self.url.CREATE_ORDER, params, sign=True)
        if data is True:
            data = CreateOrderReturn(
                exchange=self.__exchange,
                order_id=resp.get("data", {}).get("order_id"),
                custom_id=custom_id,
                result=True
            )
        return data.to_dict()

    async def create_order_batch(
            self,
            symbol: str,
            _type: str,
            start_price: float,
            final_price: float,
            order_num: int,
            order_amount: float,
            random_index: float,
            custom_id: str,
            conf: dict
    ) -> dict:
        ck = await self.check_order_conf(conf)
        if ck:
            price_tick, min_volume, volume_tick = ck
        else:
            return ErrorCodeReturn(exchange=self.__exchange, error="缺少精度参数").to_dict()
        random_index: float = random.uniform(0, 1) if abs(random_index) > 1 or random_index == 0 else random_index
        order_type = self.__order_type[_type.lower()]
        price_array = np.linspace(start_price, final_price, order_num)
        mid: list = []
        for index, price in enumerate(price_array, 1):
            # id_num = self.get_order_ids(order_count=index)
            price = round(price, price_tick)
            amount = order_amount * random.uniform(1 - random_index, 1 + random_index)
            amount = round(amount, volume_tick)
            if price * amount < self.order_count_limit and amount > min_volume:
                params = {
                    "symbol": symbol,
                    "type": order_type,
                    "price": price,
                    "amount": amount,
                    "customer_id": custom_id + str(index)
                }
                mid.append(params)
        params = {
            "orders": ujson.dumps(mid)
        }
        resp, data = await self.__send_request(self.post, self.url.CREATE_BATCH_ORDERS, params, sign=True)
        if data is True:
            data = CreateOrderReturn(
                exchange=self.__exchange,
                order_id="",
                result=True
            )
        return data.to_dict()

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        resp, data = await self.__send_request(self.post, self.url.CANCEL_ORDER, params, sign=True)
        if data is True:
            data = CancelOrderReturn(exchange=self.__exchange, result=True)
        return data.to_dict()

    async def cancel_all_orders(self, symbol: str) -> dict:
        params = {
            "symbol": symbol,
        }
        resp, data = await self.__send_request(self.post, self.url.CANCEL_ORDER_BY_SYMBOL, params, sign=True)
        if data is True:
            data = CancelOrderReturn(exchange=self.__exchange, result=True)
        elif resp.get("error_code") == 10004:
            data = CancelOrderReturn(exchange=self.__exchange, result="正在撤单中")
        return data.to_dict()

    def __init4trans(self, row: dict, price_tick: int, volume_tick: int) -> dict:
        return TransInfo(
            symbol=row["symbol"],
            type="buy" if row["isBuyer"] else "sell",
            price=round(float(row["price"]), price_tick),
            amount=round(float(row["qty"]), volume_tick),
            quoteQty=round(float(row["quoteQty"]), price_tick),
            fee=float(row["commission"]),
            fee_asset=None,
            order_id=row["orderId"],
            trade_time=MyDatetime.ts2str(row["time"], chz=True)
        ).to_dict()

    async def query_trans_history(
            self, symbol: str = None, start_time: str = None, final_time: str = None, limit: int = 100,
            price_tick: int = 18, volume_tick: int = 2
    ) -> dict:
        params = {
            "symbol": symbol,
            "limit": limit
        }
        if start_time:
            params["startTime"] = MyDatetime.ts2str(start_time, thousand=False)
        if final_time:
            params["endTime"] = MyDatetime.ts2str(final_time, thousand=False)
        resp, data = await self.__send_request(self.post, self.url.QUERY_TRANSACTION_ORDERS, params, sign=True)
        if data is True:
            history = resp.get("data", [])
            if history:
                res = list(sorted(map(lambda x: self.__init4trans(x, price_tick, volume_tick), history), key=lambda x: x["trade_time"], reverse=True))
            else:
                res = []
            data = TransHistoryReturn(
                exchange=self.__exchange,
                trans_lst=res
            )
        return data.to_dict()

    async def query_subscribeKey(self) -> dict:
        params = {
            "api_key": self.api_key
        }
        resp, data = await self.__send_request(self.post, self.url.QUERY_SUB_KEY, params, sign=True)
        if data is True:
            data = SubscribeKeyReturn(
                exchange=self.__exchange,
                key=resp["data"]
            )
        return data.to_dict()

    async def refresh_subscribeKey(self, subscribe_key: str) -> dict:
        params = {
            "subscribeKey": subscribe_key
        }
        resp, data = await self.__send_request(self.post, self.url.QUERY_REFRESH_SUB_KEY, params, sign=True)
        if data is True:
            data = SubscribeKeyReturn(
                exchange=self.__exchange,
                key=""
            )
        return data.to_dict()

    async def close_subscribeKey(self, subscribe_key: str) -> dict:
        params = {
            "subscribeKey": subscribe_key
        }
        resp, data = await self.__send_request(self.post, self.url.CLOSE_SUB_KEY, params, sign=True)
        if data is True:
            data = SubscribeKeyReturn(
                exchange=self.__exchange,
                key=""
            )
        return data.to_dict()


if __name__ == '__main__':
    pass
