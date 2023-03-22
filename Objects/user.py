# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:18

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from dataclasses import dataclass

from Utils import FreeDataclass


@dataclass
class UserInfo(FreeDataclass):
    """用户-信息"""
    username: str
    password: str = ""
    email: str = ""
    team: str = ""
    isManager: bool = False
    isFrozen: bool = False
    createTime = None


@dataclass
class UserPerm(FreeDataclass):
    """用户权限"""
    monCreate: bool = False     # 增
    monDelete: bool = False     # 删
    monUpdate: bool = False     # 改
    monSearch: bool = False     # 查
    monOrder: bool = False      # 下单
    monStrategy: bool = False   # 策略操作


@dataclass
class User(FreeDataclass):
    """用户-所有信息"""

    username: str
    password: str = ""
    email: str = ""
    team: str = ""
    isManager: bool = False
    isFrozen: bool = False
    createTime: str = None

    monCreate: bool = False
    monDelete: bool = False
    monUpdate: bool = False
    monSearch: bool = False
    monOrder: bool = False
    monStrategy: bool = False

    token_id: str = None
    # api = None
    redis_conn = None
    http_client = None
    event_dict: dict = None
    channel_dict: dict = None

    # wss
    on_timer = None
    # coin_data_wss = None
    # coin_data_source = None
    # coin_data_symbol: str = None
    # account: str = None
    # exchange: str = None
    # redis_name: str = None
    # sub_key: str = None


@dataclass
class Operation(FreeDataclass):
    """操作记录"""
    username: str           # 账号
    exchange: str = ""      # 交易所
    symbol: str = ""        # 币对
    event: str = ""         # 事件类型: 买｜卖｜撤单｜批量买｜批量卖｜启动策略｜停止策略
    time = None             # 操作时间


if __name__ == '__main__':
    pass
