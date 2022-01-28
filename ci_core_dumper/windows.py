"""
Hook into Windows post-mortem debugger facility

https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/enabling-postmortem-debugging
"""

import sys
import os
import time
import logging
import errno
import traceback
import ctypes
import subprocess as SP
from glob import glob

from . import CommonDumper, _root_dir

AeDebug = r'Software\Microsoft\Windows NT\CurrentVersion\AeDebug'
AeDebug6432 = r'Software\Wow6432Node\Microsoft\Windows NT\CurrentVersion\AeDebug'

_log = logging.getLogger(__name__)

def syncfd(F):
    lck = F.name+'.lck'
    while os.path.isfile(lck):
        time.sleep(1.0)

def reg_replace(bits, kname, vname, value):
    try:
        import winreg
    except ImportError:
        import _winreg as winreg

    access = winreg.KEY_READ|winreg.KEY_WRITE
    access |= {
        32:winreg.KEY_WOW64_32KEY,
        64:winreg.KEY_WOW64_64KEY,
    }[bits]

    key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, kname, 0, access)

    try:
        prev, type = winreg.QueryValueEx(key, vname)
        assert type==winreg.REG_SZ, type
    except WindowsError as e:
        if e.errno!=errno.ENOENT:
            raise
        prev = None

    winreg.SetValueEx(key, vname, 0, winreg.REG_SZ, value)
    winreg.FlushKey(key)
    _log.debug('%s SetValue %s.%s = %s', bits, kname, vname, value)

    return prev

def cdbsearch():
    arch = os.environ.get('PLATFORM', 'x64').lower()
    ret = []
    for cdb in glob(r'C:\Program Files (x86)\Windows Kits\*\Debuggers\{}\cdb.exe'.format(arch)):
        ret.append(os.path.dirname(cdb))
    return ret

def binsearch():
    '''Find all directories containing .exe .dll and .lib
    '''
    ret = set()
    for root, subdirs, files in os.walk(os.getcwd()):
        for file in files:
            if os.path.splitext(file)[1] in ('.exe', '.dll', '.lib'):
                ret.add(root)
    return list(ret)

class WindowsDumper(CommonDumper):
    def install(self):
        self.ErrorMode()
        os.environ['PATH'] = os.pathsep.join([os.environ['PATH']] + cdbsearch())

        cdb = self.findbin(self.args.debugger or 'cdb.exe')

        sympath = binsearch()
        [_log.debug('Sympath %s', spath) for spath in sympath]

        self.mkdirs(self.args.outdir)

        dumper = os.path.join(self.args.outdir, 'dumper.bat')
        with open(dumper, 'w') as F:
            F.write(r'''
import os
import sys
import subprocess
os.environ['_NT_SYMBOL_PATH'] = {sympath!r}
sys.path.append({cwd!r})
from ci_core_dumper.windows import dump
dump(*sys.argv[1:4],
    outdir={args.outdir!r},
    cdb={cdb!r},
    cdb_extra={cdb_cmds!r},
)
'''.format(cwd=_root_dir,
           cdb=cdb,
           cdb_cmds=self.args.cdb_cmds.replace(';', '\n'),
           args=self.args,
           sympath='*'.join(sympath)))

        reg_replace(32, AeDebug, 'Debugger', '"{}" "{}" 32 %ld %ld'.format(sys.executable, dumper))
        reg_replace(32, AeDebug, 'Auto', '1')
        # on 64
        reg_replace(64, AeDebug, 'Debugger', '"{}" "{}" 64 %ld %ld'.format(sys.executable, dumper))
        reg_replace(64, AeDebug, 'Auto', '1')
        reg_replace(64, AeDebug6432, 'Debugger', '"{}" 6432 "{}" %ld %ld'.format(sys.executable, dumper))
        reg_replace(64, AeDebug6432, 'Auto', '1')

    def uninstall(self):
        _log.warning('uninstall not implemented')

    def report(self):
        for log in glob(os.path.join(self.args.outdir, '*.txt')):
            self.error(log)
            self.catfile(log, sync=syncfd)

        self.catfile(os.path.join(self.args.outdir, 'core-dumper.log'))

    def doexec(self):
        self.ErrorMode()
        CommonDumper.doexec(self)

    def ErrorMode(self):
        # https://docs.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode?redirectedfrom=MSDN
        # SEM_NOGPFAULTERRORBOX (2) has the undocumented side-effect of preventing
        # AeDebug from being triggered.
        errmode = ctypes.windll.kernel32.GetErrorMode()
        if errmode&2:
            _log.warn('Environment sets SEM_NOGPFAULTERRORBOX which disables AeDebug.')
            _log.warn('Ensure that test runners call SetErrorMode(GetErrorMode()&~SEM_NOGPFAULTERRORBOX)')
            _log.warn('Or call through ci-core-dumper exec cmd args...')
            errmode &= ~2
            errmode = ctypes.windll.kernel32.SetErrorMode(errmode)
        _log.debug('SetErrorMode(0x%d)', errmode)

def dump(arch, pid, event, outdir=None, cdb=None, cdb_extra=None):
    dtime = time.time()

    logging.basicConfig(level=logging.DEBUG, filename=os.path.join(outdir, 'core-dumper.log'))

    _log.debug('Dumping PID %s @ %s of %s', pid, dtime, arch)
    try:
        os.chdir(outdir)

        cdbfile = '{}.{}.cdb'.format(dtime, pid)
        logfile  = '{}.{}.txt'.format(dtime, pid)
        lckfile = logfile+'.lck'

        with open(lckfile, 'w'), open(logfile, 'w') as LOG:
            LOG.write('PID: {}\n'.format(pid))
            try:

                with open(cdbfile, 'w') as F:
                    F.write('''
.symfix+ c:\symcache
.sympath
.echo Modules list
lm
.echo Stacks
~* kP n
.echo analysis
!analyze
{cdb_extra}
.echo End
.kill
q
'''.format(cdb_extra=cdb_extra))

                cmd = [
                    cdb,
                    '-p', pid,
                    '-e', event,
                    #'-netsyms', 'no',
                    '-lines',
                    '-g', '-G',
                    '-cf', cdbfile,
                    #'-c', 'lm;~* kv n;q;',
                ]

                _log.debug('exec: %s', cmd)
                LOG.flush()

                proc = SP.Popen(cmd, stdout=SP.PIPE, stderr=SP.STDOUT,
                                close_fds=False, creationflags=SP.CREATE_NEW_PROCESS_GROUP)

                if sys.version_info>=(3,3):
                    try:
                        trace, _unused = proc.communicate(timeout=20.0)
                    except SP.TimeoutExpired:
                        LOG.write('cdb TIMEOUT\n')
                        proc.kill()
                        trace, _unused = proc.communicate()
                else:
                    trace, _unused = proc.communicate()

                LOG.flush()
                LOG.seek(0,2)

                code = proc.poll()
                if code:
                    LOG.write('ERROR: {}\n'.format(code))

                LOG.write(trace.decode('ascii'))
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
