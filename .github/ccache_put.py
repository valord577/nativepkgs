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


_ccache_dir = Path(sys.argv[1])
_ccache_key = sys.argv[2]

x._util_dopack_zip_with_softlinks(_ccache_dir, _ccache_key)


_src = (_ccache_dir.parent / f'{_ccache_key}.zip').absolute().as_posix()
_dst = f'r2:{x.S3_R2_STORAGE_BUCKET}/ccache/'
x._util_func__subprocess(args=[x.RCLONE_EXEC.absolute().as_posix(), 'copy', _src, _dst])
