# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 14:58

from loguru import logger as log

import json
from datetime import timedelta
from tornado.ioloop import PeriodicCallback
from aiohttp import ClientSession

from Webs import MyWssMethod
from Utils.myEncoder import MyEncoder
from Utils import MyDatetime, MyRedisFunction
from Objects import UserObj
from Config import Configure

from App.user import \
    Admin, AdminItem, \
    Operate, OperateItem
from App.market import \
    Coins, CoinsItem, \
    Account, AccountItem, \
    Report, ReportItem, \
    Strategy, StrategyItem
from App.monitor import \
    Depth, DepthItem, \
    Order, OrderItem, \
    Trade, TradeItem, \
    Balance, BalanceItem


class V1MainRoute(MyWssMethod):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis: MyRedisFunction = None

    def prepare(self):
        self.redis = self.redis_pool.open(conn=True)

    async def open(self):
        self.set_nodelay(True)  # 设置无延迟
        # log.info(f"建立连接=[{self.current_user.username}]-[{MyDatetime.now2str()}]")

    def on_close(self):
        self.redis.close()
        try:
            if "monitor.depth" in self.current_user.channel_dict.keys():
                msg = {
                    "action": "unsubscribe",
                    "subscribe": "depth",
                    "depth": "50",
                    "pair": self.current_user.channel_dict["monitor.depth"][-1]["symbol"],
                }
                self.redis.pub2channel(channel=Configure.REDIS.wss_channel_lbk, msg=msg)
            self.stop_event()
            if self.current_user.on_timer.is_running():
                self.current_user.on_timer.stop()
            # await self.current_user.http_client.close()
            log.info(f"关闭连接=[{self.current_user.username}]-[{MyDatetime.now2str()}]")
        except AttributeError:
            pass

    async def on_message(self, message):
        """
        message = {
            "action": "close" | "rest" | "subscribe" | "unsubscribe",
            "method": "GET" | "POST" | "PUT" | "DELETE" | None,
            "channel": "user.{}" | "market.{}" | "monitor.{}",
            "token_id": "",
            ...
        }
        """
        try:
            item: dict = json.loads(message)
            # log.info(f"{type(item)}, {item}")
            action: str = item.get("action", "").lower()
            if action == "ping":
                self.after_request(code=1, msg="连接状态检查", data={"pong": MyDatetime.timestamp()})
                return
            if not self.current_user:
                await self.on_verify(item)
            if action == "close":
                self.close()
            elif action == "rest":
                await self.on_rest(item=item)
            elif action == "subscribe":
                await self.on_subscribe(item=item)
            elif action == "unsubscribe":
                await self.on_unsubscribe(item=item)
            else:
                self.after_request(code=-1, msg="缺少参数: action")
        except Exception as e:
            log.warning(f"on_message 异常: {e}")

    async def on_timer(self):
        """定时检查websocket连接状态"""
        if self.ws_connection is None or self.ws_connection.is_closing():
            await self.current_user.http_client.close()
            self.close()
        log.info(f"定时检查=[{self.current_user.username}]-[{MyDatetime.now2str()}]")

    async def on_verify(self, item: dict):
        token = self.redis.get(f"tokenID_{item.get('token_id', None)}")
        if not token:
            self.after_request(code=-1, msg="登陆过期", action="verify")
            self.close()
        else:
            self.current_user = UserObj(**MyEncoder.byJWT(Configure.SECRET_KEY).decode(token))
            self.current_user.http_client = ClientSession(trust_env=True)
            self.current_user.event_dict = {}
            self.current_user.channel_dict = {}
            self.current_user.on_timer = PeriodicCallback(
                callback=self.on_timer, callback_time=timedelta(seconds=10), jitter=0.2
            )
            self.current_user.on_timer.start()
            log.info(f"验证通过=[{self.current_user.username}]-[{MyDatetime.now2str()}]")
            self.after_request(code=200, msg="验证通过", action="verify")

    async def on_rest(self, item: dict):
        """rest请求"""
        # log.info(item)
        channel: str = item.get("channel", None)
        if channel.startswith("user"):
            if channel.endswith("admin"):
                action, obj = Admin, AdminItem
            elif channel.endswith("operate"):
                action, obj = Operate, OperateItem
            else:
                self.after_request(code=-1, msg=f"不支持的参数: channel, {channel}", action=channel)
                return
        elif channel.startswith("market"):
            if channel.endswith("coins"):
                action, obj = Coins, CoinsItem
            elif channel.endswith("account"):
                action, obj = Account, AccountItem
            elif channel.endswith("report"):
                action, obj = Report, ReportItem
            elif channel.endswith("strategy"):
                action, obj = Strategy, StrategyItem
            else:
                self.after_request(code=-1, msg=f"不支持的参数: channel, {channel}", action=channel)
                return
        elif channel.startswith("monitor"):
            if channel.endswith("order"):
                action, obj = Order, OrderItem
            elif channel.endswith("trade"):
                action, obj = Trade, TradeItem
            elif channel.endswith("balance"):
                action, obj = Balance, BalanceItem
            else:
                self.after_request(code=-1, msg=f"不支持的参数: channel, {channel}", action=channel)
                return
        else:
            self.after_request(code=-1, msg="缺少参数: channel", action=channel)
            return
        act = action(redis=self.redis, after_request=self.after_request, current_user=self.current_user)
        await act.do_job(obj=obj, item=item)
        try:
            del channel, action, obj
        except NameError:
            pass

    async def on_subscribe(self, item: dict):
        """启动订阅"""
        item["method"] = "GET"
        channel: str = item.get("channel", None)
        if channel in self.current_user.event_dict.keys():
            self.after_request(code=-1, msg=f"重复订阅: {channel}", action=channel)
            return
        if channel.startswith("market"):
            if channel.endswith("coins"):
                action, obj, dt = Coins, CoinsItem, timedelta(seconds=5)
            elif channel.endswith("strategy"):
                action, obj, dt = Strategy, StrategyItem, timedelta(seconds=1)
            # elif channel.endswith("account"):
            #     action, obj, dt = Account, AccountItem, timedelta(seconds=5)
            else:
                self.after_request(code=-1, msg=f"不支持的参数: channel, {channel}", action=channel)
                return
        elif channel.startswith("monitor"):
            if channel.endswith("depth"):
                msg = {
                    "action": "subscribe",
                    "subscribe": "depth",
                    "depth": "50",
                    "pair": item["symbol"],
                }
                self.redis.pub2channel(channel=Configure.REDIS.wss_channel_lbk, msg=msg)
                action, obj, dt = Depth, DepthItem, timedelta(milliseconds=500)
            elif channel.endswith("order"):
                action, obj, dt = Order, OrderItem, timedelta(seconds=2)
            elif channel.endswith("trade"):
                action, obj, dt = Trade, TradeItem, timedelta(seconds=10)
            elif channel.endswith("balance"):
                action, obj, dt = Balance, BalanceItem, timedelta(seconds=2)
            else:
                self.after_request(code=-1, msg=f"不支持的参数: channel, {channel}", action=channel)
                return
        else:
            self.after_request(code=-1, msg="缺少参数: channel", action=channel)
            return
        act = action(redis=self.redis, after_request=self.after_request, current_user=self.current_user)
        await act.do_job(obj, item)
        self.current_user.event_dict[channel] = PeriodicCallback(
            callback=lambda: act.do_job(obj, item.copy()),
            callback_time=dt,
            jitter=0.2
        )
        self.current_user.channel_dict[channel] = [act, obj, item]
        self.start_event()

    async def on_unsubscribe(self, item: dict):
        """关闭订阅"""
        channel: str = item.get("channel", None)
        if channel.startswith("market"):
            p = self.current_user.event_dict.get(channel, None)
        elif channel.startswith("monitor"):
            if channel.endswith("depth"):
                msg = {
                    "action": "unsubscribe",
                    "subscribe": "depth",
                    "depth": "50",
                    "pair": item["symbol"],
                }
                self.redis.pub2channel(channel=Configure.REDIS.wss_channel_lbk, msg=msg)
            p = self.current_user.event_dict.get(channel, None)
        else:
            self.after_request(code=-1, msg="缺少参数: channel", action=channel)
            return
        if p and p.is_running():
            p.stop()
        try:
            del self.current_user.event_dict[channel]
            del self.current_user.channel_dict[channel]
            del channel, p, msg
        except NameError:
            pass


if __name__ == '__main__':
    pass
