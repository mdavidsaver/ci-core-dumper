"""
On Linux use the core_pattern described in Documentation/sysctl/kernel.txt
to redirect core files to this script.  The pattern used includes the
PID of the process being dumped.  As the process has not yet been fully
reaped, the PID is still valid and is used to find the path of the
executable file.  Along with the core file, this is enough to run
GDB to produce stack traces.
"""
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import os
import errno
import logging
import fcntl
import traceback
import resource
import subprocess as SP
from glob import glob

from . import CommonDumper, _root_dir

_log = logging.getLogger(__name__)

core_pattern = '/proc/sys/kernel/core_pattern'

class FLock(object):
    def __init__(self, file):
        self._file = file
    def __enter__(self):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)
    def __exit__(self,A,B,C):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)

def syncfd(F):
    '''dump() writes only once, so it is enough to cycle through the write lock
    to know that writing has completed
    '''
    with FLock(F):
        pass

class LinuxDumper(CommonDumper):
    def install(self):
        self.fix_parent()
        self.sudo()

        gdb = self.findbin(self.args.debugger or 'gdb')

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
dump(outdir=r'{args.outdir}', gdb=r'{gdb}', extra_cmds={cmds!r})
'''.format(sys=sys,
           args=self.args,
           gdb=gdb,
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

        self.catfile(os.path.join(self.args.outdir, 'core-dumper.log'))

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
    os.umask(0o022)

    pid, hpid, dtime = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])

    logging.basicConfig(level=logging.DEBUG, filename=os.path.join(outdir, 'core-dumper.log'))

    _log.debug('Dumping PID %s @ %s', pid, dtime)

    corefile = os.path.join(outdir, '{}.{}.core'.format(dtime, hpid))
    logfile  = os.path.join(outdir, '{}.{}.txt' .format(dtime, hpid))

    with open(logfile, 'w') as LOG, FLock(LOG):
        try:
            # core file comes through stdin, and is binary
            if hasattr(sys.stdin, 'buffer'):
                IF = sys.stdin.buffer # py3
            else:
                IF = sys.stdin # py2 (!win32)

            # read info from /proc of dump'd process
            exe = os.readlink('/proc/{}/exe'.format(hpid))
            with open('/proc/{}/cmdline'.format(hpid), 'rb') as F:
                cmdline = [arg.decode('ascii') for arg in F.read().split(b'\0')]
            cmdline.pop() # result of final nil

            LOG.write('CORE: {}\nEXE: {}\nCMDLINE: {}\n'.format(corefile, exe, cmdline))

            # copy blob content
            with open(corefile, 'wb') as OF:
                while True:
                    blob = IF.read(1024*32)
                    if not blob:
                        break
                    OF.write(blob)
            # /proc/<hpid> has now disappeared

            if pid!=hpid:
                LOG.write('Crashing process is %d in a container.'%pid)
                LOG.write('Analysis not implemented')
                # would need to access container mount namespace

            else:
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
                _log.debug('exec: %s', cmd)
                LOG.flush()

                with open(os.devnull, 'r') as NULL:
                    trace = SP.check_output(cmd, stdin=NULL, stderr=SP.STDOUT).decode('utf-8', 'replace')

                LOG.write(trace)
            LOG.write('\nComplete\n')

        except:
            traceback.print_exc(file=LOG)
        finally:
            # always flush before unlock
            LOG.flush()
            os.fsync(LOG.fileno())

    _log.debug('Complete')
