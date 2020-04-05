"""
Hook into Windows post-mortem debugger facility

https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/enabling-postmortem-debugging
"""

import sys
import os
import time
import logging
import traceback
import subprocess as SP
import winreg
import msvcrt
from glob import glob

from . import CommonDumper, _root_dir

_log = logging.getLogger(__name__)

def syncfd(F):
    lck = F.name+'.lck'
    while os.path.isfile(lck):
        time.sleep(1.0)

class Reg(object):
    def __init__(self):
        self.root = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        self.key = winreg.OpenKeyEx(self.root, r'HKLM\Software\Microsoft\Windows NT\CurrentVersion\AeDebug')

    def __getitem__(self, name):
        value, type = winreg.QueryValueEx(self.key, name)
        assert type==winreg.REG_SZ, type
        return value

    def __setitem__(self, name, value):
        winreg.SetValueEx(self.key, name, 0, winreg.REG_SZ, value)

def cdbsearch():
    ret = []
    for cdb in glob(r'C:\Program Files (x86)\Windows Kits\*\Debuggers\{}\cdb.exe'.format(os.environ['PLATFORM'].lower())):
        ret.append(os.path.dirname(cdb))
    return ret
cdbsearch = cdbsearch()

class WindowsDumper(CommonDumper):
    def install(self):
        os.environ['PATH'] = os.pathsep.join([os.environ['PATH']] + cdbsearch)

        cdb = self.findbin(self.args.debugger or 'cdb.exe')
        cmd = self.findbin(self.args.debugger or 'cmd.exe')

        reg = Reg()
        current = reg['Auto'], reg['Debugger']
        _log.debug('Current PMDB %s', current)

        self.mkdirs(self.args.outdir)

        # keep for later use by uninstall
        with open(os.path.join(self.args.outdir, 'save.dat'), 'w') as F:
            F.write('{}\n{}'.format(current[0], current[1]))

        dumper = os.path.join(self.args.outdir, 'dumper.bat')
        with open(dumper, 'w') as F:
            F.write('''
set "PYTHONPATH={cwd}"
"{sys.executable}" -m ci_core_dumper.windows --outdir "{args.outdir}" --cdb "{cdb}" --pid %1
'''.format(sys=sys, cwd=_root_dir, cdb=cdb, args=self.args)

        reg['Auto'] = '1'
        reg['Debugger'] = '{} /c {} %ld %ld %p'.format(cmd, dumper)

    def uninstall(self):
        save = os.path.join(self.args.outdir, 'save.dat')
        try:
            with open(save, 'rb') as F:
                current = F.read().split('\n', 1)
        except IOError as e:
            if e.errno==errno.ENOENT:
                _log.warning('Nothing to uninstall')
                return
            raise

        reg['Auto'], reg['Debugger'] = current

        os.remove(save)

    def report(self):
        for log in glob(os.path.join(outdir, '*.txt')):
            self.catfile(log, sync=syncfd)

        self.catfile(os.path.join(outdir, 'core-dumper.log'))

def getargs():
    from argparse import ArgumentParser
    P = ArgumentParser()
    P.add_argument('--cdb')
    P.add_argument('--pid')
    return P

def dump():
    dtime = time.time()
    args = getargs().parse_args()

    _log.debug('Dumping PID %s @ %s', args.pid, dtime)
    try:

        cdbfile = os.path.join(outdir, '{}.{}.cdb'.format(dtime, args.pid))
        logfile  = os.path.join(outdir, '{}.{}.txt' .format(dtime, args.pid))
        lckfile = logfile+'.lck'

        with open(lckfile, 'w') as LCK, open(logfile, 'w') as LOG:
            LOG.write('PID: {}\n'.format(args.pid))
            try:

                with open(cdbfile, 'w') as F:
                    F.write('''
.logopen "{log}"
~* k
.logclose
q
'''.format(log=logfile)

            cmd = [
                args.cdb,
                '-p', args.pid,
                '-cf', cdbfile,
                '-g', '-G',
            ]

            _log.debug('exec: %s', cmd)
            LOG.flush()

            trace = SP.check_output(cmd, stderr=SP.STDOUT)

            LOG.write(trace)
            LOG.write('\nComplete\n')

        except:
            traceback.print_exc(file=LOG)
        finally:
            # always flush before unlock
            LOG.flush()

    except:
        _log.exception('oops')
    finally:
        os.remove(lckfile)

if __name__=='__main__':
    dump()
