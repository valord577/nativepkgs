#!/usr/bin/env python3

# fmt: off

import sys
sys.dont_write_bytecode = True

import utils as x
# ----------------------------

import os
import sys
import shutil

from pathlib import Path


_adapt_arch_libc = sys.argv[1]
pkg_name         = sys.argv[2]
pkg_platform     = sys.argv[3]
pkg_version      = sys.argv[4]
pkg_type         = sys.argv[5]
pkg_extra        = sys.argv[6]
_3rd_deps_dir    = sys.argv[7]
os.makedirs(_3rd_deps_dir, exist_ok=True)

_this_lib_dir = (Path(_3rd_deps_dir) / pkg_name)
if False:
    pass
elif x.ON_GITLAB_CI:
    pass
elif x.ON_GITHUB_CI:
    _pkg_dl_name = f"{pkg_name}_{pkg_platform}_{_adapt_arch_libc}_{pkg_version}_{pkg_type}"
    if pkg_extra:
        _pkg_dl_name += f"_{pkg_extra}"

    _src = f'r2:{x.S3_R2_STORAGE_BUCKET}/packages/{pkg_name}/{pkg_version}/{_pkg_dl_name}.zip'
    x._util_func__subprocess(args=[x.RCLONE_EXEC.absolute().as_posix(), 'copy', _src, _3rd_deps_dir])

    archive_filepath = (Path(_3rd_deps_dir) / f'{_pkg_dl_name}.zip')
    x._util_unpack_zip_with_softlinks(archive_filepath, extract_dir=_3rd_deps_dir)
else:
    _this_lib_dir.unlink(missing_ok=True)
    _src = (Path(x.PROJ_ROOT) / 'out' / pkg_name / pkg_platform / _adapt_arch_libc).absolute().as_posix()
    _this_lib_dir.symlink_to(_src, target_is_directory=True)
