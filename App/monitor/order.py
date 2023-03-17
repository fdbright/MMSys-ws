# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:22

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate
from Objects import OperateObj


@dataclass
class OrderItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    symbol: str = None
    exchange: str = "lbk"
    page: int = 1
    per_page: int = 200
    # 订单
    type: str = ""
    batch: bool = False
    price: float = 0
    start_price: float = 0
    final_price: float = 0
    order_num: int = 0
    order_amount: float = 0
    random_index: float = 0
    # 撤单
    order_ids: str = None


class Order(MyActionTemplate):

    async def get(self, item: OrderItem):
        """查询挂单"""
        if self.current_user.monOrder:
            api = self.get_rest_api_by_exchange(item.exchange, item.symbol)
            if api:
                data = await api.query_open_orders(item.symbol, page=item.page, per_page=item.per_page)
            else:
                data = None
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="查询挂单", action=item.channel, data=data)

    async def post(self, item: OrderItem):
        """下单"""
        if self.current_user.monOrder:
            conf: dict = self.redis.hGet(name=f"{item.exchange.upper()}-DB", key="contract_data").get(item.symbol, {})
            api = self.get_rest_api_by_exchange(item.exchange, item.symbol)
            if api:
                if item.batch:
                    data = await api.create_order_batch(
                        symbol=item.symbol,
                        _type=item.type,
                        start_price=float(item.start_price),
                        final_price=float(item.final_price),
                        order_num=int(item.order_num),
                        order_amount=float(item.order_amount),
                        random_index=float(item.random_index),
                        custom_id=api.make_custom_id(custom="MMsys"),
                        conf=conf
                    )
                else:
                    data = await api.create_order(
                        symbol=item.symbol,
                        _type=item.type,
                        price=float(item.price),
                        amount=float(item.order_amount),
                        custom_id=api.make_custom_id(custom="MMsys"),
                        conf=conf
                    )
                self.add_operation(operation=OperateObj(
                    username=self.current_user.username,
                    exchange=item.exchange,
                    symbol=item.symbol,
                    event=item.type
                ))
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
        if item.batch:
            msg = "批量下单"
        else:
            msg = "下单"
        self.after_request(code=code, msg=msg, action=item.channel, data=data)

    async def delete(self, item: OrderItem):
        """撤单"""
        if self.current_user.monOrder:
            api = self.get_rest_api_by_exchange(item.exchange, item.symbol)
            if api:
                if item.order_ids:
                    for order_id in item.order_ids.split(","):
                        data = await api.cancel_order(item.symbol, order_id)
                else:
                    data = await api.cancel_all_orders(item.symbol)
                self.add_operation(operation=OperateObj(
                    username=self.current_user.username,
                    exchange=item.exchange,
                    symbol=item.symbol,
                    event="撤单"
                ))
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
        if item.order_ids:
            if "," in item.order_ids:
                msg = "批量撤单"
            else:
                msg = "撤单"
        else:
            msg = "全部撤单"
        self.after_request(code=code, msg=msg, action=item.channel, data=data)


if __name__ == '__main__':
    pass
