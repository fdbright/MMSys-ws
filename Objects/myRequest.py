# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 16:21

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union
from dataclasses import dataclass
from Utils import FreeDataclass, FrozenDataclass


@dataclass(frozen=True)
class Method(FrozenDataclass):
    get: str = "GET"
    post: str = "POST"


@dataclass
class Request(FreeDataclass):
    method: str = ""
    host: str = ""
    api: str = ""

    params: Union[dict, None] = None
    data: Union[dict, str, bytes, None] = None
    headers: dict = None

    apiKey: str = ""
    secretKey: str = ""
    path: str = ""


if __name__ == '__main__':
    pass
