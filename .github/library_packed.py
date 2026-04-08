#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.append(
    (Path(__file__).parent / '..').resolve().as_posix()
)
from scripts import utils as x
# ----------------------------

import os


_inst_dir = os.getenv('INST_DIR', '')
_pkg_zipname = os.getenv('PKG_ZIPNAME', '')

_sh = 'bash'
_cwd = (Path(_inst_dir).parent).resolve().as_posix()
if sys.platform == 'win32':
    _sh = 'C:/msys64/usr/bin/bash.exe'
    _cwd = f'$(cygpath -u "{_cwd}")'
_zip_cmd = f'zip -ry {_pkg_zipname}.zip {Path(_inst_dir).name}'
x._util_func__subprocess(args=[_sh, '-lc', f'cd {_cwd}; {_zip_cmd}'])
