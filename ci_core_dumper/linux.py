"""
On Linux use the core_pattern described in Documentation/sysctl/kernel.txt
to redirect core files to this script.  The pattern used includes the
PID of the process being dumped.  As the process has not yet been fully
reaped, the PID is still valid and is used to find the path of the
executable file.  Along with the core file, this is enough to run
GDB to produce stack traces.
"""
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import sys
import os
import time
import errno
import ctypes
import logging
import fcntl
import shutil
import traceback
import resource
import subprocess as SP
from glob import glob
try:
    from distutils.spawn import find_executable # < 3.12
except ImportError:
    from shutil import which as find_executable # >= 3.3

from . import CommonDumper, _root_dir

try:
    from os import set_inheritable # >=3.4
except ImportError:
    def set_inheritable(F, inheirt=True):
        cur = fcntl.fcntl(F, fcntl.F_GETFD)
        if inheirt:
            cur &= ~fcntl.FD_CLOEXEC
        else:
            cur |= fcntl.FD_CLOEXEC
        fcntl.fcntl(F, fcntl.F_SETFD, cur)

_log = logging.getLogger(__name__)

core_pattern = '/proc/sys/kernel/core_pattern'

def forknpark(fn, **kws):
    sys.stdout.flush()
    sys.stderr.flush()

    pid = os.fork()
    if pid==0: # child
        code=0
        try:
            fn(**kws)
        except:
            traceback.print_exc()
            code=1

        sys.stdout.flush()
        sys.stderr.flush()

        os._exit(code)
        os.abort() # paranoia
    else: # parent
        pid, sts = os.waitpid(pid, 0)

        sys.stdout.flush()
        sys.stderr.flush()

        if sts!=0:
            raise RuntimeError(sts)

def nsenter(pid):
    """Join the current process to all of the namespaces
       of the target PID of which it is not already a member.
    """
    myself = ctypes.CDLL(None)

    _setns = myself.setns
    _setns.argtypes = [ctypes.c_int, ctypes.c_int]
    _setns.restype = ctypes.c_int

    def setns(F, nstype=0):
        ret = _setns(F.fileno(), nstype)
        if ret!=0:
            raise OSError(ctypes.get_errno())

    NSs = []

    # join all all namespaces of target process.
    # Some are entered immediately, the rest will only be
    # entered by child process(es).

    # must open all NS files first (from init mount ns)
    # before entering any (including mount ns)
    for ns in os.listdir('/proc/%d/ns'%pid):
        NSs.append((ns,
                    open('/proc/%d/ns/%s'%(pid, ns), 'rb'),
                    open('/proc/self/ns/%s'%ns, 'rb')))

    for ns, T, S in NSs:
        if not os.path.sameopenfile(T.fileno(), S.fileno()):
            print('Join', ns, 'namespace')
            setns(T)
        T.close()
        S.close()

class FLock(object):
    def __init__(self, file):
        self._file = file
    def __enter__(self):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)
    def __exit__(self,A,B,C):
        self._file.flush()
        os.fsync(self._file.fileno())
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)

def syncfd(F):
    '''dump() writes only once, so it is enough to cycle through the write lock
    to know that writing has completed
    '''
    with FLock(F):
        pass

class InstallStdIO(object):
    def __init__(self, out):
        self.out = out

    def __enter__(self):
        os.dup2(self.out.fileno(), 1)
        os.dup2(self.out.fileno(), 2)

        set_inheritable(1, True) # paranoia?
        set_inheritable(2, True)

        if not sys.stdout:
            sys.stdout = os.fdopen(1, 'w')

        if not sys.stderr:
            sys.stderr = os.fdopen(2, 'w')

    def __exit__(self,A,B,C):
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = sys.stderr = None

class LinuxDumper(CommonDumper):
    def install(self):
        self.fix_parent()
        self.sudo()

        with open(core_pattern, 'r') as F:
            current = F.read()
        _log.debug('Current core_pattern: %s', current)

        self.mkdirs(self.args.outdir)

        # keep for later use by uninstall
        with open(os.path.join(self.args.outdir, 'core_pattern'), 'w') as F:
            F.write(current)

        dumper = os.path.join(self.args.outdir, 'dumper.py')
        with open(dumper, 'w') as F:
            F.write('''#!{sys.executable}
import sys
sys.path.append(r'{cwd}')
from ci_core_dumper.linux import dump
dump(outdir=r'{args.outdir}', gdb=r'{args.debugger}', extra_cmds={cmds!r})
'''.format(sys=sys,
           args=self.args,
           cwd=_root_dir,
           cmds=self.args.gdb_cmds.split(';'),
           ))

        # executable
        os.chmod(dumper, 0o755)

        try:
            with open(core_pattern, 'w') as F:
                F.write('|{} %p %P %t'.format(dumper))
        except IOError as e:
            if e.errno==errno.EACCES:
                _log.error('Insufficient permission to open "{}".  sudo?'.format(core_pattern))
                return # soft-fail
            elif e.errno==errno.EROFS:
                _log.error('Unable to open "{}" Read-only FS.  docker?'.format(core_pattern))
                return # soft-fail
            raise

    def uninstall(self):
        self.sudo()

        save = os.path.join(self.args.outdir, 'core_pattern')
        try:
            with open(save, 'r') as F:
                current = F.read()
        except IOError as e:
            if e.errno==errno.ENOENT:
                _log.warning('Nothing to uninstall')
                return
            raise

        try:
            with open(core_pattern, 'w') as F:
                F.write(current)
        except IOError as e:
            if e.errno==errno.EACCES:
                _log.error('Insufficient permission to open "{}".  sudo?'.format(core_pattern))
                return # soft-fail
            raise

        os.remove(save)

    def report(self):
        for log in glob(os.path.join(self.args.outdir, '*.txt')):
            self.error(log)
            self.catfile(log, sync=syncfd)

    def doexec(self):
        # raise core file limit for self and child
        S, H = resource.getrlimit(resource.RLIMIT_CORE)
        resource.setrlimit(resource.RLIMIT_CORE, (H, H))
        _log.debug('adjust ulimit -c%d', H)
        CommonDumper.doexec(self)

    def fix_parent(self):
        '''Attempt to adjust core dump limits of parent so that
           it can be inherited by future siblings (tests which might crash).

           Allow us to "just work" even if caller has forgotten to raise
           the core limit, and doesn't use our 'exec' sub-command.
        '''
        if not hasattr(resource, 'prlimit'):
            return # py < 3.4
        try:
            ppid = os.getppid() # Parent PID
            S, H = resource.prlimit(ppid, resource.RLIMIT_CORE)
            resource.prlimit(ppid, resource.RLIMIT_CORE, (H, H))
            _log.debug('adjust parent %d ulimit -c%d', ppid, H)

        except:
            _log.exception('Unable to "ulimit -c unlimited" for parent')

    def sudo(self):
        '''re-exec myself w/ sudo
        '''
        who = os.geteuid()
        _log.info('IAM %d', who)
        if os.geteuid()==0:
            return
        _log.info('Attempting to acquire privilege for %s', os.geteuid())

        try:
            sudo = [self.findbin('sudo'), 'PYTHONPATH='+os.environ.get('PYTHONPATH',''),
                    sys.executable, '-m', 'ci_core_dumper'] + sys.argv[1:]
            _log.debug('EXEC %s', sudo)
            ret = SP.call(sudo)
        except:
            _log.exception('Unable to acquire permission')
            # soft-fail and attempt to continue

        if ret==0:
            sys.exit(0)

def dump(outdir, gdb, extra_cmds):
    # running as root in init namespaces (not container)
    # core file open as stdin

    os.umask(0o022)

    # PID in target namespace, PID in init namespace, time of dump (POSIX)
    tpid, ipid, dtime = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])

    logfile  = os.path.join(outdir, '{}.{}.txt' .format(dtime, ipid))

    # Open output file for this analysis, lock output against later syncfd(),
    # and cause stdout/err to be redirected to it.  (saves us the bother of
    # redirecting later)
    with open(logfile, 'w') as LOG, FLock(LOG), InstallStdIO(LOG):
        print('Dumping PID %d (%d) @ %d %s'%(tpid, ipid, dtime, time.ctime(dtime)))

        try:
            nsenter(ipid)

            forknpark(dump2, pid=tpid, gdb=gdb, extra_cmds=extra_cmds)
        except:
            traceback.print_exc()
            sys.exit(1) # not really any point as Linux kernel doesn't seem to do anything with !=0
        else:
            print('Complete')

def dump2(pid, gdb, extra_cmds):
    # running as root, fully in the target/container namespaces

    # os.environ is still from the init namespaces.
    # We can't easily inspect target environment(s)
    # so try to make up something workable.
    orig_env = os.environ.copy()
    os.environ.clear()
    os.environ['TERM'] = 'vt100'
    os.environ['USER'] = orig_env.get('USER', 'root')
    os.environ['PATH'] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    for sh in (orig_env.get('SHELL','sh'), 'sh', 'bash', 'dash'):
        shell = find_executable(sh)
        if sh:
            os.environ['SHELL'] = shell
            break
    else:
        print('ERROR: no support shell in target')
        sys.exit(1)

    for gname in (gdb, 'gdb'):
        gdb = find_executable(gname)
        if gdb:
            break
    else:
        print('ERROR: Debugger executable not found.  Must install %s'%gdb)
        sys.exit(1)

    # inspect the target process
    exe = os.readlink('/proc/{}/exe'.format(pid))
    with open('/proc/{}/cmdline'.format(pid), 'rb') as F:
        cmdline = [arg.decode('ascii') for arg in F.read().split(b'\0')]
    cmdline.pop() # result of final nil

    print('EXE: {}\nCMDLINE: {}'.format(exe, cmdline))

    # write the core file into some temporary storage in the target mount NS
    for tmpdir in ('/tmp', '/var/tmp', '/dev/shm'):
        corefile = os.path.join(tmpdir, 'core.ccd.%d'%pid)
        try:
            OF = open(corefile, 'wb')
            break
        except:
            print('Unable to write core file to %s'%corefile)
            continue
    else:
        print('Unable to store core file in target FS')
        sys.exit(1)

    print('Wrote core file to %s'%corefile)
    with OF:
        if hasattr(sys.stdin, 'buffer'):
            IF = sys.stdin.buffer # py3
        else:
            IF = sys.stdin # py2 (!win32)
        shutil.copyfileobj(IF, OF)
        OF.flush()

    # /proc/<pid> has now disappeared

    cmd = [
        gdb,
        '--nx', '--nw', '--batch', # no .gitinit, no UI, no interactive
        '-ex', 'set pagination 0',
        '-ex', 'thread apply all bt',
    ]
    for extra in extra_cmds:
        cmd += ['-ex', extra]
    cmd += [
        exe, corefile
    ]
    print('exec: %s'%cmd)
    sys.stdout.flush()
    sys.stderr.flush()

    os.execv(gdb, cmd)
    # not reached
