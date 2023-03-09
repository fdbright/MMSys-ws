# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:45

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate
from Config import Configure


@dataclass
class ReportItem(FreeDataclass):
    action: str
    method: str
    channel: str
    token_id: str
    # kwargs
    new_file: bytes = None


class Report(MyActionTemplate):

    async def post(self, item: ReportItem):
        """更新日报文件"""
        if item.new_file:
            with open(Configure.DAILY_REPORT_PATH, "wb") as f:
                f.write(item.new_file)
            self.after_request(code=1, msg="上传成功")
        else:
            self.after_request(code=-1, msg="上传失败")


if __name__ == '__main__':
    pass
