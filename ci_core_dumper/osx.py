"""Show OSX Crash Reporter logs
"""
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import os
from glob import glob

from . import CommonDumper

class DarwinDumper(CommonDumper):
    def install(self):
        pass
    def uninstall(self):
        pass

    def report(self):
        # we have no way to know if any crash reporter logs will be written, or are still *being* written.
        # so we just wait a while and hope for the best
        time.sleep(10)

        for dir in ('~/Library/Logs/DiagnosticReports/', '~/Library/Logs/CrashReporter/'):
            for pat in ('*.crash', '*.ips'): # OSX >= 12.0 changes dump format, and file extension
                for report in glob(os.path.expanduser(dir+pat)):
                    self.error(report)
                    self.catfile(report)
