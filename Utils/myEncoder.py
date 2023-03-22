# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2022/7/19 13:44
# @Date: 2022/10/31 18:53

from Crypto.Cipher import DES
import binascii, hmac, hashlib, jwt


class ByHmac:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def encode(self, msg: str) -> str:
        """仅加密"""
        return hmac.new(self.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


class ByDES:
    def __init__(self, secret_key: str):
        assert len(secret_key) == 8
        self.des = DES.new(secret_key.encode(), DES.MODE_ECB)   # ECB模式

    def encode(self, msg: str) -> str:
        # msg += (8 - (len(msg) % 8)) * '='
        length = 8 - (len(msg) % 8) - 1
        msg += length * "=" + str(length)
        encrypt_msg = self.des.encrypt(msg.encode())
        return binascii.b2a_hex(encrypt_msg).decode()

    def decode(self, msg: str) -> str:
        encrypto_msg = binascii.a2b_hex(msg)
        ds = self.des.decrypt(encrypto_msg).decode()
        length = int(ds[-1]) + 1
        return ds[:-length]


class ByJWT:
    def __init__(self, secret_key: str, algorithm="HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def encode(self, payload: dict) -> str:
        return jwt.encode(payload=payload, key=self.secret_key, algorithm=self.algorithm)

    def decode(self, token: str) -> dict:
        return jwt.decode(jwt=token, key=self.secret_key, algorithms=[self.algorithm])


class MyEncoder:
    byHmac = ByHmac
    byDES = ByDES
    byJWT = ByJWT


if __name__ == '__main__':
    sk = "MMSys1.0"
    mg = "69879e76f383ba27a01dcf7eeee029127cb8d8021c62f751f95afafc68f9731e37db5f8f21c5824b"
    # r = MyEncode.byHmac(secret_key=sk).encode(msg="coin")
    r = MyEncoder.byDES(secret_key=sk).decode(msg=mg)
    print(r)
