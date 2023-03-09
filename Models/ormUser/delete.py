# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from Database import db, UserModel, UserOperationModel

from Utils import ExDecorator, MyDatetime


class FromUserTb:

    @ExDecorator(event="删除用户")
    @db.atomic()
    def one(self, username: str) -> bool:
        UserModel.get(
            UserModel.username == username
        ).delete_instance(
            recursive=True, delete_nullable=True
        )
        return True


class FromOperateTb:

    @ExDecorator(event="删除记录")
    @db.atomic()
    def batch(self, start_time: str, final_time: str) -> bool:
        st = MyDatetime.str2dt(start_time)
        ft = MyDatetime.str2dt(final_time)
        UserOperationModel.delete().where(
            UserOperationModel.time.between(st, ft)
        ).execute()
        return True


class Delete:
    fromUserTb = FromUserTb()
    fromOperateTb = FromOperateTb()


if __name__ == '__main__':
    pass
