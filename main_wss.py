# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 17:41

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import asyncio
import tornado.web
from tornado.options import define

from Route import V1MainRoute
from Utils import MyRedis
from Config import Configure

mr = MyRedis(db=0)
define("redis", default=mr)


class Main:

    def __init__(self, debug=False):
        self.debug = debug
        self.urls = [
            ("/app/ws/v1", V1MainRoute),
        ]
        log.add(Configure.WSS.log_path, retention="2 days", encoding="utf-8")

    def mkApp(self):
        return tornado.web.Application(
            self.urls,
            debug=self.debug,
            # websocket_ping_interval=5,  # 间隔5秒发送一次ping帧，第一次发送为触发的5s后
            # websocket_ping_timeout=60,  # 每次 ping 操作重置时间超时时间，若超时则断开连接，默认3次 ping 或 30s 断开
        )

    async def admin(self, host, port):
        app = self.mkApp()
        app.listen(address=host, port=port)
        await asyncio.Event().wait()

    def run(self, host, port):
        log.info(f"启动服务: {host}:{port}")
        asyncio.run(self.admin(host=host, port=port))


if __name__ == '__main__':
    Main(debug=True).run(host=Configure.WSS.host, port=Configure.WSS.port)
