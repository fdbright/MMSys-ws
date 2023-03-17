# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/17 13:15

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import tornado.web
import tornado.ioloop
import tornado.httpserver
from tornado.options import define, options

from App import Login
from Route import V1MainRoute
from Utils import MyRedis
from Config import Configure

mr = MyRedis(db=0)
define("redis", default=mr)
define("port", default=12270, help="run on the given port", type=int)
options.parse_command_line()

log.add(Configure.LOG_MAIN, retention="2 days", encoding="utf-8")

urls = [
    ("/app/wss/v1", V1MainRoute),
    ("/app/htp/v1/user/login", Login),
]
app = tornado.web.Application(
    urls,
    debug=True,
    # websocket_ping_interval=5,  # 间隔5秒发送一次ping帧，第一次发送为触发的5s后
    # websocket_ping_timeout=60,  # 每次 ping 操作重置时间超时时间，若超时则断开连接，默认3次 ping 或 30s 断开
)

httpserver = tornado.httpserver.HTTPServer(app)
httpserver.listen(options.port)

if __name__ == '__main__':
    log.info(f"启动服务: 127.0.0.1:{options.port}")
    tornado.ioloop.IOLoop.current().start()
