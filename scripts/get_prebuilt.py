#!/usr/bin/env python3

# fmt: off

import sys
sys.dont_write_bytecode = True

import utils as x
# ----------------------------

import os
import sys
import shutil
import urllib.request

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
    pass
else:
    _this_lib_dir.unlink(missing_ok=True)
    _src = (Path(x.PROJ_ROOT) / 'out' / pkg_name / pkg_platform / _adapt_arch_libc).absolute().as_posix()
    _this_lib_dir.symlink_to(_src, target_is_directory=True)
