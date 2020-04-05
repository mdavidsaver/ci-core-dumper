#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import subprocess as SP

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
