"""Show OSX Crash Reporter logs
"""
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import os
import platform
from glob import glob

from . import CommonDumper

class DarwinDumper(CommonDumper):

    def __init__(self, args):
        super().__init__(args)

        v, _, _ = platform.mac_ver()
        v = float('.'.join(v.split('.')[:2]))
        if v >= 12.0:
            self.crash_ext = "ips"
        else:
            self.crash_ext = "crash"

    def install(self):
        pass
    def uninstall(self):
        pass

    def report(self):
        # we have no way to know if any crash reporter logs will be written, or are still *being* written.
        # so we just wait a while and hope for the best
        time.sleep(10)

        for path in ('~/Library/Logs/DiagnosticReports/*.diag', '~/Library/Logs/DiagnosticReports/*.dpsub', '~/Library/Logs/CrashReporter/*.{0}'.format(self.crash_ext)):
            for report in glob(os.path.expanduser(path)):
                self.error(report)
                self.catfile(report)
