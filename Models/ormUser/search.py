# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:04

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import List, Union

from Database import db, UserModel, UserPermModel, UserOperationModel

from Objects import UserObj
from Utils import ExDecorator, MyDatetime


class FromUserTb:

    @staticmethod
    def __initData(data: dict, pwd: bool = False) -> UserObj:
        if not pwd:
            data.pop("password", None)
        data.pop("id", None)
        data.pop("user", None)
        data["createTime"] = MyDatetime.dt2str(data["createTime"])
        return UserObj(**data)

    @ExDecorator(event="查询一个用户")
    def one(self, username: str, pwd: bool = False, perm: bool = False) -> Union[UserObj, None]:
        if not UserModel.get_or_none(UserModel.username == username):
            return None
        if perm:
            query = UserModel.select(
                UserModel, UserPermModel
            ).join(
                UserPermModel
            ).where(
                UserModel.username == username
            ).dicts().get()
        else:
            query = UserModel.select().where(
                UserModel.username == username
            ).dicts().get()
        return self.__initData(query, pwd)

    @ExDecorator(event="查询所有用户")
    def all(self, pwd: bool = False) -> List[dict]:
        query = UserModel.select(
            UserModel, UserPermModel
        ).join(
            UserPermModel
        ).order_by(
            UserModel.id.asc()
        ).dicts().iterator()
        return list(map(lambda x: self.__initData(x, pwd).to_dict(), query))

    @ExDecorator(event="根据组查询所有用户")
    def byTeam(self, team: str, pwd: bool = False) -> List[dict]:
        query = UserModel.select(
            UserModel, UserPermModel
        ).join(
            UserPermModel
        ).where(
            UserModel.team == team
        ).order_by(
            UserModel.id.asc()
        ).dicts().iterator()
        return list(map(lambda x: self.__initData(x, pwd).to_dict(), query))


class FromOperateTb:

    @staticmethod
    def __initData(data: dict) -> dict:
        data.pop("id", None)
        data["time"] = MyDatetime.dt2str(data["time"])
        return data

    @ExDecorator(event="根据条件查询记录")
    def batch(
            self,
            username: str = None,
            exchange: str = None,
            symbol: str = None,
            start_time: str = None,
            final_time: str = None,
            page: int = 1,
            per_page: int = 50,
    ) -> dict:
        st = MyDatetime.str2dt(start_time) if start_time else MyDatetime.yesterday()
        ft = MyDatetime.str2dt(final_time) if final_time else MyDatetime.today()
        query = UserOperationModel.select().order_by(UserOperationModel.time.desc())
        query = query.where(UserOperationModel.time.between(st, ft))
        if username:
            query = query.where(UserOperationModel.username == username)
        if exchange:
            query = query.where(UserOperationModel.exchange == exchange)
        if symbol:
            query = query.where(UserOperationModel.symbol == symbol)
        total = query.count()
        query = query.paginate(
            page=page, paginate_by=per_page
        ).dicts().iterator()
        return {"total": total, "data": list(map(self.__initData, query))}


class Search:
    fromUserTb = FromUserTb()
    fromOperateTb = FromOperateTb()


if __name__ == '__main__':
    db.connect(reuse_if_open=True)

    r = Search.fromUserTb.one("aiden")
    print(r)
