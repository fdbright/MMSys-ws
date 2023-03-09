# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 21:08

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union
from loguru import logger as log

import json
import urllib.parse as up
from asyncio import Lock
from tornado.httpclient import HTTPRequest, AsyncHTTPClient

from Objects import Request


class MyApiTemplate:

    def __init__(self):
        self.get = "GET"
        self.post = "POST"
        self.put = "PUT"
        self.delete = "DELETE"
        self.order_count_lock = Lock()

    @staticmethod
    async def get_response(htp_client: AsyncHTTPClient, req: Request) -> Union[dict, list]:
        """异步请求"""
        if req.params:
            path = req.host + req.api + "?" + up.urlencode(sorted(req.params.items()))
        else:
            path = req.host + req.api
        request = HTTPRequest(
            url=path,
            method=req.method.upper(),
            headers=req.headers,
            body=json.dumps(req.data) if req.data else None,
            allow_nonstandard_methods=True,
        )
        try:
            log.info(f"url: {request.url}")
            resp = await htp_client.fetch(request)
            resp = json.loads(resp.body.decode(errors="ignore"))
        except Exception as e:
            log.error(f"请求失败, url: {request.url}, err: {e}")
            resp = {}
        log.info(req)
        # log.info(resp)
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

    async def query_account_info(self) -> dict:
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

    async def get_order_ids(self, order_count: int = 1) -> str:
        """获取订单ID"""
        with self.order_count_lock:
            return str(order_count + 1)

    async def create_order(self, symbol: str, _type: str, price: float, amount: float, conf: dict) -> dict:
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

    def __init4trans(self, row: dict) -> dict:
        raise NotImplementedError

    async def query_trans_history(
            self, symbol: str = None, start_time: str = None, final_time: str = None, limit: int = None
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

