# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 21:08

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union
from loguru import logger as log

import uuid
import ujson
from aiohttp import ClientSession, ClientResponse

from Objects import Request


class MyApiTemplate:

    def __init__(self):
        self.get = "GET"
        self.post = "POST"
        self.put = "PUT"
        self.delete = "DELETE"
        self.htp_client: ClientSession = None

    async def get_response(self, req: Request) -> Union[dict, list]:
        """异步请求"""
        if req.params:
            query: list = []
            for k, v in sorted(req.params.items()):
                query.append(k + "=" + str(v))
            query: str = '&'.join(query)
            path = req.host + req.api + "?" + query
            req.params = {}
        else:
            path = req.host + req.api
        cr: ClientResponse = await self.htp_client.request(
            method=req.method,
            url=path,
            headers=req.headers,
            params=req.params,
            data=req.data,
        )
        try:
            # log.info(cr.url)
            status_code = cr.status
            resp: str = await cr.text()
            log.info(f"status_code: {status_code}")
            # log.info(f"text, type: {type(resp)} value: {resp}")
            try:
                resp: dict = ujson.loads(resp)
            except TypeError:
                pass
        except Exception as e:
            log.error(f"请求失败, url: {cr.url}, err: {e}")
            resp: dict = {}
        del cr
        return resp

    def __sign(self, request):
        """验签"""
        raise NotImplementedError

    def __check_response(self, response: dict):
        """校验response"""
        raise NotImplementedError

    async def __send_request(self, *args, **kwargs):
        """发送请求"""
        raise NotImplementedError

    async def query_timestamp(self) -> dict:
        """查询服务器时间"""
        raise NotImplementedError

    async def query_tick(self, symbol: str) -> dict:
        """查询币币行情"""
        raise NotImplementedError

    def __init4contract(self, row: dict) -> dict:
        raise NotImplementedError

    async def query_contract(self) -> dict:
        """查询币对信息"""
        raise NotImplementedError

    def __init4depth(self, row: list) -> list:
        raise NotImplementedError

    async def query_depth(self, symbol: str, limit: int = 100) -> dict:
        """查询深度信息"""
        raise NotImplementedError

    def __init4account(self, row: dict) -> dict:
        raise NotImplementedError

    async def query_account_info(self, to_dict: bool = False) -> dict:
        """查询账户信息"""
        raise NotImplementedError

    def __init4orders(self, row: dict) -> dict:
        raise NotImplementedError

    async def query_open_orders(self, symbol: str = None, page: int = None, per_page: int = None) -> dict:
        """查询当前挂单"""
        raise NotImplementedError

    @staticmethod
    async def check_order_conf(conf: dict) -> Union[bool, tuple]:
        """检查下单配置"""
        price_tick = int(conf.get("priceTick", -1))
        min_volume = float(conf.get("minVol", -1))
        volume_tick = int(conf.get("amountTick", -1))
        if -1 in [price_tick, min_volume, volume_tick]:
            return False
        else:
            return price_tick, min_volume, volume_tick

    @staticmethod
    def make_custom_id(custom: str = "") -> str:
        """
        生成自定义ID
        :param custom: 开始字符串
        """
        return custom + uuid.uuid4().hex[len(custom):] if custom else uuid.uuid4().hex

    async def create_order(self, symbol: str, _type: str, price: float, amount: float, custom: str, conf: dict) -> dict:
        """下单"""
        raise NotImplementedError

    async def create_order_batch(
            self,
            symbol: str,
            _type: str,
            start_price: float,
            final_price: float,
            order_num: int,
            order_amount: float,
            random_index: float,
            custom: str,
            conf: dict
    ) -> dict:
        """
        批量下单
        :param symbol: 币对
        :param _type: 方向, 买卖
        :param start_price: 价格下限
        :param final_price: 价格上限
        :param order_num: 下单档位量
        :param order_amount: 下单总数量
        :param random_index: 随机值
        :param custom: 订单前缀
        :param conf: 下单配置, 价格精度, 数量精度, 最小数量
        :return:
        """
        raise NotImplementedError

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """单一撤单"""
        raise NotImplementedError

    async def cancel_all_orders(self, symbol: str) -> dict:
        """全部撤单"""
        raise NotImplementedError

    def __init4trans(self, row: dict, price_tick: int, volume_tick: int) -> dict:
        raise NotImplementedError

    async def query_trans_history(
            self, symbol: str = None, start_time: str = None, final_time: str = None, limit: int = None,
            price_tick: int = None, volume_tick: int = None
    ) -> dict:
        """查询历史成交记录"""
        raise NotImplementedError

    async def query_subscribeKey(self) -> dict:
        """生成subscribeKey"""
        raise NotImplementedError

    async def refresh_subscribeKey(self, subscribe_key: str) -> dict:
        """延长subscribeKey有效期"""
        raise NotImplementedError

    async def close_subscribeKey(self, subscribe_key: str) -> dict:
        """关闭subscribeKey"""
        raise NotImplementedError


if __name__ == '__main__':
    pass

