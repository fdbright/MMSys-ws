# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/13 22:49

from time import sleep
from queue import Queue, Empty
from threading import Thread
from asyncio import get_event_loop, set_event_loop, run_coroutine_threadsafe


class MyEventEngine:

    def __init__(self, interval: float = 1):

        self._interval = interval
        self._active: bool = False
        self._queue: Queue = Queue()
        self._loop = get_event_loop()

        self._normal = Thread(target=self._normal)
        self._timer = Thread(target=self._run_timer)

    def _run_timer(self):
        while self._active:
            sleep(self._interval)
            # self._queue.put()

    def _normal(self):
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=1)
                start_event_loop(self._loop)
                run_coroutine_threadsafe(event(), self._loop)
            except Empty:
                pass

    def start(self):
        self._active = True
        self._normal.start()
        self._timer.start()

    def stop(self):
        self._active = False
        self._normal.join()
        self._timer.join()


def start_event_loop(loop):
    """启动事件循环"""
    if not loop.is_running():
        Thread(target=run_event_loop, args=(loop,), daemon=True).start()


def run_event_loop(loop) -> None:
    """运行事件循环"""
    set_event_loop(loop)
    loop.run_forever()
