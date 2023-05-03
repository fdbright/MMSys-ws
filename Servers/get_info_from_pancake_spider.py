# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023.05.03 19:43

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List

import bs4
from tornado.gen import sleep
from tornado.ioloop import IOLoop
from aiohttp.http_websocket import WSMessage
from aiohttp import ClientSession, ClientResponse


class PancakeSpider:

    def __init__(self):
        super().__init__()

        self.loop = IOLoop.current()

        self.session = None

        self.url = "https://pancakeswap.finance/swap?chain={chain}&outputCurrency={out_addr}"

        self.chain: dict = {
            "eth": "eth",
            "bsc": "bsc",
        }
        self.usdt_addr = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

    async def on_first(self):
        self.session = ClientSession(trust_env=True)

        resp = await self.session.get(self.url.format(chain="eth", out_addr=self.usdt_addr), proxy="http://127.0.0.1:7890")
        bs4.BeautifulSoup.decode()
        print(resp)

    async def on_timer(self):
        pass

    def run(self):
        self.loop.run_sync(self.on_first)
        self.loop.add_callback(self.on_timer)
        self.loop.start()


if __name__ == '__main__':
    PancakeSpider().run()
