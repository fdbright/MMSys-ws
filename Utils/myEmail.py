# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/2/27 22:05

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

from typing import List

import smtplib
from email.mime.text import MIMEText  # 负责构造文本
from email.mime.multipart import MIMEMultipart  # 负责将多个对象集合起来


class MyEmail:
    """邮件发送类"""

    def __init__(self, host, user, password):
        """初始化"""
        self.host = host
        self.sender = user
        self.password = password
        self.__obj = None
        self.mm = None
        self.receivers: List[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def init_msg(self, receivers: List[str], sub_title: str, sub_content: str = None):
        """
        :param sub_title: 邮件主题
        :param sub_content: 邮件正文
        :param receivers: 收件人
        """
        self.receivers = receivers
        # 构造文本, 参数: 正文内容, 文本格式, 编码方式
        if sub_content:
            self.mm = MIMEText(sub_content, "html", "utf-8")
        else:
            self.mm = MIMEMultipart("related")
        self.mm["Subject"] = sub_title
        self.mm["From"] = self.sender
        for receiver in self.receivers:
            self.mm["To"] = receiver

    def add_file(self, filepath: str, filename: str, charset="utf-8"):
        attachment = MIMEText(open(filepath, "rb").read(), "base64", charset)
        attachment.add_header("Content-Disposition", "attachment", filename=(charset, '', filename))
        self.mm.attach(attachment)

    def send_mail(self):
        try:
            self.__obj = smtplib.SMTP_SSL(self.host, 465)
            self.__obj.login(self.sender, self.password)
            self.__obj.sendmail(self.sender, self.receivers, self.mm.as_string())
            # log.info(f"[邮件] 发送成功")
        except Exception as e:
            log.info(f"[邮件] 发送失败 {e}")
        finally:
            self.mm = None
            self.receivers = []

    def quit(self):
        self.__obj.quit()
        # log.info(f'[邮件] 断开连接')


if __name__ == '__main__':
    pass
