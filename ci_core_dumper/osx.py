"""Show OSX Crash Reporter logs
"""

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

        for path in ('~/Library/Logs/DiagnosticReports/*.crash', '~/Library/Logs/CrashReporter/*.crash'):
            for report in glob(os.path.expanduser(path)):
                self.error(report)
                self.catfile(report)
