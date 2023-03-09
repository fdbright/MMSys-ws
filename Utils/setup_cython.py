# -*- coding:utf-8 -*-
# @Author: Aiden
# @Date: 2023/3/2 15:36

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize
import time, os


def main(name: str, path: str):
    filename = name
    extensions = Extension(filename, [path])
    setup(
        name=name,
        cmdclass={'build_ext': build_ext},
        ext_modules=cythonize(extensions, language_level=3),
    )
    time.sleep(5)
    os.remove(path=path.replace(".py", ".c"))


if __name__ == '__main__':
    # main(name="lbk_mcm_mode", path="/home/ec2-user/strategy/lbk_mcm_mode.py")
    # main(name="lbk_redis_mode", path="/home/ec2-user/strategy/mm_modes/lbk_redis_mode.py")
    # main(name="myEncoder", path="/home/ec2-user/strategy/StrategyUtils/myEncoder.py")
    main(name="myEncoder", path="/home/ec2-user/MMSys-ws/Utils/myEncoder.py")
    # main(name="myEncoder", path="/root/myEncoder.py")

    # python setup_cython.py build_ext --inplace
