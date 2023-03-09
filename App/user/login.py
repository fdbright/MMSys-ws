# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/1 16:23

import sys
sys.path.append("/home/ec2-user/MMSys-ws")

from loguru import logger as log

import random
import tornado.gen

from Webs import MyHtpMethod
from Config import Configure

from Utils.myEncoder import MyEncoder
from Utils import MyDatetime
from Models import OrmUser
from Objects import UserObj


class Login(MyHtpMethod):

    @tornado.gen.coroutine
    def get(self):
        """获取验证码"""
        username: str = self.get_argument("username")
        userinfo: UserObj = OrmUser.search.fromUserTb.one(username)
        # print(userinfo)
        if not userinfo:
            code = -1
            msg = "账户不存在"
        else:
            verify_code = str(random.randint(1, 999999)).zfill(6)
            self.redis.set(key=f"{username}_verifyCode", value=verify_code, timeout=600)
            content = """
            <p>尊敬的用户您好！</p>
            <p>验证码:</p>
            <p><h1>{}</h1></p>
            <p>有效期10分钟</p>
            """.format(verify_code)
            data = {
                "title": "上币监控系统登录验证码",
                "content": content,
                "receivers": [userinfo.email]
            }
            self.redis.pub2channel(channel=Configure.REDIS.send_mail_channel, msg=data)
            code = 1
            msg = "发送成功"
        self.after_request(code, msg)

    @tornado.gen.coroutine
    def post(self):
        """登陆"""
        payload = self.get_payload()
        username: str = payload.get("username", "")
        password: str = payload.get("password", "")
        verify_code: str = payload.get("verifyCode", "error")
        if verify_code != str(self.redis.get(key=f"{username}_verifyCode")):
            self.after_request(code=-1, msg="验证码错误")
            return
        userinfo: UserObj = OrmUser.search.fromUserTb.one(username, pwd=True, perm=True)
        if not userinfo:
            self.after_request(code=-1, msg="账户不存在")
            return
        if userinfo.isFrozen:
            self.after_request(code=-1, msg="账户已被冻结, 请联系管理员!")
            return
        if MyEncoder.byHmac(Configure.SECRET_KEY).encode(password) != userinfo.password:
            self.after_request(code=-1, msg="密码错误")
            return
        token = MyEncoder.byJWT(Configure.SECRET_KEY).encode(payload=userinfo.to_dict())
        token_id = f"{int(MyDatetime.timestamp() * 1000)}-{verify_code}"
        self.redis.set(key=f"tokenID_{token_id}", value=token, timeout=self.oneDay_sec)
        userinfo.token_id = token_id
        self.after_request(code=1, msg="登陆成功", data=userinfo.to_dict())

    @tornado.gen.coroutine
    def put(self):
        """修改密码"""
        payload = self.get_payload()
        password: str = payload.get("password", None)
        data = OrmUser.update.toUserTb.password(self.current_user.username, password)
        self.after_request(code=1 if data else -1, msg="修改密码", data=data)

    @tornado.gen.coroutine
    def delete(self):
        """登出"""
        self.clear_all_cookies()
        self.redis.delete(f"tokenID_{self.current_user.token_id}")
        self.after_request(code=1, msg="登出成功")


if __name__ == '__main__':
    pass
