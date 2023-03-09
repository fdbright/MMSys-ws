# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2022/8/23 14:33

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union
import datetime, pytz


class MyDatetime:
    @staticmethod
    def dt2str(dt: datetime.datetime) -> str:
        return datetime.datetime.strftime(dt, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def dt2ts(dt: datetime.datetime, thousand: bool = True) -> int:
        if thousand:
            return int(dt.timestamp() * 1000)
        else:
            return int(dt.timestamp())

    @staticmethod
    def today() -> datetime.datetime:
        return datetime.datetime.now()

    @staticmethod
    def yesterday() -> datetime.datetime:
        return datetime.datetime.now() - datetime.timedelta(days=1)

    @staticmethod
    def now2str() -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def utcnow2str() -> str:
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def timestamp() -> float:
        return datetime.datetime.now().timestamp()

    @staticmethod
    def ts2str(ts: Union[str, Union[float, int]], thousand: bool = True) -> str:
        """毫秒"""
        if thousand:
            ts = float(ts) / 1000
        else:
            ts = float(ts)
        dt = datetime.datetime.fromtimestamp(ts)
        return datetime.datetime.strftime(dt, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def str2ts(dt: str) -> int:
        return int(datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000

    @staticmethod
    def str2dt(dt: str) -> datetime.datetime:
        return datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def utc2bj(dt: datetime.datetime) -> datetime.datetime:
        return dt.astimezone(pytz.timezone('Asia/Shanghai'))

    @staticmethod
    def add8hr() -> datetime.datetime:
        return datetime.datetime.now() + datetime.timedelta(hours=8)


if __name__ == '__main__':
    pass
