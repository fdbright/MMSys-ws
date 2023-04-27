# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/21 00:07
# 定时清理缓存

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import schedule
from tornado.gen import sleep
from tornado.ioloop import IOLoop

from Utils import MyAioSubprocess


class MonitorSystem:

    def __init__(self):
        # loop
        self.loop = IOLoop.current()

        # cache
        self.cmd_cache_clear: str = """
        sync
        echo 3 > /proc/sys/vm/drop_caches
        """
        self.cmd_cache_check: str = """free -h|awk 'NR==2{print$6}'"""

    async def clear_cache(self):
        await MyAioSubprocess(cmd=self.cmd_cache_clear)

    async def on_check(self):
        out = await MyAioSubprocess(cmd=self.cmd_cache_check)
        if "G" in out:
            await self.clear_cache()

    async def on_timer(self):
        schedule.every().day.at("00:00").do(lambda: self.loop.add_callback(self.clear_cache))
        schedule.every().day.at("08:00").do(lambda: self.loop.add_callback(self.clear_cache))
        schedule.every().day.at("16:00").do(lambda: self.loop.add_callback(self.clear_cache))
        while True:
            schedule.run_pending()
            await sleep(1)

    def run(self):
        self.loop.add_callback(self.on_timer)
        self.loop.start()


if __name__ == '__main__':
    MonitorSystem().run()
