# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/15 23:07

import tempfile
import subprocess
from tornado.process import Subprocess


def MySubprocess(cmd: str) -> str:
    out_temp = tempfile.SpooledTemporaryFile(max_size=1024 * 10)
    file = out_temp.fileno()
    out = subprocess.Popen(cmd, shell=True, close_fds=True, bufsize=1, stdout=file, stderr=file, executable="/bin/bash")
    out.wait()
    out_temp.seek(0)
    lines = out_temp.readlines()
    out_temp.close()
    line = ""
    if lines:
        for lin in lines:
            line += lin.decode()
    return line


async def MyAioSubprocess(cmd: str) -> str:
    p = Subprocess(cmd, shell=True, executable="/bin/bash", stdout=Subprocess.STREAM, stderr=Subprocess.STREAM)
    # p = Subprocess(cmd, shell=True, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM)
    out = await p.stdout.read_until_close()
    try:
        return out.decode().strip()
    except AttributeError:
        return ""


if __name__ == '__main__':
    d = "ll -h"
    r = MySubprocess(cmd=d)
    print(r)
