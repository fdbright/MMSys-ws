# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 19:06

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from peewee import CharField

from Database import BaseModel


class ABM(BaseModel):

    account = CharField(unique=True)  # 账号
    apiKey = CharField()
    secretKey = CharField()
    team = CharField(default="")


class LBKAccountModel(ABM):
    class Meta:
        table_name = "accounts_lbk"


class BINANCEAccountModel(ABM):
    class Meta:
        table_name = "accounts_binance"


class GATEAccountModel(ABM):
    class Meta:
        table_name = "accounts_gate"


class OKEXAccountModel(ABM):
    class Meta:
        table_name = "accounts_okex"


class WOOAccountModel(ABM):
    class Meta:
        table_name = "accounts_woo"


AccountModels: dict = {
    "lbk": LBKAccountModel,
    # "binance": BINANCEAccountModel,
    # "gate": GATEAccountModel,
    # "okex": OKEXAccountModel,
    # "woo": WOOAccountModel,
}


if __name__ == '__main__':
    from Database import db

    db.connect(reuse_if_open=True)

    db.drop_tables(AccountModels.values())
    db.create_tables(AccountModels.values())

    db.close()
