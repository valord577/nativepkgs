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
import shutil


_rclone = (Path(x.PROJ_ROOT) / '.github' / 'rclone').resolve().as_posix()
_s3_storage_bucket = os.getenv('S3_R2_STORAGE_BUCKET', '')


_ccache_dir = sys.argv[1]
_ccache_key = sys.argv[2]

_src = f'r2:{_s3_storage_bucket}/ccache/{_ccache_key}.tar.xz'
_dst = (Path(x.PROJ_ROOT) / f'{_ccache_key}.tar.xz').resolve().as_posix()
x._util_func__subprocess(args=[_rclone, 'copyto', _src, _dst])
if (Path(_dst)).exists():
    shutil.unpack_archive(_dst, extract_dir=(Path(_ccache_dir).parent).resolve().as_posix())
