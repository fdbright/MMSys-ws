# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 17:41

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import asyncio
import tornado.web
import tornado.ioloop
import tornado.httpserver
from tornado.options import define

from App import Login
from Config import Configure
from Utils import MyRedis

mr = MyRedis(db=0)
define("redis", default=mr)


class Main:

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.urls = [
            ("/app/v1/user/login", Login),
        ]
        log.add(Configure.HTTP.log_path, retention="2 days", encoding="utf-8")

    async def admin(self, host, port):
        app = tornado.web.Application(self.urls, debug=self.debug)
        app.listen(address=host, port=port)
        await asyncio.Event().wait()

    def run(self, host, port):
        log.info(f"启动服务: {host}:{port}")
        asyncio.run(self.admin(host=host, port=port))


if __name__ == '__main__':
    Main(debug=True).run(host=Configure.HTTP.host, port=Configure.HTTP.port)
