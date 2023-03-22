# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 17:56

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from enum import Enum
from dataclasses import dataclass


@dataclass
class FreeDataclass:
    def to_dict(self) -> dict:
        """转化为字典"""
        return self.__dict__


@dataclass(frozen=True)
class FrozenDataclass:
    def to_dict(self) -> dict:
        """转化为字典"""
        return self.__dict__


class MyEnum(Enum):
    def value(self):
        """key对应value"""
        return self._value_

    @classmethod
    def to_dict(cls) -> dict:
        """转化为字典"""
        return {k: v.value() for k, v in cls._member_map_.items()}

    @classmethod
    def keys(cls) -> list:
        """所有key值"""
        return cls._member_names_

    @classmethod
    def values(cls) -> list:
        """所有value值"""
        return list(cls._value2member_map_.keys())


if __name__ == '__main__':
    pass
