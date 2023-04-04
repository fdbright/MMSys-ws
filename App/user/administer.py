# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 16:24

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate
from Models import OrmUser
from Objects import UserInfoObj, UserPermObj
from Config import Configure


@dataclass
class AdminItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    username: str = None
    user_info: dict = None
    user_perm: dict = None
    initPwd: bool = False


class Admin(MyActionTemplate):

    async def get(self, item: AdminItem):
        """获取用户信息"""
        if self.current_user.isManager:
            if item.username:
                data = OrmUser.search.fromUserTb.one(item.username, perm=True)
            else:
                if self.current_user.team == "":
                    data = OrmUser.search.fromUserTb.all()
                else:
                    data = OrmUser.search.fromUserTb.byTeam(self.current_user.team)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="获取所有用户", action=item, data=data)

    async def post(self, item: AdminItem):
        """新增用户"""
        user_info: UserInfoObj = UserInfoObj(**item.user_info)
        user_perm: UserPermObj = UserPermObj(**item.user_perm)
        if self.current_user.isManager:
            data = OrmUser.create.toUserTb.one(user_info, user_perm)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="新增用户", action=item, data=data)

    async def put(self, item: AdminItem):
        """修改用户信息"""
        if self.current_user.isManager:
            if item.initPwd:
                item.user_info["password"] = Configure.INIT_USER_PD
            data = OrmUser.update.toUserTb.one(item.username, item.user_info, item.user_perm)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="修改用户信息", action=item, data=data)

    async def delete(self, item: AdminItem):
        """删除用户"""
        if self.current_user.isManager:
            data = OrmUser.delete.fromUserTb.one(item.username)
        else:
            data = None
        self.after_request(code=1 if data else -1, msg="删除用户", action=item, data=data)


if __name__ == '__main__':
    pass
