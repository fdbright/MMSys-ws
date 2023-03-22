# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/22 22:10

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from peewee import CharField, BooleanField, FloatField, IntegerField, DateTimeField

from Database import BaseModel


class CBM(BaseModel):
    symbol = CharField()                        # 币对
    f_coin = CharField()                        # 外部名称
    full_name = CharField()                     # 币对全名

    f_coin_addr = CharField()                   # 币种地址
    addr_type = CharField()                     # 链名称

    if1m = BooleanField(default=False)          # 是否乘以1000000

    account = CharField()                       # 账号
    team = CharField(default="")                # 团队类型

    profit_rate = FloatField(null=True)         # 点差
    step_gap = FloatField(null=True)            # 步长
    order_amount = IntegerField(null=True)      # 挂单量
    order_nums = IntegerField(default=30)       # 档位

    isUsing = BooleanField(default=True)        # 是否正在做市
    createTime = DateTimeField()                # 添加时间
    updateTime = DateTimeField()                # 更新时间


class LBKCoinModel(CBM):
    class Meta:
        table_name = "coins_lbk"


class BINANCECoinModel(CBM):
    class Meta:
        table_name = "coins_binance"


class GATECoinModel(CBM):
    class Meta:
        table_name = "coins_gate"


class OKEXCoinModel(CBM):
    class Meta:
        table_name = "coins_okex"


class WOOCoinModel(CBM):
    class Meta:
        table_name = "coins_woo"


CoinModels: dict = {
    "lbk": LBKCoinModel,
    # "binance": BINANCECoinModel,
    # "gate": GATECoinModel,
    # "okex": OKEXCoinModel,
    # "woo": WOOCoinModel,
}


if __name__ == '__main__':
    from Database import db

    db.connect(reuse_if_open=True)

    db.drop_tables(CoinModels.values())
    db.create_tables(CoinModels.values())
    # BINANCECoinModel.drop_table()

    db.close()
