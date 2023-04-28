# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/17 13:15

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import tornado.httpserver
from tornado.web import Application
from tornado.ioloop import IOLoop
from tornado.options import define, options
from tornado.routing import Rule, RuleRouter, PathMatches

from App import Login, ReportRest
from Route import V1MainRoute
from Utils import MyAioredis
from Config import Configure

define("redis_pool", default=MyAioredis(db=0))
define("port", default=12270, help="run on the given port", type=int)
options.parse_command_line()

log.add(Configure.LOG_MAIN, retention="2 days", encoding="utf-8")

htp_app = Application(
    [
        ("/app/htp/v1/user/login", Login),
        ("/app/htp/v1/report", ReportRest),
    ],
    debug=True
)
wss_app = Application(
    [
        ("/app/wss/v1", V1MainRoute),
    ],
    debug=True,
    # websocket_ping_interval=5,  # 间隔5秒发送一次ping帧，第一次发送为触发的5s后
    # websocket_ping_timeout=60,  # 每次 ping 操作重置时间超时时间，若超时则断开连接，默认3次 ping 或 30s 断开
)

router = RuleRouter([
    Rule(PathMatches("/app/htp/.*"), htp_app),
    Rule(PathMatches("/app/wss/.*"), wss_app),
])

httpserver = tornado.httpserver.HTTPServer(router)
httpserver.listen(options.port)

if __name__ == '__main__':
    log.info(f"启动服务: 127.0.0.1:{options.port}")
    tornado.ioloop.IOLoop.current().start()
