# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/4/23 11:27

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

import schedule
from tornado.gen import sleep
from tornado.ioloop import IOLoop

from Utils import MyAioSubprocess


class AutoRestart:
    
    def __init__(self):
        # loop
        self.loop = IOLoop().current()

        # cmd
        self.server_cmd: str = "sudo supervisorctl restart MMsys:*"

    def restart_server(self):
        self.loop.add_callback(lambda: MyAioSubprocess(cmd=self.server_cmd))

    async def on_timer(self):
        schedule.every().day.at("00:00").do(self.restart_server)

        while True:
            schedule.run_pending()
            await sleep(1)

    def run(self):
        self.loop.add_callback(self.on_timer)
        self.loop.start()


if __name__ == '__main__':
    AutoRestart().run()
