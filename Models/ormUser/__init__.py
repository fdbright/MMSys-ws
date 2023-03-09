# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 18:59

from .create import Create
from .delete import Delete
from .update import Update
from .search import Search


class OrmUser:
    create = Create()
    delete = Delete()
    update = Update()
    search = Search()


if __name__ == '__main__':
    pass
