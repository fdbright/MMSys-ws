# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/22 23:52

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import ujson

from Config import Configure
from Utils import MyEmail, MyRedis


class SendMail:

    def __init__(self):
        self.redis_conn = MyRedis(db=0).open(conn=True)
        self.me = MyEmail(Configure.EMAIL.host, Configure.EMAIL.user, Configure.EMAIL.password)
        self.channel = Configure.REDIS.send_mail_channel

    def run(self):
        pub = self.redis_conn.subscribe(self.channel)
        while True:
            item: list = pub.parse_response(block=True)
            # print(type(item), item)
            if item[0] != "message":
                continue
            data: dict = ujson.loads(item[-1])
            self.me.init_msg(receivers=data["receivers"], sub_title=data["title"], sub_content=data["content"])
            self.me.send_mail()


if __name__ == '__main__':
    sm = SendMail()
    sm.run()

