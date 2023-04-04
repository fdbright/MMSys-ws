# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 17:45

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from dataclasses import dataclass

from Utils import FreeDataclass
from Webs import MyActionTemplate, MyHtpMethod
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
        # log.info(item)
        if item.new_file:
            with open(Configure.DAILY_REPORT_PATH, "wb") as f:
                f.write(eval(item.new_file))
            self.after_request(code=1, msg="上传成功", action=item.channel + f".{item.action}")
        else:
            self.after_request(code=-1, msg="上传失败", action=item.channel + f".{item.action}")


class ReportRest(MyHtpMethod):

    async def post(self):
        """更新日报文件"""
        file_dict = self.request.files
        file_meta = file_dict.get("file", None)  # 提取表单中‘name’为‘file’的文件元数据
        # log.info(file_meta)
        if file_meta:
            file = file_meta[0]
            with open(Configure.DAILY_REPORT_PATH, "wb") as f:
                f.write(file.body)
            self.after_request(code=1, msg="上传成功")
        else:
            self.after_request(code=-1, msg="上传失败")


if __name__ == '__main__':
    pass
