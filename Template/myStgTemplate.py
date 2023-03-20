# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/17 18:00

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

import nest_asyncio
nest_asyncio.apply()

from loguru import logger as log
from typing import List, Dict, Union

import asyncio


class EventEngine:

    def __init__(self):

        self._loop: asyncio.AbstractEventLoop = None

    def start(self):
        pass

    def stop(self):
        pass


if __name__ == '__main__':
    pass
