# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 17:42

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Optional, Awaitable

from loguru import logger as log

import json

import tornado.gen
from tornado.web import RequestHandler
from tornado.options import options
from tornado.httpclient import AsyncHTTPClient

from Config import Configure
from Utils.myEncoder import MyEncoder
from Objects import UserObj
from Database import db


class MyHtpMethod(RequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_headers()
        self.oneDay_sec = 24 * 60 * 60
        self.redis = None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def initialize(self):
        self.settings["cookie_secret"] = Configure.SECRET_KEY
        self.current_user = None

    def get_current_user(self):
        return

    def set_default_headers(self):
        """允许跨域请求"""
        origin_url = self.request.headers.get("Origin", "*")
        self.set_header("Access-Control-Allow-Origin", origin_url)
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Access-Control-Allow-Headers", ",".join(
            ["Content-Type"] + self.request.headers.get("Access-Control-Request-Headers", "").split(",")
        ))
        self.set_header("Access-Control-Expose-Headers", "Content-Type, ")
        self.set_header("Access-Control-Allow-Methods", "POST, GET, PUT, DELETE, PATCH, OPTIONS")
        self.set_header("Access-Control-Max-Age", 1000)
        self.set_header("Content-type", "application/x-www-form-urlencoded")

    def options(self):
        """vue预加载"""
        self.set_status(200)
        self.finish()

    def prepare(self):
        log.info(f"请求开始, method: {self.request.method}, path: {self.request.path}")
        self.redis = options.redis.open(conn=True)
        if "undefined" in self.request.query or "undefined" in self.request.body.decode():
            self.after_request(code=-1, msg="参数异常")
            return
        try:
            try:
                token_id = self.request.headers["token_id"]
            except KeyError:
                token_id = self.request.headers["Cookie"][9:]
        except KeyError:
            token_id = None
        if token_id not in [None, "None", "null", "undefined", ""]:
            token = self.redis.get(f"tokenID_{token_id}")
            if not token:
                self.after_request(code=-1, msg="登陆过期")
                return
            payload = MyEncoder.byJWT(Configure.SECRET_KEY).decode(token=token)
            self.current_user = UserObj(**payload)
            if "/htp/" in self.request.path:
                self.current_user.http_client = AsyncHTTPClient()
        else:
            self.current_user = UserObj(username="traveler")
        db.connect(reuse_if_open=True)

    def after_request(self, code: int, msg: str, action: str, data=None):
        resp = {
            "code": code,
            "msg": msg,
            "action": action
        }
        if data:
            resp["data"] = data
        self.finish(resp)

    def get_payload(self) -> dict:
        """获取body参数"""
        try:
            data = json.loads(self.request.body.decode())
        except Exception as e:
            print(e)
            data = {}
        log.info(data)
        return data

    @tornado.gen.coroutine
    def on_finish(self) -> None:
        log.info(f"请求结束, method: {self.request.method}")
        db.close()
        self.redis.close()
        try:
            if self.current_user.username == "traveler":
                # self.current_user.es.quit()
                pass
            else:
                self.current_user.http_client.close()
        except AttributeError:
            pass
        return super(MyHtpMethod, self).on_finish()


if __name__ == '__main__':
    pass
