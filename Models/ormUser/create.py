# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union

from Database import db, UserModel, UserPermModel, UserOperationModel

from Config import Configure
from Objects import UserInfoObj, UserPermObj, OperateObj
from Utils.myEncoder import MyEncoder
from Utils import ExDecorator, MyDatetime


class ToUserTb:

    @ExDecorator(event="新增用户")
    @db.atomic()
    def one(self, user_info: UserInfoObj, user_perm: UserPermObj) -> Union[int, bool]:
        if not user_info.password:
            user_info.password = Configure.INIT_USER_PD
        user_info.password = MyEncoder.byHmac(Configure.SECRET_KEY).encode(user_info.password)
        user_info.createTime = MyDatetime.today()
        user = UserModel(**user_info.to_dict())
        uid = user.save()
        UserPermModel.create(user=user, **user_perm.to_dict()).save()
        return uid


class ToOperateTb:

    @ExDecorator(event="新增操作记录")
    @db.atomic()
    def one(self, new_operate: OperateObj) -> Union[int, bool]:
        new_operate.time = MyDatetime.today()
        uid = UserOperationModel.insert(
            new_operate.to_dict()
        ).execute()
        return uid


class Create:
    toUserTb = ToUserTb()
    toOperateTb = ToOperateTb()


if __name__ == '__main__':
    db.connect(reuse_if_open=True)

    nu_info = UserInfoObj(
        username="aiden",
        password="aiden",
        email="hai.shi@Lbk.one",
        team="",
        isManager=True,
        isFrozen=False
    )
    nu_perm = UserPermObj(
        monCreate=True,
        monDelete=True,
        monUpdate=True,
        monSearch=True,
        monOrder=True,
        monStrategy=True
    )
    Create.toUserTb.one(nu_info, nu_perm)

    db.close()
