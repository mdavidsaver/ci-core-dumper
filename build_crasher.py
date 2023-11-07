#!/usr/bin/env python

from __future__ import print_function

import setuptools # allow to monkey path in setuptools._distutils
from distutils.ccompiler import new_compiler
import os
import platform
from functools import partial

print(platform.uname())

debug = os.environ.get('DEBUG', 'NO')=='YES'

def build(exe, src):
    cc = new_compiler(verbose=1, force=1)

    # because verbose=1 is, and has long been, broken...
    def verbose_spawn(original, cmd):
        print(cmd)
        return original(cmd)
    cc.spawn = partial(verbose_spawn, cc.spawn)

    objs = cc.compile([src], debug=debug)
    cc.link_executable(objs, exe, debug=debug)

build('crasher', 'crasher.c')
