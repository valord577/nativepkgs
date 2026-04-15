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

import shutil


_ccache_dir = Path(sys.argv[1])
_ccache_key = sys.argv[2]

_src = f'r2:{x.S3_R2_STORAGE_BUCKET}/ccache/{_ccache_key}.tar.xz'
_dst = (Path(x.PROJ_ROOT) / f'{_ccache_key}.tar.xz').absolute().as_posix()
x._util_func__subprocess(args=[x.RCLONE_EXEC.absolute().as_posix(), 'copyto', _src, _dst])
if (Path(_dst)).exists():
    shutil.unpack_archive(_dst, extract_dir=(_ccache_dir.parent).absolute().as_posix())
