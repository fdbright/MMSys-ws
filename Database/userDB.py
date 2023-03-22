# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 18:58

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from peewee import CharField, DateTimeField, BooleanField, ForeignKeyField
from Database import BaseModel


class UserModel(BaseModel):
    class Meta:
        table_name = "user"
        indexes = (
            (("username", "team"), False),
        )

    username = CharField(unique=True)
    password = CharField()
    email = CharField()
    team = CharField(default="")
    isManager = BooleanField(default=False)     # 是否管理员
    isFrozen = BooleanField(default=False)      # 是否冻结
    createTime = DateTimeField()


class UserPermModel(BaseModel):
    class Meta:
        table_name = "user_perm"

    user = ForeignKeyField(UserModel)           # UserId

    monCreate = BooleanField(default=False)     # 增
    monDelete = BooleanField(default=False)     # 删
    monUpdate = BooleanField(default=False)     # 改
    monSearch = BooleanField(default=False)     # 查
    monOrder = BooleanField(default=False)      # 下单|撤单
    monStrategy = BooleanField(default=False)   # 策略操作


class UserOperationModel(BaseModel):
    class Meta:
        table_name = "user_operations"
        indexes = (
            (("username", "symbol", "time", "exchange"), False),
        )

    username = CharField()              # 账号
    exchange = CharField()              # 交易所
    symbol = CharField()                # 币对
    event = CharField()                 # 事件类型: 买｜卖｜撤单｜批量买｜批量卖｜启动策略｜停止策略
    time = DateTimeField()              # 操作时间


if __name__ == '__main__':
    from Database import db
    import datetime

    db.connect(reuse_if_open=True)
    tables = [
        UserModel,
        UserPermModel,
        UserOperationModel,
    ]
    db.drop_tables(tables)
    db.create_tables(tables)

    # UserModel.insert(
    #     {
    #         "username": "aiden",
    #         "password": "aiden",
    #         "email": "hai.shi@Lbk.one",
    #         "isManager": True,
    #         "createTime": datetime.datetime.now(),
    #         "monCreate": True,
    #         "monDelete": True,
    #         "monUpdate": True,
    #         "monSearch": True,
    #         "monOrder": True,
    #         "monStrategy": True
    #     }
    # ).execute()

    db.close()
