# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/23 21:07

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from typing import Union, List, Dict
from dataclasses import dataclass

from Utils import FreeDataclass


@dataclass
class ErrorCodeReturn(FreeDataclass):
    """请求失败"""
    exchange: str       # 交易所
    error: Union[int, str]
    type: str = "error_code"


@dataclass
class ServerTsReturn(FreeDataclass):
    """服务器时间: 毫秒"""

    exchange: str       # 交易所
    timestamp: int      # 时间戳, 毫秒
    type: str = "server_timestamp"


@dataclass
class TickReturn(FreeDataclass):
    """币币行情"""
    exchange: str       # 交易所
    all: bool = False
    symbol: str = ""    # 币对
    latest: float = -1  # 价格
    ticker: Dict[str, float] = None


@dataclass
class ContractInfo(FreeDataclass):
    """币对信息"""
    symbol: str         # 币对
    priceTick: int      # 价格精度
    amountTick: int     # 数量精度
    minVol: float       # 最小下单数量


@dataclass
class ContractReturn(FreeDataclass):
    """币对信息"""
    exchange: str       # 交易所
    contract_dict: dict
    type: str = "contract_data"


@dataclass
class DepthReturn(FreeDataclass):
    """深度信息"""
    exchange: str       # 交易所
    asks: list
    bids: list
    type: str = "depth_data"


@dataclass
class CurrentPairsReturn(FreeDataclass):
    """可用交易对"""

    exchange: str       # 交易所
    pair_lst: List[str]    # 交易对
    type: str = "current_pairs"


@dataclass
class NetWorkInfo(FreeDataclass):
    """支持充提操作的币种信息"""

    symbol: str         # 币种
    network: List[str]  # 链名
    withdraw_status: bool   # 是否开启提币
    deposit_status: bool    # 是否开启充值
    name: List[str] = None
    min_fee: Union[float, List[float]] = -1      # 提币手续费
    max_fee: Union[float, List[float]] = -1      # 提币手续费


@dataclass
class NetworkReturn(FreeDataclass):
    """支持充提操作的币种信息"""

    exchange: str       # 交易所
    network_lst: List[Union[dict, NetWorkInfo]]
    type: str = "network_data"


@dataclass
class AccountInfo(FreeDataclass):
    """账户信息"""

    symbol: str         # 币种
    free: float         # 可用
    frozen: float       # 占用
    balance: float      # 总额


@dataclass
class AccountReturn(FreeDataclass):
    """账户信息"""

    exchange: str       # 交易所
    account_lst: Union[dict, List[Union[dict, AccountInfo]]]
    type: str = "account_data"


@dataclass
class OrderInfo(FreeDataclass):
    """订单信息"""

    symbol: str         # 币种
    type: str           # 委托买卖类型
    price: float        # 价格
    amount: float       # 数量
    deal_price: float   # 成交金额
    deal_amount: float  # 成交数量
    order_id: str       # 订单ID
    status: str         # 订单状态
    create_time: str    # 订单创建时间
    update_time: str    # 最后更新时间
    fee: float = -1      # 手续费
    fee_asset: str = ""  # 手续费币种


@dataclass
class OpenOrderReturn(FreeDataclass):
    """当前挂单"""

    exchange: str       # 交易所
    order_lst: Union[List[Union[dict, OrderInfo]], str]
    total: int = -1     # 挂单总数
    type: str = "open_order"


@dataclass
class CreateOrderReturn(FreeDataclass):
    """下单"""

    exchange: str       # 交易所
    result: bool        # 是否成功
    order_id: str       # 订单ID
    custom_id: str = ""
    type: str = "create_order"


@dataclass
class CancelOrderReturn(FreeDataclass):
    """撤单"""

    exchange: str       # 交易所
    result: Union[bool, str]  # 是否成功
    type: str = "cancel_order"


@dataclass
class CancelAllOrderReturn(FreeDataclass):
    """全部撤单"""

    exchange: str       # 交易所
    result: bool        # 是否成功
    type: str = "cancel_all_order"


@dataclass
class TransInfo(FreeDataclass):
    """成交记录"""

    symbol: str         # 币种
    type: str           # 委托买卖类型
    price: float        # 成交价格
    amount: float       # 成交数量
    quoteQty: float     # 成交金额
    fee: float          # 手续费
    fee_asset: Union[str, None]  # 手续费币种
    order_id: str       # 订单ID
    trade_time: str    # 交易时间


@dataclass
class TransHistoryReturn(FreeDataclass):
    """历史成交记录"""

    exchange: str       # 交易所
    trans_lst: Union[List[Union[dict, TransInfo]], str]
    type: str = "trade_data"


@dataclass
class SubscribeKeyReturn(FreeDataclass):
    """生成subscribeKey"""
    exchange: str       # 交易所
    key: str            # subscribeKey
    type: str = "subscribe_key"


if __name__ == '__main__':
    pass
