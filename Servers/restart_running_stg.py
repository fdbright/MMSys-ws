# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/24 16:22

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from tornado.ioloop import IOLoop

from Utils import MyAioSubprocess


class RestartRunningSTG:

    def __init__(self):

        # loop
        self.loop = IOLoop.current()

        self.update_cmd: str = "sudo supervisorctl update"
        self.restart_cmd: str = "sudo supervisorctl restart ZFT_STG:{symbol}"
        self.running_cmd = "sudo supervisorctl status ZFT_STG:* |grep RUNNING|awk '{print $1}'"

    async def get_running_stg(self) -> list:
        data = await MyAioSubprocess(self.running_cmd)
        if data == "":
            return []
        return [v[8:] for v in data.split("\n")]

    async def restart(self):
        symbols = await self.get_running_stg()

        log.info(f"start: {symbols}")
        for index, symbol in enumerate(symbols, 1):
            status = await MyAioSubprocess(cmd="sudo supervisorctl status ZFT_STG:" + symbol + "|awk '{print $2}'")
            if status == "STOPPED":
                continue
            await MyAioSubprocess(self.restart_cmd.format(symbol=symbol))
            log.info(f"restart_stg: No.{index}, {symbol}")
        log.info("finish")

        exit()

    def run(self):
        self.loop.run_sync(self.restart)

        self.loop.start()


if __name__ == '__main__':
    RestartRunningSTG().run()

