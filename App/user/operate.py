# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 16:54

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate
from Models import OrmUser


@dataclass
class OperateItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    page: int = 1
    per_page: int = 50
    username: str = None
    symbol: str = None
    exchange: str = None
    startTime: str = None
    finalTime: str = None


class Operate(MyActionTemplate):

    async def get(self, item: OperateItem):
        """获取操作记录"""
        if self.current_user.isManager:
            data = OrmUser.search.fromOperateTb.batch(
                username=item.username,
                exchange=item.exchange,
                symbol=item.symbol,
                start_time=item.startTime,
                final_time=item.finalTime,
                page=item.page,
                per_page=item.per_page
            )
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="获取操作记录", action=item.channel + f".{item.action}", data=data)

    async def delete(self, item: OperateItem):
        """删除记录"""
        if self.current_user.isManager:
            data = OrmUser.delete.fromOperateTb.batch(item.startTime, item.finalTime)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="删除记录", action=item.channel + f".{item.action}", data=data)


if __name__ == '__main__':
    pass
