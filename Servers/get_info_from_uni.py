# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/9 18:05

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log
from typing import List

import time
import datetime
import pandas as pd
from dataclasses import dataclass
from sqlalchemy import create_engine
from web3 import Web3
from web3.middleware import geth_poa_middleware

from Utils import MyRedis, MyDatetime, FreeDataclass


@dataclass
class DexPrice(FreeDataclass):
    type: str
    coinDepth: float = 0
    baseDepth: float = 0    # weth深度
    price: float = -1
    timestamp: float = 0


uni_Factory_abi = """
[{"inputs":[{"internalType":"address","name":"_feeToSetter","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"address","name":"pair","type":"address"},{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"PairCreated","type":"event"},{"constant":true,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"allPairs","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"allPairsLength","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"}],"name":"createPair","outputs":[{"internalType":"address","name":"pair","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"feeTo","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"feeToSetter","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_feeTo","type":"address"}],"name":"setFeeTo","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_feeToSetter","type":"address"}],"name":"setFeeToSetter","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]
"""
uni_Router_abi = """
[{"inputs":[{"components":[{"internalType":"address","name":"permit2","type":"address"},{"internalType":"address","name":"weth9","type":"address"},{"internalType":"address","name":"seaport","type":"address"},{"internalType":"address","name":"nftxZap","type":"address"},{"internalType":"address","name":"x2y2","type":"address"},{"internalType":"address","name":"foundation","type":"address"},{"internalType":"address","name":"sudoswap","type":"address"},{"internalType":"address","name":"nft20Zap","type":"address"},{"internalType":"address","name":"cryptopunks","type":"address"},{"internalType":"address","name":"looksRare","type":"address"},{"internalType":"address","name":"routerRewardsDistributor","type":"address"},{"internalType":"address","name":"looksRareRewardsDistributor","type":"address"},{"internalType":"address","name":"looksRareToken","type":"address"},{"internalType":"address","name":"v2Factory","type":"address"},{"internalType":"address","name":"v3Factory","type":"address"},{"internalType":"bytes32","name":"pairInitCodeHash","type":"bytes32"},{"internalType":"bytes32","name":"poolInitCodeHash","type":"bytes32"}],"internalType":"struct RouterParameters","name":"params","type":"tuple"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"ContractLocked","type":"error"},{"inputs":[],"name":"ETHNotAccepted","type":"error"},{"inputs":[{"internalType":"uint256","name":"commandIndex","type":"uint256"},{"internalType":"bytes","name":"message","type":"bytes"}],"name":"ExecutionFailed","type":"error"},{"inputs":[],"name":"FromAddressIsNotOwner","type":"error"},{"inputs":[],"name":"InsufficientETH","type":"error"},{"inputs":[],"name":"InsufficientToken","type":"error"},{"inputs":[],"name":"InvalidBips","type":"error"},{"inputs":[{"internalType":"uint256","name":"commandType","type":"uint256"}],"name":"InvalidCommandType","type":"error"},{"inputs":[],"name":"InvalidOwnerERC1155","type":"error"},{"inputs":[],"name":"InvalidOwnerERC721","type":"error"},{"inputs":[],"name":"InvalidPath","type":"error"},{"inputs":[],"name":"InvalidReserves","type":"error"},{"inputs":[],"name":"LengthMismatch","type":"error"},{"inputs":[],"name":"NoSlice","type":"error"},{"inputs":[],"name":"SliceOutOfBounds","type":"error"},{"inputs":[],"name":"SliceOverflow","type":"error"},{"inputs":[],"name":"ToAddressOutOfBounds","type":"error"},{"inputs":[],"name":"ToAddressOverflow","type":"error"},{"inputs":[],"name":"ToUint24OutOfBounds","type":"error"},{"inputs":[],"name":"ToUint24Overflow","type":"error"},{"inputs":[],"name":"TransactionDeadlinePassed","type":"error"},{"inputs":[],"name":"UnableToClaim","type":"error"},{"inputs":[],"name":"UnsafeCast","type":"error"},{"inputs":[],"name":"V2InvalidPath","type":"error"},{"inputs":[],"name":"V2TooLittleReceived","type":"error"},{"inputs":[],"name":"V2TooMuchRequested","type":"error"},{"inputs":[],"name":"V3InvalidAmountOut","type":"error"},{"inputs":[],"name":"V3InvalidCaller","type":"error"},{"inputs":[],"name":"V3InvalidSwap","type":"error"},{"inputs":[],"name":"V3TooLittleReceived","type":"error"},{"inputs":[],"name":"V3TooMuchRequested","type":"error"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"RewardsSent","type":"event"},{"inputs":[{"internalType":"bytes","name":"looksRareClaim","type":"bytes"}],"name":"collectRewards","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes","name":"commands","type":"bytes"},{"internalType":"bytes[]","name":"inputs","type":"bytes[]"}],"name":"execute","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"bytes","name":"commands","type":"bytes"},{"internalType":"bytes[]","name":"inputs","type":"bytes[]"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"execute","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256[]","name":"","type":"uint256[]"},{"internalType":"uint256[]","name":"","type":"uint256[]"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC1155BatchReceived","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC1155Received","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC721Received","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"int256","name":"amount0Delta","type":"int256"},{"internalType":"int256","name":"amount1Delta","type":"int256"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"uniswapV3SwapCallback","outputs":[],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]
"""
uni_pair_abi = """
[{"inputs":[],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Burn","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"Mint","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount0Out","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1Out","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Swap","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint112","name":"reserve0","type":"uint112"},{"indexed":false,"internalType":"uint112","name":"reserve1","type":"uint112"}],"name":"Sync","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"constant":true,"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"MINIMUM_LIQUIDITY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"PERMIT_TYPEHASH","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"burn","outputs":[{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_token0","type":"address"},{"internalType":"address","name":"_token1","type":"address"}],"name":"initialize","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"kLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"mint","outputs":[{"internalType":"uint256","name":"liquidity","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"price0CumulativeLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"price1CumulativeLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"skim","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"uint256","name":"amount0Out","type":"uint256"},{"internalType":"uint256","name":"amount1Out","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"swap","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"sync","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]
"""
uni_Factory = Web3.toChecksumAddress("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
uni_Route = Web3.toChecksumAddress("0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B")


class GetInfoFromDEX:

    def __init__(self):

        # mysql
        self.db = "mysql+pymysql://root:lbank369@127.0.0.1:3306/mm_sys?charset=utf8"

        # redis
        self.redis_pool = MyRedis(db=0)
        self.name = "DEX-DB"
        self.key = "dex_price_uni"

        # symbol
        self.symbols: List[dict] = []
        self.symbols_type: dict = {}

        # web3
        self.rpc = [
            "https://rpc.ankr.com/eth",
            "https://eth-rpc.gateway.pokt.network",
            "https://ethereum.publicnode.com",
            "https://cloudflare-eth.com",
            "https://eth.rpc.blxrbdn.com",
            "https://eth.llamarpc.com",
            "https://singapore.rpc.blxrbdn.com",
            "https://virginia.rpc.blxrbdn.com",
            "https://eth.api.onfinality.io/public",
            "https://1rpc.io/eth",
            "https://rpc.flashbots.net",
            "https://virginia.rpc.blxrbdn.com",
            "https://eth.rpc.blxrbdn.com",
            "https://1rpc.io/eth",
            "https://api.securerpc.com/v"
        ]
        self.w3 = None
        self.contract_uni_Router = None
        self.contract_uni_Factory = None
        self.uni_contract_abi = uni_pair_abi
        self.weth_address = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'.lower()
        self.usdt_address = '0xdAC17F958D2ee523a2206206994597C13D831ec7'.lower()
        self.usdc_address = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'.lower()
        self.dai_address = '0x6B175474E89094C44Da98b954EedeAC495271d0F'.lower()

        self.dex_coin_dict = {}
        self.weth_price: float = 0

    def get_data_from_mysql(self):
        eg = create_engine(self.db)
        df = pd.read_sql("SELECT symbol, f_coin, f_coin_addr FROM coins_lbk WHERE addr_type = 'ETH';", eg)
        self.symbols = df.to_dict(orient="records")

    def init_web3(self, index: int):
        self.w3 = Web3(Web3.HTTPProvider(self.rpc[index]))
        print(self.w3.isConnected())
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract_uni_Router = self.w3.eth.contract(
            address=Web3.toChecksumAddress(uni_Route), abi=uni_Router_abi
        )
        self.contract_uni_Factory = self.w3.eth.contract(
            address=Web3.toChecksumAddress(uni_Factory), abi=uni_Factory_abi
        )

    def get_weth_price(self):
        weth_usdc_address = self.contract_uni_Factory.caller.getPair(
            Web3.toChecksumAddress(self.weth_address),
            Web3.toChecksumAddress(self.usdc_address)
        )
        weth_usdc_contract = self.w3.eth.contract(
            address=Web3.toChecksumAddress(weth_usdc_address), abi=self.uni_contract_abi
        )
        weth_usdc_reserves = weth_usdc_contract.caller.getReserves()
        self.weth_price = weth_usdc_reserves[0] / weth_usdc_reserves[1] * (10 ** 12)

    def get_dex_price(self, address: str, _type: str = "weth") -> DexPrice:
        res = DexPrice(type=_type)
        if _type == "weth":
            addr = self.weth_address
        elif _type == "usdt":
            addr = self.usdt_address
        elif _type == "usdc":
            addr = self.usdc_address
        elif _type == "dai":
            addr = self.dai_address
        else:
            return res
        try:
            contract_address = self.contract_uni_Factory.caller.getPair(
                Web3.toChecksumAddress(address),
                Web3.toChecksumAddress(addr)
            )
            if contract_address != '0x0000000000000000000000000000000000000000':
                contract = self.w3.eth.contract(
                    address=Web3.toChecksumAddress(contract_address), abi=self.uni_contract_abi
                )
                reserves = contract.caller.getReserves()
                coin_contract = self.w3.eth.contract(
                    address=Web3.toChecksumAddress(address), abi=self.uni_contract_abi
                )
                decimal = coin_contract.caller.decimals()
                if contract.caller.token0().lower() == address.lower():
                    reserves0 = reserves[0] / 10 ** decimal
                    reserves1 = float(self.w3.fromWei(reserves[1], 'ether'))
                    res.coinDepth = reserves0
                    res.baseDepth = reserves1
                    res.price = (reserves1 / reserves0)
                    res.timestamp = reserves[2]
                else:
                    reserves0 = float(self.w3.fromWei(reserves[0], 'ether'))
                    reserves1 = reserves[1] / 10 ** decimal
                    res.coinDepth = reserves1
                    res.baseDepth = reserves0
                    res.price = (reserves0 / reserves1)
                    res.timestamp = reserves[2]
                if _type == "weth":
                    res.price *= self.weth_price
            else:
                pass
        except Exception as e:
            log.warning(f"weth 异常: {e}")
        finally:
            return res

    def get_price(self):
        for index, symbol in enumerate(self.symbols):
            self.init_web3(index=(index % 14))
            if index == 0:
                self.get_weth_price()
            coin = symbol["symbol"]
            addr = symbol["f_coin_addr"]
            _type = self.symbols_type.get(coin, None)
            if _type:
                dex_price = self.get_dex_price(address=addr, _type=_type)
            else:
                dex_lst = [
                    self.get_dex_price(address=addr, _type="usdt"),
                    self.get_dex_price(address=addr, _type="usdc"),
                    self.get_dex_price(address=addr, _type="dai"),
                    self.get_dex_price(address=addr, _type="weth"),
                ]
                dex_price = sorted(dex_lst, key=lambda x: x.baseDepth)[-1]
                self.symbols_type[coin] = dex_price.type
            self.dex_coin_dict[coin] = dex_price.to_dict()
            time.sleep(2)

    def set_redis(self):
        redis = self.redis_pool.open(conn=True)
        for symbol, dex_price in self.dex_coin_dict.items():
            redis.hSet(name=self.name, key=symbol, value=dex_price)
        dt = MyDatetime.today()
        self.dex_coin_dict["upgrade_time"] = MyDatetime.dt2ts(dt, thousand=True)
        self.dex_coin_dict["upgrade_time_dt"] = MyDatetime.dt2str(dt)
        print(self.dex_coin_dict)
        redis.hSet(name=self.name, key=self.key, value=self.dex_coin_dict)
        redis.close()

    def main(self):
        self.get_data_from_mysql()
        self.get_price()
        self.set_redis()
        self.dex_coin_dict.clear()


if __name__ == '__main__':
    from tornado.ioloop import PeriodicCallback, IOLoop

    dex = GetInfoFromDEX()
    dex.main()
    PeriodicCallback(
        callback=dex.main,
        callback_time=datetime.timedelta(minutes=2),
        jitter=0.2
    ).start()
    IOLoop.instance().start()
