# SPDX-License-Identifier: GPL-3.0-or-later
import sys
import logging
import winreg
from subprocess import check_call

# https://github.com/actions/runner-images/issues/13465#issuecomment-3702051401

#          $installerEntry = Get-ItemProperty HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* `
#            | ?{$_.DisplayName -match "Windows Software Development Kit"} `
#            | Sort-Object DisplayVersion -Descending | select -First 1
#          $bundleCachePath = $installerEntry.BundleCachePath
#          $process = Start-Process -FilePath $bundleCachePath -ArgumentList ('/features', 'OptionId.WindowsDesktopDebuggers', '/q') -Wait -PassThru
#          $exitCode = $process.ExitCode
#          if ($exitCode -eq 0) {
#              Write-Host "Installation successful"
#          }

access = winreg.KEY_READ|winreg.KEY_WOW64_64KEY
rootname = r'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'

# find latest version of winsdksetup.exe

def main():
    print('Attempting to install WindowsDesktopDebuggers')
    winsdks = {}

    with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, rootname, 0, access) as root:
        nsub, _nval, _lastmod = winreg.QueryInfoKey(root)

        for idx in range(nsub):
            sname = winreg.EnumKey(root, idx) # some hash or GUID

            with winreg.OpenKeyEx(root, sname, 0, access) as sk:
                try:
                    sval, _stype = winreg.QueryValueEx(sk, 'DisplayName') # "Windows Software Development Kit - Windows 10.0.26100.7175"
                except FileNotFoundError:
                    continue # ignore entries w/o DisplayName
                except:
                    logging.exception(f'{rootname}\\{sname} DisplayName')
                    continue
                else:
                    print(f'  consider {sname} : {sval!r}')
                    if not sval.startswith('Windows Software Development Kit'):
                        continue

                    print(f'Found Windows SDK {sname} : {sval!r}')

                    try:
                        iversion, _vtype = winreg.QueryValueEx(sk, 'DisplayVersion') # eg. "10.1.26100.7175"
                        print(f'  version: {iversion}')
                        installer, _itype = winreg.QueryValueEx(sk, 'BundleCachePath') # "C:\ProgramData\...\winsdksetup.exe"
                        print(f'  installer: {installer}')

                        winsdks[iversion] = installer
                    except:
                        logging.exception(sname)

    if not len(winsdks):
        raise RuntimeError('No winsdksetup.exe')

    winsdks = list(winsdks.items()) # [(version, exe)]
    winsdks.sort() # sort incrementing

    for ver, exe in winsdks:
        print(f'{ver}: {exe!r}')

    winsdk = winsdks[-1][1] # last (latest)

    cmd = [
        winsdk,
        '/features', 'OptionId.WindowsDesktopDebuggers', '/q',
    ]
    print(f'run: {cmd!r}')
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        check_call(cmd)
    finally:
        sys.stdout.flush()
        sys.stderr.flush()

if __name__=='__main__':
    main()
