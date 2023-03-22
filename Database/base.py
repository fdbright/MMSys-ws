# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/22 20:09

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from playhouse.pool import PooledMySQLDatabase
from peewee import Model

from Config import Configure

db = PooledMySQLDatabase(
    Configure.MYSQL.database,
    max_connections=300,     # 最大连接数
    stale_timeout=60,        # 秒
    user=Configure.MYSQL.user,
    host=Configure.MYSQL.host,
    port=Configure.MYSQL.port,
    password=Configure.MYSQL.password,
    autoconnect=False
)

# db = PooledMySQLDatabase(
#     "mm_sys",
#     max_connections=300,     # 最大连接数
#     stale_timeout=300,       # 秒
#     user="root",
#     host="127.0.0.1",
#     port=3306,
#     password="lbank369",
#     autoconnect=False
# )

# db = PooledSqliteExtDatabase(
#     # Configure.SQLITE.database,
#     "./mm_sys.db",
#     max_connections=50,
#     stale_timeout=300,
#     pragmas={
#         "journal_mode": "wal",          # WAL-mode | 允许读者和作者共存
#         "cache_size": -1000,            # ≈ 64M | kib为单位
#         "foreign_keys": 1,              # 强制外键约束
#         "ignore_check_constraints": 0,  # 强制检查约束
#         "synchronous": 0,               # 让操作系统处理fsync（小心使用）
#     },
# )


class BaseModel(Model):
    class Meta:
        database = db


if __name__ == '__main__':
    from playhouse.migrate import *
    db.connect(reuse_if_open=True)

    migrator = MySQLMigrator(db)
    # migrator = SqliteMigrator(db)
    with db.atomic():
        migrate(
            migrator.add_column("user_info", "team", CharField(default="")),
        )

    db.connect(reuse_if_open=True)
    # db_sys.connect(reuse_if_open=True)

