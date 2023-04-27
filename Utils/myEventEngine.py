# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/13 22:49

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from threading import Thread
from asyncio import set_event_loop

from loguru import logger as log

import time
import ujson
import asyncio
from tornado.gen import sleep
from tornado.queues import Queue
from tornado.ioloop import IOLoop
from aiohttp.http_websocket import WSMessage
from aiohttp import ClientSession, ClientResponse


class MyEngine:

    def __init__(self):
        self._queue = Queue()
        self.loop = IOLoop.current()

        self.session: ClientSession = ClientSession(trust_env=True)

        self.is_connected: bool = False
        self._register_lst = []

    async def _task(self) -> None:
        while True:
            task, args = await self._queue.get()
            if args:
                await task(*args)
            else:
                await task()

    async def _timer(self, interval: float):
        while True:
            await sleep(interval)
            if self.is_connected:
                await self.add_task(self.on_timer)

    async def add_task(self, task: asyncio.coroutine, args: tuple = None) -> None:
        await self._queue.put([task, args])

    async def on_timer(self):
        pass

    async def register(self, event: str, task: asyncio.coroutine):
        pass

    def start(self, interval: float = None) -> None:
        self.loop.add_callback(self._task)
        if interval:
            self.loop.add_callback(lambda: self._timer(interval))
        self.loop.start()

    def stop(self) -> None:
        self.loop.stop()


class RestClient:

    def __init__(self, session: ClientSession = None):
        self.session: ClientSession = session

    async def get_response(self, req):
        if req.params:
            query: list = []
            for k, v in sorted(req.params.items()):
                query.append(k + "=" + str(v))
            query: str = '&'.join(query)
            path = req.host + req.api + "?" + query
            req.params = {}
        else:
            path = req.host + req.api
        cr: ClientResponse = await self.session.request(
            method=req.method,
            url=path,
            headers=req.headers,
            params=req.params,
            data=req.data,
        )
        try:
            # log.info(cr.url)
            resp: dict = await cr.json()
        except Exception as e:
            log.error(f"请求失败, url: {cr.url}, err: {e}")
            resp = {}
        del cr
        return resp


class WebsocketClient:

    def __init__(self, session: ClientSession = None):

        self._ws = None

        self.session: ClientSession = session

        self.is_connected: bool = False

    async def init_session(self):
        self.session = ClientSession(trust_env=True)

    async def on_ping(self, data: dict):
        pass

    async def on_connected(self):
        pass

    async def on_packet(self, data: dict):
        pass

    async def send_packet(self, data: dict):
        try:
            await self._ws.send_str(ujson.dumps(data))
        except AttributeError:
            pass

    async def subscribe(self, url: str):
        while True:
            try:
                self._ws = await self.session.ws_connect(url=url, ssl=False)
                await self.on_connected()
                self.is_connected = True
                async for msg in self._ws:  # type: WSMessage
                    try:
                        item: dict = msg.json(loads=ujson.loads)
                    except Exception as e:
                        log.warning(f"websocket data: {msg.data}, {e}")
                    else:
                        await self.on_packet(item)
                self._ws = None
                self.is_connected = False
                log.warning(f"websocket 断连, 即将重连")
                await sleep(0.2)
            except Exception as e:
                log.warning(f"websocket 异常: {e}, 即将重连")
                self.is_connected = False
                time.sleep(5)


def start_event_loop(loop):
    """启动事件循环"""
    if not loop.is_running():
        Thread(target=run_event_loop, args=(loop,), daemon=True).start()


def run_event_loop(loop) -> None:
    """运行事件循环"""
    set_event_loop(loop)
    loop.run_forever()


if __name__ == '__main__':
    pass
