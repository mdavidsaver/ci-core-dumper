#!/usr/bin/env python

from distutils.ccompiler import new_compiler
import distutils.sysconfig
import sys
import os

def build(exe, src):
    cc = new_compiler()
    objs = cc.compile([src])
    cc.link_executable(objs, exe)

build('crasher', 'crasher.c')
