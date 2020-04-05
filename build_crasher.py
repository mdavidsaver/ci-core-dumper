#!/usr/bin/env python

from __future__ import print_function

from distutils.ccompiler import new_compiler
import distutils.sysconfig
import sys
import os
import platform

print(platform.uname())

def build(exe, src):
    cc = new_compiler()
    objs = cc.compile([src])
    cc.link_executable(objs, exe)

build('crasher', 'crasher.c')
