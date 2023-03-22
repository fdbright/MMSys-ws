# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/20 17:47

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

import os
import pytz
from dataclasses import dataclass
from Utils import FrozenDataclass

# 日志路径
log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


@dataclass(frozen=True)
class HTTP(FrozenDataclass):
    host: str = "127.0.0.1"
    port: int = 12271
    log_path: str = os.path.join(log_path, "htp.log")


@dataclass(frozen=True)
class WSS(FrozenDataclass):
    host: str = "127.0.0.1"
    port: int = 12272
    log_path: str = os.path.join(log_path, "wss.log")


@dataclass(frozen=True)
class MYSQL(FrozenDataclass):
    """mysql配置"""
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = "lbank369"
    # password: str = "root"
    database: str = "mm_sys"

    ACConf_table: str = "account_config"
    DMConf_table: str = "depth_maker_config"
    VSConf_table: str = "vol_strategy_config"


@dataclass(frozen=True)
class SQLite(FrozenDataclass):
    """SQLite配置"""
    database: str = "/home/ec2-user/MMSys-ws/Database/mm_sys.db"
    # db_user: str = "mm_user.db"


@dataclass(frozen=True)
class REDIS(FrozenDataclass):
    """
    redis配置
    redis-cli -h 0.0.0.0 -c -p 23910
    auth 8y7bZzQr3
    """
    host: str = "127.0.0.1"
    port: int = 6379
    db: int = 0,
    password: str = "8y7bZzQr3"

    mm_sys_name: str = "MMSys-DB"
    db_lbk: str = "LBK-DB"
    db_binance: str = "Binance-DB"
    db_gate: str = "Gate-DB"
    db_okex: str = "Okex-DB"
    db_woo: str = "Woo-DB"

    send_mail_channel: str = "SendEmail"
    run_cmd_channel: str = "RunCmd"
    wss_channel_lbk: str = "Conn2WssLbk"
    htp_channel_lbk: str = "Conn2HtpLbk"

    # strategy
    stg_to_start: str = "{exchange}-STG-DB-TO-START"
    stg_to_stop: str = "{exchange}-STG-DB-TO-STOP"
    stg_running: str = "{exchange}-STG-DB-RUNNING"
    stg_ws_channel: str = "{exchange}-STG-WS-DB-{server}"
    stg_db: str = "{exchange}-STG-DB"


@dataclass(frozen=True)
class EMAIL(FrozenDataclass):
    """邮件配置"""
    host: str = "smtp.yeah.net"
    user: int = "lbank098@yeah.net"
    password: str = "JIBGZZDEDMYFBHOL"

    channel: str = "SendMail"


@dataclass(frozen=True)
class ProConf(FrozenDataclass):
    """生产环境配置"""

    HTTP = HTTP
    WSS = WSS
    MYSQL = MYSQL
    SQLITE = SQLite
    REDIS = REDIS
    EMAIL = EMAIL

    INIT_USER_PD: str = "LBK123456"             # 用户初始密码
    SECRET_KEY: str = "MMSys1.0"                # 加密 key
    CHINA_TZ = pytz.timezone("Asia/Shanghai")   # 中国时区

    TEMPLATE_PATH: str = "/home/ec2-user/MMSys-ws/Template"
    DAILY_REPORT_PATH: str = "/home/ec2-user/MMSys-ws/Template/日报模板.xlsx"

    LOG_PATH: str = log_path
    LOG_MAIN: str = os.path.join(log_path, "main.log")


if __name__ == '__main__':
    pass
