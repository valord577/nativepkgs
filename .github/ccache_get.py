#!/usr/bin/env python3

# fmt: off

import os
import shutil
import subprocess as sp
import sys
from typing import NoReturn, Union


_basedir = os.path.abspath(os.path.dirname(__file__))
_rclone = os.path.abspath(os.path.join(_basedir, 'rclone'))
_s3_storage_bucket = os.getenv('S3_R2_STORAGE_BUCKET', '')

def _print(msg: str):
    print(msg, file=sys.stderr)
def show_errmsg(errmsg: str) -> NoReturn:
    _print(f'[e] {errmsg}')
    sys.exit(1)


def _util_func__subprocess(args: list[str],
    cwd: Union[str, None] = None, env: Union[dict[str, str], None] = None, shell=False
):
    print(f'>>>> subprocess cmdline: {args}', file=sys.stderr)
    proc = sp.run(args=args, cwd=cwd, env=env, shell=shell)
    if proc.returncode != 0:
        print(f'>>>> subprocess exitcode: {proc.returncode}', file=sys.stderr)
        sys.exit(proc.returncode)


if __name__ == "__main__":
    _ccache_dir = sys.argv[1]
    _ccache_key = sys.argv[2]

    _src = f'r2:{_s3_storage_bucket}/ccache/{_ccache_key}.tar.xz'
    _dst = os.path.abspath(os.path.join(_basedir, f'{_ccache_key}.tar.xz'))
    _util_func__subprocess(args=[_rclone, 'copyto', _src, _dst])
    if os.path.exists(_dst):
        shutil.unpack_archive(_dst, extract_dir=os.path.abspath(os.path.dirname(_ccache_dir)))
