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

_src = f'r2:{x.S3_R2_STORAGE_BUCKET}/ccache/{_ccache_key}.zip'
_dst = (Path(x.PROJ_ROOT) / f'{_ccache_key}.zip')
x._util_func__subprocess(args=[x.RCLONE_EXEC.absolute().as_posix(), 'copyto', _src, _dst.absolute().as_posix()])
if _dst.exists():
    x._util_unpack_zip_with_softlinks(_dst, extract_dir=(_ccache_dir.parent).absolute().as_posix())
