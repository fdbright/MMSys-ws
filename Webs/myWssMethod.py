# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 15:00

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import Optional, Awaitable, Union, Dict, Any

import time
import tornado.escape
from tornado.websocket import WebSocketHandler


class MyWssMethod(WebSocketHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        pass

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def write_message(self, message: Union[bytes, str, Dict[str, Any]], binary: bool = False):
        if self.ws_connection is None or self.ws_connection.is_closing():
            return
        if isinstance(message, dict):
            message = tornado.escape.json_encode(message)
        return self.ws_connection.write_message(message, binary=binary)

    def after_request(self, code: int, msg: str, action=None, data=None):
        resp: dict = {
            "code": code,
            "msg": msg,
        }
        if action:
            if isinstance(action, str):
                resp["action"] = action
            else:
                if action.action == "rest":
                    resp["action"] = f"{action.channel}.{action.action}.{action.method.lower()}"
                else:
                    resp["action"] = f"{action.channel}.{action.action}"
        if data:
            resp["data"] = data
        print("resp", resp)
        self.write_message(resp)

    def check_origin(self, origin):
        """允许跨域请求"""
        return True

    def getParams(self) -> dict:
        return {k: v[0].decode() for k, v in self.request.arguments.items()}

    def on_ping(self, data):
        log.info("ping", data)

    def on_pong(self, data):
        log.info("pong", data)
        if not data:
            self.ping(str(round(time.time() * 1000)))

    def start_event(self):
        try:
            for p in self.current_user.event_dict.values():
                if p.is_running():
                    continue
                p.start()
        except Exception as e:
            log.warning(f"启动定时任务 异常: {e}")

    def stop_event(self):
        try:
            for p in self.current_user.event_dict.values():
                if p.is_running():
                    p.stop()
        except Exception as e:
            log.warning(f"关闭定时任务 异常: {e}")


if __name__ == '__main__':
    pass
