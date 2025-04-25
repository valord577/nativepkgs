#!/usr/bin/env python3

# fmt: off

import os
import shutil
import subprocess as sp
import sys
from typing import NoReturn, Union


def _print(msg: str):
    print(msg, file=sys.stderr)
def show_errmsg(errmsg: str) -> NoReturn:
    _print(f'[e] {errmsg}')
    sys.exit(1)


def _util_func__subprocess_devnul(args: list[str],
    cwd: Union[str, None] = None, env: Union[dict[str, str], None] = None, shell=False
):
    print(f'>>>> subprocess cmdline: {args}', file=sys.stderr)
    proc = sp.run(args=args, cwd=cwd, env=env, shell=shell)
    if proc.returncode != 0:
        print(f'>>>> subprocess exitcode: {proc.returncode}', file=sys.stderr)
        sys.exit(proc.returncode)


if __name__ == "__main__":
    _inst_dir = os.getenv('INST_DIR', '')
    _pkg_zipname = os.getenv('PKG_ZIPNAME', '')

    _sh = shutil.which('bash') or 'bash'
    _cwd = os.path.abspath(os.path.dirname(_inst_dir))
    if sys.platform == 'win32':
        _sh = 'C:/msys64/usr/bin/bash.exe'
        _cwd = f'$(cygpath -u "{_cwd}")'
    _zip_cmd = f'zip -ry {_pkg_zipname}.zip {os.path.basename(_inst_dir)}'
    _util_func__subprocess_devnul(args=[_sh, '-lc', f'cd {_cwd}; {_zip_cmd}'])
