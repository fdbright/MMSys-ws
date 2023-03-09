# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from Database import db, UserModel, UserPermModel

from Config import Configure
from Utils.myEncoder import MyEncoder
from Utils import ExDecorator


class ToUserTb:

    @ExDecorator(event="更新用户信息")
    @db.atomic()
    def one(self, username: str, user_info: dict = None, user_perm: dict = None) -> bool:
        uid = UserModel.get(UserModel.username == username).id
        if user_info:
            if "password" in user_info:
                user_info["password"] = MyEncoder.byHmac(Configure.SECRET_KEY).encode(user_info["password"])
            UserModel.update(user_info).where(UserModel.id == uid).execute()
        if user_perm:
            UserPermModel.update(user_perm).where(UserPermModel.id == uid).execute()
        return True

    @ExDecorator(event="更新用户密码")
    @db.atomic()
    def password(self, username: str, password: str = None) -> bool:
        if not password:
            password = Configure.INIT_USER_PD
        UserModel.update(
            UserModel.password == MyEncoder.byHmac(Configure.SECRET_KEY).encode(password)
        ).where(
            UserModel.username == username
        ).execute()
        return True


class ToOperateTb:
    pass


class Update:
    toUserTb = ToUserTb()
    toOperateTb = ToOperateTb()


if __name__ == '__main__':
    pass
