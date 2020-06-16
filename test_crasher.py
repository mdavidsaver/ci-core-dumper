#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import platform
import ctypes
import subprocess as SP

if platform.system()=='Windows':
    # https://docs.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode?redirectedfrom=MSDN
    # set SEM_FAILCRITICALERRORS  (1)
    # but leave clear SEM_NOGPFAULTERRORBOX (2)
    errmode = ctypes.windll.kernel32.SetErrorMode(1)
    print('Previous windows error mode 0x%x'%errmode)
    errmode = ctypes.windll.kernel32.SetErrorMode(errmode&~2)
    print('New windows error mode 0x%x'%errmode)

ret=0

os.environ['PATH'] = os.pathsep.join(['.', os.environ['PATH']])

if SP.call('crasher abort', shell=True):
    print('aborted')
else:
    print('Unexpected lack of abort')
    ret=1

if SP.call('crasher crash', shell=True):
    print('crashed')
else:
    print('Unexpected lack of crash')
    ret=1

if ret==0:
    print('All as expected')

sys.exit(ret)
