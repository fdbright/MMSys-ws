# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:07

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate
from Models import OrmMarket
from Objects import AccountObj


@dataclass
class AccountItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    account: str = None
    exchange: str = "lbk"
    new_account: dict = None


class Account(MyActionTemplate):

    async def get(self, item: AccountItem):
        """获取账户"""
        if self.current_user.monSearch:
            if item.account:
                data = OrmMarket.search.fromAccountTb.one(item.exchange, item.account, to_dict=True)
            else:
                if self.current_user.team == "":
                    data = OrmMarket.search.fromAccountTb.all(item.exchange, to_dict=True)
                else:
                    data = OrmMarket.search.fromAccountTb.byTeam(item.exchange, self.current_user.team, to_dict=True)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="获取账户", data=data)

    async def post(self, item: AccountItem):
        """新增账户"""
        if self.current_user.monCreate:
            if isinstance(item.new_account, list):
                data = OrmMarket.create.toAccountTb.batch(item.exchange, [AccountObj(**val) for val in item.new_account])
            else:
                data = OrmMarket.create.toAccountTb.one(item.exchange, AccountObj(**item.new_account))
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="新增账户", data=data)

    async def put(self, item: AccountItem):
        """修改账户"""
        if self.current_user.monUpdate:
            data = OrmMarket.update.toAccountTb.one(item.exchange, item.new_account)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="修改账户", data=data)

    async def delete(self, item: AccountItem):
        """删除账户"""
        if self.current_user.monDelete:
            data = OrmMarket.delete.fromAccountTb.one(item.exchange, item.account)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="删除账户", data=data)


if __name__ == '__main__':
    pass
