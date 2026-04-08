#!/usr/bin/env python3

# fmt: off

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.append(
    (Path(__file__).parent / '..').absolute().as_posix()
)
from scripts import utils as x
# ----------------------------

import os


_rclone = (Path(x.PROJ_ROOT) / '.github' / 'rclone').absolute().as_posix()
_s3_storage_bucket = os.getenv('S3_R2_STORAGE_BUCKET', '')


_ccache_dir = sys.argv[1]
_ccache_key = sys.argv[2]

_sh = 'bash'
_cwd = _cwd_origin = (Path(_ccache_dir).parent).absolute().as_posix()
if sys.platform == 'win32':
    _sh = 'C:/msys64/usr/bin/bash.exe'
    _cwd = f'$(cygpath -u "{_cwd}")'
_tar_cmd = f'tar --posix --xz -cvf {_ccache_key}.tar.xz {os.path.basename(_ccache_dir)}'
x._util_func__subprocess(args=[_sh, '-lc', f'cd {_cwd}; export XZ_OPT="--threads=0"; {_tar_cmd}'])

_src = (Path(_cwd_origin) / f'{_ccache_key}.tar.xz').absolute().as_posix()
_dst = f'r2:{_s3_storage_bucket}/ccache/'
x._util_func__subprocess(args=[_rclone, 'copy', _src, _dst])
