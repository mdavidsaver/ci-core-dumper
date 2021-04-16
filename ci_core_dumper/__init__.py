import sys
import os
import errno
import logging
import platform
import tempfile
import subprocess as SP

_log = logging.getLogger(__name__)

# our entry in sys.path
_root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class CommonDumper(object):
    inactions = 'GITHUB_ACTIONS' in os.environ

    def __init__(self, args):
        self.args = args
        self.exit = 0

    # sub-class hooks
    def install(self):
        _log.warn('core file analysis not implemented for %s'%platform.system())
    def uninstall(self):
        pass
    def report(self):
        _log.warn('core file analysis not implemented for %s'%platform.system())

    def doexec(self):
        cmd = [self.findbin(self.args.command)] + self.args.args
        _log.debug('EXEC %s', cmd)
        sys.exit(SP.call(cmd))

    # utilities
    def findbin(self, name):
        search = ['.']+os.environ['PATH'].split(os.pathsep)
        for path in search:
            for suf in ('', '.exe'):
                cand = os.path.join(path, name+suf)
                if os.path.isfile(cand):
                    return cand
        raise RuntimeError("Unable to find {} in {}".format(name, search))

    def mkdirs(self, name):
        try:
            os.makedirs(name)
        except OSError as e:
            if e.errno!=errno.EEXIST:
                raise
            # EEXIST is expected

    def error(self, msg, code=1):
        self.exit = max(self.exit, code)
        if self.inactions:
            sys.stdout.write('::error::Core Dump %s\n'%msg)
        else:
            sys.stdout.write('Core Dump: %s\n'%msg)

    def catfile(self, name, sync=lambda F:None):
        if self.inactions:
            sys.stdout.write('::group::%s\n'%name)
        sys.stdout.write('==== BEGIN: {} ====\n'.format(name))
        try:
            with open(name, 'r') as F:
                sync(F)
                sys.stdout.write(F.read())
        except IOError as e:
            if e.errno==errno.ENOENT:
                sys.stdout.write('==== No such file ===\n')
            else:
                _log.exception('Unable to read %s', name)
        sys.stdout.write('==== END: {} ====\n'.format(name))
        if self.inactions:
            sys.stdout.write('::endgroup::\n')

def getargs():
    from argparse import ArgumentParser, REMAINDER
    P = ArgumentParser(description='CI core dump analyzer.'\
        +'  Run install prior to exec of suspect code.'\
        +'  Then report afterwards.'\
        +'  install and uninstall require root (eg. sudo).')

    P.add_argument('--outdir', default=os.path.join(tempfile.gettempdir(), 'cores'),
                   help='Write backtraces to this directory')

    P.add_argument('-v', '--verbose', dest='level', default=logging.INFO,
                   action='store_const', const=logging.DEBUG)

    plat = platform.system()
    _log.debug('platform %s', plat)
    if plat=='Linux':
        from .linux import LinuxDumper as Dumper
    elif plat=='Windows':
        from .windows import WindowsDumper as Dumper
    elif plat=='Darwin':
        from .osx import DarwinDumper as Dumper
    else:
        Dumper = CommonDumper

    P.set_defaults(target=Dumper)

    SP = P.add_subparsers()

    CMD = SP.add_parser('install')
    CMD.add_argument('--gdb', dest='debugger')
    CMD.set_defaults(func=Dumper.install)

    CMD = SP.add_parser('uninstall')
    CMD.set_defaults(func=Dumper.uninstall)

    CMD = SP.add_parser('report')
    CMD.set_defaults(func=Dumper.report)

    CMD = SP.add_parser('exec')
    CMD.add_argument('command')
    CMD.add_argument('args', nargs=REMAINDER)
    CMD.set_defaults(func=Dumper.doexec)

    return P

def main(args = None):
    args = getargs().parse_args(args)
    logging.basicConfig(level=args.level)
    _log.debug('py %s', sys.executable)
    dumper = args.target(args)
    args.func(dumper)
    sys.exit(dumper.exit)
